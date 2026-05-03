"""
Separation Endpoint - Drum Separation Functionality
Uses storage/uploaded/ as the main directory
Separation results are stored in storage/uploaded/separated/ subdirectory
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response, Request
from fastapi.responses import StreamingResponse
from pathlib import Path
import shutil
import time
import json
import asyncio
import queue

from core.separator import DrumSeparator
from core.audio_io import AudioIO
from api.config import get_storage_dir
from api.rate_limiter import separation_limit

router = APIRouter(prefix="/separation", tags=["Separation"])

# NEW: Upload directory (main storage for uploads)
UPLOAD_DIR = get_storage_dir() / "uploaded"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/separate", summary="Separate drums")
@separation_limit
async def separate_drums(
    request: Request,
    file: UploadFile = File(..., description="Audio file (mp3, wav, flac)"),
    chunk_duration: float = Form(
        30.0, description="Chunk processing duration (seconds) to avoid memory overflow"
    ),
    model: str = Form(
        "htdemucs",
        description="Separation model: htdemucs (4-stem) or htdemucs_ft (fine-tuned 4-stem) or htdemucs_6s (6-stem)",
    ),
    shifts: int = Form(1, description="Number of time-shift augmentations"),
):
    """
    Separate drum parts from audio

    **Processing Flow**:
    1. Save file to storage/uploaded/filename
    2. **Copy** to storage/uploaded/separated/temp.mp3 for separation (original file is kept)
    3. Run separation (results saved in separated/ directory)
    4. Delete temp.mp3

    **Model Selection**:
    - `htdemucs`: 4-stem separation (drums, bass, other, vocals) - **Recommended**
    - `htdemucs_ft`: Fine-tuned 4-stem separation (drums, bass, other, vocals)
    - `htdemucs_6s`: 6-stem separation (drums, bass, piano, guitar, other, vocals)

    **Quality Enhancement**:
    - `shifts`: Number of time-shift augmentations
    """
    start_time = time.time()

    # Validate file type
    if not file.content_type.startswith("audio/"):
        raise HTTPException(400, "Please upload an audio file")

    # Step 1: Save uploaded file to storage/uploaded/
    uploaded_file = UPLOAD_DIR / file.filename
    try:
        with open(uploaded_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Step 2: Create separated directory and COPY file (keep original for playback)
    separated_dir = UPLOAD_DIR / "separated"
    separated_dir.mkdir(parents=True, exist_ok=True)

    temp_file = separated_dir / "temp.mp3"
    shutil.copy2(str(uploaded_file), str(temp_file))

    try:
        # Step 3: Run separation - save results to separated_dir
        separator = DrumSeparator(model_name=model)
        results = separator.separate(
            temp_file, separated_dir, chunk_duration=chunk_duration, shifts=shifts
        )

        processing_time = time.time() - start_time

        # Step 4: Cleanup temp file
        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "message": "Separation complete",
            "processing_time": round(processing_time, 2),
            "output_dir": str(separated_dir),
            "files": results,
            "note": "Files are saved on the server and can be downloaded via links",
        }

    except Exception as e:
        # Cleanup on error
        if temp_file.exists():
            temp_file.unlink()
        shutil.rmtree(separated_dir, ignore_errors=True)
        raise HTTPException(500, f"Separation failed: {str(e)}")


@router.post("/preview", summary="Quick preview")
@separation_limit
async def preview_separation(
    request: Request,
    file: UploadFile = File(...),
    shifts: int = Form(1, description="Number of time-shift augmentations"),
):
    """
    Quick preview of separation results (files are not saved)

    Only analyzes the first 30 seconds, returns duration info for each stem

    **Quality Enhancement**:
    - `shifts`: Number of time-shift augmentations, higher values yield better quality (default 2)
    """
    temp_file = UPLOAD_DIR / f"preview_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        separator = DrumSeparator()
        durations = separator.preview_sources(temp_file, shifts=shifts)

        # Cleanup
        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "preview": durations,
            "note": "Preview based on the first 30 seconds",
        }

    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(500, f"Preview failed: {str(e)}")


@router.post("/clear", summary="Clear uploaded files")
async def clear_uploaded():
    """
    Clear storage/uploaded/ directory and all its contents
    """
    if UPLOAD_DIR.exists():
        # Remove all files and subdirectories in uploaded/
        for item in UPLOAD_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)

        # Recreate the directory
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    return {"status": "success", "message": "Uploaded files cleared"}


@router.post("/separate_by_name", summary="Separate uploaded file")
@separation_limit
async def separate_by_name(
    request: Request,
    filename: str = Form(..., description="File name to separate"),
    chunk_duration: float = Form(
        30.0, description="Chunk processing duration (seconds)"
    ),
    model: str = Form(
        "htdemucs",
        description="Separation model: htdemucs (4-stem) or htdemucs_ft (fine-tuned 4-stem) or htdemucs_6s (6-stem)",
    ),
    shifts: int = Form(1, description="Number of time-shift augmentations"),
):
    """
    Separate a file already uploaded to storage/uploaded/

    Used by frontend: user uploads file for preview first, then clicks to process

    The file will be **copied** to storage/uploaded/separated/temp.mp3 for separation (original file is kept)
    Separation results are saved in storage/uploaded/separated/ directory

    **Model Selection**:
    - `htdemucs`: 4-stem separation (drums, bass, other, vocals) - **Recommended**
    - `htdemucs_ft`: Fine-tuned 4-stem separation (drums, bass, other, vocals)
    - `htdemucs_6s`: 6-stem separation (drums, bass, piano, guitar, other, vocals)

    **Quality Enhancement**:
    - `shifts`: Number of time-shift augmentations
    """
    start_time = time.time()

    # Check if file exists
    uploaded_file = UPLOAD_DIR / filename
    if not uploaded_file.exists():
        raise HTTPException(404, f"File not found: {filename}")

    # Create separated directory
    separated_dir = UPLOAD_DIR / "separated"
    separated_dir.mkdir(parents=True, exist_ok=True)

    # Copy file instead of move - keep original for playback during processing
    temp_file = separated_dir / "temp.mp3"
    shutil.copy2(str(uploaded_file), str(temp_file))

    try:
        # Run separation - save results to separated_dir
        separator = DrumSeparator(model_name=model)
        results = separator.separate(
            temp_file, separated_dir, chunk_duration=chunk_duration, shifts=shifts
        )

        processing_time = time.time() - start_time

        # Cleanup temp file
        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "message": "Separation complete",
            "processing_time": round(processing_time, 2),
            "output_dir": str(separated_dir),
            "files": results,
        }

    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        shutil.rmtree(separated_dir, ignore_errors=True)
        raise HTTPException(500, f"Separation failed: {str(e)}")


@router.post(
    "/separate_by_name_stream", summary="Separate uploaded file (streaming progress)"
)
@separation_limit
async def separate_by_name_stream(
    request: Request,
    filename: str = Form(..., description="File name to separate"),
    chunk_duration: float = Form(
        30.0, description="Chunk processing duration (seconds)"
    ),
    model: str = Form(
        "htdemucs",
        description="Separation model: htdemucs (4-stem) or htdemucs_ft (fine-tuned 4-stem) or htdemucs_6s (6-stem)",
    ),
    shifts: int = Form(1, description="Number of time-shift augmentations"),
):
    """
    Separate a file already uploaded to storage/uploaded/ with SSE streaming progress

    The file will be **copied** to storage/uploaded/separated/temp.mp3 for separation (original file is kept)

    **Progress Stages**:
    - loading: Loading audio file
    - chunk: Chunk processing (N/total chunks)
    - merging: Merging results (N/6 or N/4)
    - saving: Saving files (N/6 or N/4)
    - complete: Done

    **Model Selection**:
    - `htdemucs`: 4-stem separation (drums, bass, other, vocals) - **Recommended**
    - `htdemucs_ft`: Fine-tuned 4-stem separation (drums, bass, other, vocals)
    - `htdemucs_6s`: 6-stem separation (drums, bass, piano, guitar, other, vocals)

    **Quality Enhancement**:
    - `shifts`: Number of time-shift augmentations

    Uses SSE (Server-Sent Events) to stream progress, client must listen on text/event-stream
    """
    start_time = time.time()

    # Check if file exists
    uploaded_file = UPLOAD_DIR / filename
    if not uploaded_file.exists():
        raise HTTPException(404, f"File not found: {filename}")

    # Create separated directory
    separated_dir = UPLOAD_DIR / "separated"
    separated_dir.mkdir(parents=True, exist_ok=True)

    # Copy file instead of move - keep original for playback during processing
    temp_file = separated_dir / "temp.mp3"
    shutil.copy2(str(uploaded_file), str(temp_file))

    async def generate_progress():
        """Generate SSE event stream"""
        # Thread-safe queue for progress events
        progress_queue = queue.Queue()
        separation_completed = False
        separation_result = None
        separation_error = None

        # Progress callback function (runs in the worker thread)
        def progress_callback(stage: str, current: int, total: int, message: str):
            progress_data = {
                "stage": stage,
                "current": current,
                "total": total,
                "message": message,
                "percentage": round((current / total) * 100, 1) if total > 0 else 0,
            }
            progress_queue.put(json.dumps(progress_data))

        # Run separation in a separate thread (to avoid blocking the event loop)
        def run_separation():
            nonlocal separation_completed, separation_result, separation_error
            try:
                separator = DrumSeparator(model_name=model)
                results = separator.separate(
                    temp_file,
                    separated_dir,
                    chunk_duration=chunk_duration,
                    shifts=shifts,
                    progress_callback=progress_callback,
                )
                separation_result = results
            except Exception as e:
                separation_error = e
            finally:
                separation_completed = True
                progress_queue.put(None)  # Signal to exit

        # Run the blocking separation in thread pool
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_separation)

            # Continuously yield progress events
            while True:
                try:
                    # Wait for next event with timeout
                    event_data = progress_queue.get(timeout=0.5)

                    if event_data is None:  # Signal received
                        break

                    yield f"data: {event_data}\n\n"
                    await asyncio.sleep(0.01)  # Small yield to flush buffer
                except queue.Empty:
                    # No events yet, check if future is done
                    if future.done() and progress_queue.empty():
                        # Wait one more time to ensure we get the None signal
                        try:
                            event_data = progress_queue.get(timeout=0.5)
                            if event_data is None:
                                break
                            yield f"data: {event_data}\n\n"
                            await asyncio.sleep(0.01)
                        except queue.Empty:
                            break

            # Wait for future completion
            future.result()

        # Handle results or errors
        if separation_error:
            # Cleanup on error
            if temp_file.exists():
                temp_file.unlink()
            shutil.rmtree(separated_dir, ignore_errors=True)

            error_data = {
                "stage": "error",
                "status": "error",
                "message": str(separation_error),
                "percentage": 0,
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        else:
            processing_time = time.time() - start_time

            # Cleanup temp file
            temp_file.unlink(missing_ok=True)

            # Send completion event
            completion_data = {
                "stage": "complete",
                "status": "success",
                "message": "Separation complete",
                "processing_time": round(processing_time, 2),
                "output_dir": str(separated_dir),
                "files": separation_result,
                "percentage": 100,
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
