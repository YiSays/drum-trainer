"""
YouTube download and separation endpoint
"""

from fastapi import APIRouter, HTTPException, Body, Form, Request
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from typing import Optional, Dict
import json
import shutil

from api.config import get_storage_dir
from api.rate_limiter import youtube_limit
from core.youtube_downloader import YouTubeDownloader
from core.separator import DrumSeparator
from core.audio_io import AudioIO

router = APIRouter(prefix="/youtube", tags=["YouTube"])

UPLOAD_DIR = get_storage_dir() / "uploaded"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/download", summary="Download YouTube audio")
@youtube_limit
async def download_youtube_audio(
    request: Request,
    url: str = Body(
        ...,
        description="YouTube video URL (supports various formats including URLs with playlist parameters)",
    ),
    name: Optional[str] = Body(None, description="Output filename (optional)"),
):
    """
    Download audio from YouTube and save to storage/uploaded/

    **Supported URL formats**:
    - Standard: https://www.youtube.com/watch?v=VIDEO_ID
    - Complex: https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&start_radio=1&pp=...
    - Short: https://youtu.be/VIDEO_ID
    - Embed: https://www.youtube.com/embed/VIDEO_ID
    - Video ID only: VIDEO_ID
    """
    try:
        downloader = YouTubeDownloader(UPLOAD_DIR)
        result = downloader.download_audio(url, name)

        return {
            "status": "success",
            "message": "Audio downloaded successfully",
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Download failed: {str(e)}")


@router.post("/separate", summary="Download and separate YouTube audio")
@youtube_limit
async def separate_youtube_audio(
    request: Request,
    url: str = Body(..., description="YouTube video URL"),
    name: Optional[str] = Body(None, description="Output filename (optional)"),
    chunk_size: int = Body(30, description="Audio chunk duration in seconds"),
    model: str = Body(
        "htdemucs_6s",
        description="Separation model: htdemucs_6s (6-stem) or htdemucs (4-stem)",
    ),
):
    """
    Download audio from YouTube and perform drum separation.

    **Processing pipeline**:
    1. Download audio to storage/uploaded/
    2. Copy file to storage/uploaded/separated/temp.mp3 for separation
    3. Save separated tracks to storage/uploaded/separated/

    **Model options**:
    - `htdemucs_6s`: 6-stem separation (drums, bass, guitar, piano, other, vocals)
    - `htdemucs`: 4-stem separation (drums, bass, other, vocals)
    """
    try:
        print("Step 1: Downloading YouTube audio")
        downloader = YouTubeDownloader(UPLOAD_DIR)
        download_result = downloader.download_audio(url, name)

        audio_path = Path(download_result["file_path"])

        print("Step 2: Copying file for processing (keeping original)")
        separated_dir = UPLOAD_DIR / "separated"
        separated_dir.mkdir(parents=True, exist_ok=True)

        temp_file = separated_dir / "temp.mp3"
        shutil.copy2(str(audio_path), str(temp_file))

        try:
            print(f"Step 3: Separating drums (chunk_size={chunk_size}s)")
            separator = DrumSeparator(model_name=model)

            audio_io = AudioIO()
            audio_info = audio_io.get_audio_info(temp_file)
            duration = audio_info["duration"]

            if duration > chunk_size:
                print(f"Long audio ({duration}s), will process in chunks...")

            separator.separate(
                audio_path=temp_file, output_dir=separated_dir, chunk_size=chunk_size
            )

            print("Step 4: Collecting separated results")
            separated_files = {}
            for file in separated_dir.glob("*.wav"):
                key = file.stem
                separated_files[key] = str(file.relative_to(UPLOAD_DIR.parent))

            temp_file.unlink(missing_ok=True)

            result = {
                "status": "success",
                "message": "YouTube audio downloaded and separated successfully",
                "original": download_result,
                "separated": separated_files,
                "processing_time": audio_info.get("duration", 0),
            }

            print("✅ Full processing complete")
            print(f"   Original: {audio_path}")
            print(f"   Separated: {separated_dir}")

            return result

        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            shutil.rmtree(separated_dir, ignore_errors=True)
            raise

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")


@router.get("/list", summary="List uploaded files")
async def list_uploaded_files():
    """List files in storage/uploaded/"""
    supported_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"}
    files = []

    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                if file_path.name == "temp.mp3":
                    continue

                try:
                    audio_io = AudioIO()
                    info = audio_io.get_audio_info(file_path)

                    files.append(
                        {
                            "name": file_path.name,
                            "path": str(file_path.relative_to(UPLOAD_DIR.parent)),
                            "size": file_path.stat().st_size,
                            "duration": info["duration"],
                            "samplerate": info["samplerate"],
                            "channels": info["channels"],
                            "extension": file_path.suffix[1:],
                        }
                    )
                except Exception:
                    continue

    files.sort(key=lambda x: x["name"])
    return {"status": "success", "count": len(files), "files": files}
