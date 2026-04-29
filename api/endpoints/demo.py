"""
Demo Tracks endpoint - demo audio files for testing
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from typing import List, Optional
import soundfile as sf

from api.config import get_storage_dir
from core.audio_io import AudioIO

router = APIRouter(prefix="/demo", tags=["Demo"])

# Demo directory (for test tracks)
DEMO_DIR = get_storage_dir() / "demo"


@router.get("/list", summary="List demo tracks", response_model=List[dict])
async def list_demo_tracks():
    """List audio files in the demo directory."""
    audio_io = AudioIO()
    supported_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"}

    files = []

    if DEMO_DIR.exists():
        for file_path in DEMO_DIR.iterdir():
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in supported_extensions:
                continue

            try:
                info = audio_io.get_audio_info(file_path)

                files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(DEMO_DIR.parent)),
                    "size": file_path.stat().st_size,
                    "duration": info["duration"],
                    "samplerate": info["samplerate"],
                    "channels": info["channels"],
                    "extension": file_path.suffix[1:],
                    "source": "demo",
                    "description": _get_file_description(file_path.name)
                })
            except Exception as e:
                print(f"⚠️ Cannot read demo file {file_path.name}: {e}")
                continue

    files.sort(key=lambda x: x["name"])

    return JSONResponse(
        content=files,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        }
    )


@router.get("/audio/{filename}", summary="Get demo audio file")
async def get_demo_audio_file(filename: str):
    """Get an audio file from the demo directory for playback."""
    file_path = DEMO_DIR / filename

    try:
        file_path = file_path.resolve()
        demo_dir = DEMO_DIR.resolve()
        if not str(file_path).startswith(str(demo_dir)):
            raise HTTPException(403, "Access denied for this path")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(403, "Path resolution error")

    if not file_path.exists():
        raise HTTPException(404, f"Demo file not found: {filename}")

    if not file_path.is_file():
        raise HTTPException(400, "Not a file")

    ext = file_path.suffix.lower()
    media_type = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
        ".webm": "audio/webm",
    }.get(ext, "application/octet-stream")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",
        }
    )


def _get_file_description(filename: str) -> str:
    """Get file description."""
    descriptions = {
        "drums.wav": "Separated drum track - for drum detection testing",
        "bass.wav": "Separated bass track",
        "vocals.wav": "Separated vocal track",
        "other.wav": "Separated other instruments track",
        "unhidden_light.mp3": "Original audio - Unhidden Light"
    }
    return descriptions.get(filename, "Demo audio file")
