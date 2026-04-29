"""
Tracks Endpoint - File browsing and audio playback for Flutter Web App

Uses storage/uploaded/ as the main directory
Separation results are saved in storage/uploaded/separated/ subdirectory
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Optional
import soundfile as sf

from core.audio_io import AudioIO
from api.config import get_storage_dir

router = APIRouter(prefix="/tracks", tags=["Tracks"])

# Upload directory (main storage for uploads)
UPLOAD_DIR = get_storage_dir() / "uploaded"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Demo directory (for demo tracks - ignored in current implementation)
DEMO_DIR = get_storage_dir() / "demo"


@router.get("/list", summary="List all tracks", response_model=List[dict])
async def list_tracks():
    """
    List files in storage/uploaded/ directory
    Includes: original files (storage/uploaded/) and separated files (storage/uploaded/separated/)

    **Separation Output (htdemucs model)**:
    - drums.wav - Drums
    - bass.wav - Bass
    - other.wav - Other instruments
    - vocals.wav - Vocals
    """
    from fastapi.responses import JSONResponse
    audio_io = AudioIO()
    supported_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm", ".mid", ".midi"}

    files = []

    # First, check for original files in storage/uploaded/
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            if file_path.name == "temp.mp3":
                continue

            try:
                info = audio_io.get_audio_info(file_path)

                files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(UPLOAD_DIR.parent)),
                    "size": file_path.stat().st_size,
                    "duration": info["duration"],
                    "samplerate": info["samplerate"],
                    "channels": info["channels"],
                    "extension": file_path.suffix[1:],
                    "source": "uploaded",
                    "is_separated": False,  # This is an original file
                })
            except Exception:
                continue

    # Then, check for separated files in storage/uploaded/separated/
    separated_dir = UPLOAD_DIR / "separated"
    if separated_dir.exists():
        for file_path in separated_dir.glob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in supported_extensions:
                continue

            try:
                # MIDI files don't have audio info, skip getting info for them
                if file_path.suffix.lower() in [".mid", ".midi"]:
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(UPLOAD_DIR.parent)),
                        "size": file_path.stat().st_size,
                        "duration": 0,
                        "samplerate": 0,
                        "channels": 0,
                        "extension": file_path.suffix[1:],
                        "source": "uploaded",
                        "is_separated": True,
                        "is_midi": True,  # Mark as MIDI file
                    })
                else:
                    info = audio_io.get_audio_info(file_path)
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(UPLOAD_DIR.parent)),
                        "size": file_path.stat().st_size,
                        "duration": info["duration"],
                        "samplerate": info["samplerate"],
                        "channels": info["channels"],
                        "extension": file_path.suffix[1:],
                        "source": "uploaded",
                        "is_separated": True,
                        "is_midi": False,
                    })
            except Exception:
                continue

    files.sort(key=lambda x: x["name"])

    return JSONResponse(
        content=files,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        }
    )


@router.get("/status", summary="Check upload status")
async def get_upload_status():
    """
    Check uploaded/ directory status

    Returns:
        - has_uploaded: Whether there are files in uploaded/ (original files)
        - has_separated: Whether there are separation results in separated/ folder
    """
    upload_dir = UPLOAD_DIR
    separated_dir = UPLOAD_DIR / "separated"

    # Check for original files in upload directory (exclude temp.mp3)
    has_uploaded = False
    if upload_dir.exists():
        for file_path in upload_dir.iterdir():
            if file_path.is_file() and file_path.name != "temp.mp3":
                has_uploaded = True
                break

    # Check for separated tracks in separated/ subdirectory
    has_separated = False
    if separated_dir.exists():
        for file_path in separated_dir.iterdir():
            if file_path.is_file() and file_path.name != "temp.mp3":
                has_separated = True
                break

    return {
        "has_uploaded": has_uploaded,
        "has_separated": has_separated,
        "uploaded_dir_exists": upload_dir.exists(),
        "separated_dir_exists": separated_dir.exists(),
    }


@router.get("/audio/{filename}", summary="Get audio file")
async def get_audio_file(filename: str):
    """
    Get audio file for playback

    Args:
        filename: Audio file name (e.g., "drum.wav")

    Returns:
        Audio file stream
    """
    # Search order:
    # 1. storage/uploaded/separated/ (separated tracks)
    # 2. storage/uploaded/ (original files)
    # 3. storage/demo/ (demo files)

    separated_dir = UPLOAD_DIR / "separated"
    uploaded_dir = UPLOAD_DIR

    # Try separated/ directory first
    file_path = separated_dir / filename

    # Security check for separated directory
    try:
        file_path = file_path.resolve()
        separated_dir_resolved = separated_dir.resolve()
        demo_dir = DEMO_DIR.resolve()

        allowed_path = False
        for allowed_dir in [separated_dir_resolved, demo_dir]:
            if str(file_path).startswith(str(allowed_dir)):
                allowed_path = True
                break

        if not allowed_path:
            raise HTTPException(403, "Access denied for this path")
    except Exception:
        raise HTTPException(403, "Path resolution error")

    # If not found in separated/, try uploaded/ directory
    if not file_path.exists():
        file_path = uploaded_dir / filename

        # Security check for uploaded directory
        try:
            file_path = file_path.resolve()
            uploaded_dir_resolved = uploaded_dir.resolve()
            if not str(file_path).startswith(str(uploaded_dir_resolved)):
                raise HTTPException(403, "Access denied for this path")
        except Exception:
            raise HTTPException(403, "Path resolution error")

    # If not found in uploaded/, try demo directory
    if not file_path.exists():
        file_path = DEMO_DIR / filename

        # Verify demo path is still allowed
        try:
            file_path = file_path.resolve()
            demo_dir = DEMO_DIR.resolve()
            if not str(file_path).startswith(str(demo_dir)):
                raise HTTPException(403, "Access denied for this path")
        except Exception:
            raise HTTPException(403, "Path resolution error")

    if not file_path.exists():
        raise HTTPException(404, f"File not found: {filename}")

    if not file_path.is_file():
        raise HTTPException(400, "Not a file")

    # Set media type based on extension
    ext = file_path.suffix.lower()
    media_type = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".mid": "audio/midi",
        ".midi": "audio/midi",
    }.get(ext, "application/octet-stream")

    # For MIDI files, use attachment to trigger browser download
    content_disposition = "attachment" if ext in [".mid", ".midi"] else "inline"

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
        # Enable range requests (support seek) and inline playback
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": content_disposition,  # MIDI: attachment, Audio: inline
        }
    )


@router.get("/info/{filename}", summary="Get audio file info")
async def get_audio_info(filename: str):
    """
    Get detailed information for a single audio file

    Args:
        filename: Audio file name

    Returns:
        File information
    """
    # Search order:
    # 1. storage/uploaded/separated/ (separated tracks)
    # 2. storage/uploaded/ (original files)
    # 3. storage/demo/ (demo files)

    separated_dir = UPLOAD_DIR / "separated"
    uploaded_dir = UPLOAD_DIR

    # Try separated/ directory first
    file_path = separated_dir / filename

    # Security check for separated directory
    try:
        file_path = file_path.resolve()
        separated_dir_resolved = separated_dir.resolve()
        demo_dir = DEMO_DIR.resolve()

        allowed_path = False
        for allowed_dir in [separated_dir_resolved, demo_dir]:
            if str(file_path).startswith(str(allowed_dir)):
                allowed_path = True
                break

        if not allowed_path:
            raise HTTPException(403, "Access denied for this path")
    except Exception:
        raise HTTPException(403, "Path resolution error")

    # If not found in separated/, try uploaded/ directory
    if not file_path.exists():
        file_path = uploaded_dir / filename

        # Security check for uploaded directory
        try:
            file_path = file_path.resolve()
            uploaded_dir_resolved = uploaded_dir.resolve()
            if not str(file_path).startswith(str(uploaded_dir_resolved)):
                raise HTTPException(403, "Access denied for this path")
        except Exception:
            raise HTTPException(403, "Path resolution error")

    # If not found in uploaded/, try demo directory
    if not file_path.exists():
        file_path = DEMO_DIR / filename

        # Verify demo path is still allowed
        try:
            file_path = file_path.resolve()
            demo_dir = DEMO_DIR.resolve()
            if not str(file_path).startswith(str(demo_dir)):
                raise HTTPException(403, "Access denied for this path")
        except Exception:
            raise HTTPException(403, "Path resolution error")

    if not file_path.exists():
        raise HTTPException(404, f"File not found: {filename}")

    try:
        audio_io = AudioIO()
        info = audio_io.get_audio_info(file_path)

        # Determine source
        source = "uploaded" if str(file_path).startswith(str(UPLOAD_DIR)) else "demo"

        return {
            "name": file_path.name,
            "size": file_path.stat().st_size,
            "samplerate": info["samplerate"],
            "channels": info["channels"],
            "duration": info["duration"],
            "format": info["format"],
            "subtype": info["subtype"],
            "source": source,
        }

    except Exception as e:
        raise HTTPException(500, f"Unable to read file info: {str(e)}")


@router.get("/audio/original/{filename}", summary="Get original audio file")
async def get_original_audio(filename: str):
    """
    Get original audio file from storage/uploaded/ (for playback preview)

    Args:
        filename: Audio file name

    Returns:
        Original audio file stream
    """
    file_path = UPLOAD_DIR / filename

    # Security check: prevent path traversal
    try:
        file_path = file_path.resolve()
        upload_dir_resolved = UPLOAD_DIR.resolve()
        if not str(file_path).startswith(str(upload_dir_resolved)):
            raise HTTPException(403, "Access denied for this path")
    except Exception:
        raise HTTPException(403, "Path resolution error")

    if not file_path.exists():
        raise HTTPException(404, f"File not found: {filename}")

    if not file_path.is_file():
        raise HTTPException(400, "Not a file")

    # Set media type based on extension
    ext = file_path.suffix.lower()
    media_type = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
        ".mid": "audio/midi",
        ".midi": "audio/midi",
    }.get(ext, "application/octet-stream")

    # For MIDI files, use attachment to trigger browser download
    content_disposition = "attachment" if ext in [".mid", ".midi"] else "inline"

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
        # Enable range requests (support seek) and inline playback
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": content_disposition,  # MIDI: attachment, Audio: inline
        }
    )
