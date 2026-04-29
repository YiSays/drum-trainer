"""
FastAPI Main Server

Smart Drum Separation & Music Analysis Service
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import torch
import shutil
import asyncio
from datetime import datetime, timedelta

# Import endpoints
from api.endpoints import separation, analysis, generation, tracks, youtube, transcription, demo, transcription_ast, transcription_torch
from api.models import HealthResponse
from api.config import get_storage_dir

# Upload directory configuration
UPLOAD_DIR = get_storage_dir() / "uploaded"
SEPARATED_DIR = UPLOAD_DIR / "separated"

# Cleanup configuration
CLEANUP_AGE_HOURS = 24  # Files older than this will be cleaned up on startup

# Create application
app = FastAPI(
    title="🥁 Smart Drum Separation & Music Analysis API",
    description="""
    AI-powered Music Analysis & Drum Performance Generation Service

    **Core Features**:
    - 🎵 Drum Separation (Demucs AI)
    - 📊 Music Analysis (Style/BPM/Structure/Rhythm)
    - 🥁 Smart Generation (Fully Automatic Drum Performance)
    - 🔄 Full Pipeline (One-stop API)

    **Optimizations**:
    - Apple Silicon (Metal Acceleration)
    - uv Dependency Management
    - Cross-platform Support
    """,
    version="0.1.0",
    contact={
        "name": "Drum Trainer Team",
        "url": "https://github.com/your-repo"
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(separation.router)
app.include_router(analysis.router)
app.include_router(generation.router)
app.include_router(tracks.router)
app.include_router(youtube.router)
app.include_router(transcription.router)
app.include_router(transcription_ast.router)
app.include_router(transcription_torch.router)
app.include_router(demo.router)


# ============================================
# Cleanup Utilities
# ============================================

def cleanup_old_uploads(max_age_hours: int = CLEANUP_AGE_HOURS) -> dict:
    """
    Clean up old files in storage/uploaded/ and storage/uploaded/separated/

    Args:
        max_age_hours: Delete files older than this many hours

    Returns:
        Dict with cleanup statistics
    """
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    stats = {
        "deleted_files": [],
        "deleted_dirs": [],
        "kept_files": [],
        "errors": [],
        "total_deleted_size": 0
    }

    # Ensure directories exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SEPARATED_DIR.mkdir(parents=True, exist_ok=True)

    # Clean up files in uploaded/
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file() and file_path.name != "temp.mp3":
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_time:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    stats["deleted_files"].append(str(file_path.name))
                    stats["total_deleted_size"] += file_size
                else:
                    stats["kept_files"].append(str(file_path.name))
            except Exception as e:
                stats["errors"].append(f"Error deleting {file_path}: {str(e)}")

    # Clean up files in separated/
    if SEPARATED_DIR.exists():
        for file_path in SEPARATED_DIR.iterdir():
            if file_path.is_file():
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_time:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        stats["deleted_files"].append(f"separated/{file_path.name}")
                        stats["total_deleted_size"] += file_size
                    else:
                        stats["kept_files"].append(f"separated/{file_path.name}")
                except Exception as e:
                    stats["errors"].append(f"Error deleting {file_path}: {str(e)}")

    # Try to delete empty separated/ directory
    try:
        if SEPARATED_DIR.exists() and not any(SEPARATED_DIR.iterdir()):
            SEPARATED_DIR.rmdir()
            stats["deleted_dirs"].append("separated/")
    except Exception:
        pass  # Directory not empty or other error

    return stats


@app.on_event("startup")
async def startup_event():
    """
    Clean up old files on server startup
    """
    print("=" * 60)
    print("🚀 Startup: Cleaning up old files...")
    print(f"   Age threshold: {CLEANUP_AGE_HOURS} hours")

    # Create directories if they don't exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SEPARATED_DIR.mkdir(parents=True, exist_ok=True)

    # Clean up old files
    try:
        stats = cleanup_old_uploads(CLEANUP_AGE_HOURS)

        if stats["deleted_files"] or stats["deleted_dirs"]:
            print(f"   ✅ Deleted {len(stats['deleted_files'])} files")
            for f in stats["deleted_files"]:
                print(f"      - {f}")
            if stats["total_deleted_size"] > 0:
                size_mb = stats["total_deleted_size"] / (1024 * 1024)
                print(f"   🗑️  Freed {size_mb:.1f} MB")

        if stats["kept_files"]:
            print(f"   📦 Kept {len(stats['kept_files'])} files (recent)")

        if stats["errors"]:
            print(f"   ⚠️  Errors: {len(stats['errors'])}")
            for e in stats["errors"]:
                print(f"      - {e}")

    except Exception as e:
        print(f"   ⚠️  Cleanup error: {str(e)}")

    print("=" * 60)


@app.get("/cleanup", summary="Manual cleanup of old files", response_model=dict)
async def manual_cleanup(max_age_hours: int = 24):
    """
    Manually trigger cleanup of old files (keeps files from the last N hours)

    Args:
        max_age_hours: How many hours of files to keep, default 24 hours
    """
    stats = cleanup_old_uploads(max_age_hours)
    return {
        "status": "success",
        "message": "Cleanup complete",
        **stats
    }


@app.get("/", summary="Root endpoint", response_model=HealthResponse)
async def root():
    """
    API service status check
    """
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")

    # Check if core libraries are available
    try:
        import demucs
        model_loaded = True
    except:
        model_loaded = False

    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "device": device,
        "model_loaded": model_loaded,
        "default_model": "htdemucs",
        "shifts": 1
    }


@app.get("/health", summary="Health check", response_model=HealthResponse)
async def health():
    """Service health status"""
    return await root()


@app.get("/download/{file_path:path}", summary="Download file")
async def download_file(file_path: str):
    """
    Download processed files

    Args:
        file_path: File path (relative to storage directory)
    """
    base_path = get_storage_dir()
    full_path = base_path / file_path

    # Security check: prevent path traversal attacks
    full_path = full_path.resolve()
    if not str(full_path).startswith(str(base_path.resolve())):
        raise HTTPException(403, "Access denied for this path")

    if not full_path.exists():
        raise HTTPException(404, "File not found")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type="audio/wav" if full_path.suffix in [".wav", ".mp3"] else "application/octet-stream"
    )


@app.post("/test/analyze", summary="Test endpoint")
async def test_analyze(file: UploadFile = File(...)):
    """Quick test for analysis functionality"""
    from core.music_analyzer import MusicAnalyzer
    from core.audio_io import AudioIO
    import tempfile
    import shutil

    temp_dir = get_storage_dir() / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    temp_file = temp_dir / f"test_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        analyzer = MusicAnalyzer()
        result = analyzer.analyze(temp_file)

        temp_file.unlink(missing_ok=True)

        return {"status": "success", "result": result}
    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(500, str(e))


@app.post("/upload/preview", summary="Upload file for preview")
async def upload_preview(file: UploadFile = File(...)):
    """
    Upload file to storage/uploaded/ and return file info for preview

    Used by frontend: user uploads file for preview, then clicks to process
    """
    from core.audio_io import AudioIO
    from fastapi import Form

    upload_dir = get_storage_dir() / "uploaded"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    saved_path = upload_dir / file.filename
    try:
        with open(saved_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Get file info
    try:
        audio_io = AudioIO()
        info = audio_io.get_audio_info(saved_path)

        return {
            "status": "success",
            "message": "File uploaded successfully",
            "file_info": {
                "name": file.filename,
                "path": str(saved_path.relative_to(upload_dir.parent)),
                "size": saved_path.stat().st_size,
                "duration": info["duration"],
                "samplerate": info["samplerate"],
                "channels": info["channels"],
            }
        }

    except Exception as e:
        # Cleanup on error
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(500, f"Unable to read file info: {str(e)}")


@app.get("/info", summary="System information")
async def info():
    """Get system information"""
    info = {
        "torch_version": torch.__version__,
        "device": "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu"),
        "metal_available": torch.backends.mps.is_available(),
        "cuda_available": torch.cuda.is_available(),
        "python_version": "3.10+",
        "default_model": "htdemucs",
        "available_models": ["htdemucs", "htdemucs_ft", "htdemucs_6s"],
        "shifts": 1,
        "model_cache_dir": str(get_storage_dir() / "models"),
    }
    return info


# ============================================
# Web UI Endpoints
# ============================================

WEB_UI_DIR = Path("web_ui")


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui_index():
    """Serve the main web UI page"""
    index_path = WEB_UI_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(404, "Web UI not found. Run setup first.")

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Add cache-busting header and prevent browser caching
        return HTMLResponse(
            content=content,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )


@app.get("/ui/css/style.css", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui_css():
    """Serve CSS file"""
    css_path = WEB_UI_DIR / "css" / "style.css"
    if not css_path.exists():
        raise HTTPException(404, "CSS not found")

    with open(css_path, "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            media_type="text/css",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            }
        )


@app.get("/ui/js/app.js", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui_js():
    """Serve JavaScript file"""
    js_path = WEB_UI_DIR / "js" / "app.js"
    if not js_path.exists():
        raise HTTPException(404, "JavaScript not found")

    with open(js_path, "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            }
        )


@app.get("/ui/test_bench.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_test_bench_html():
    """Serve Test Bench UI page"""
    path = WEB_UI_DIR / "test_bench.html"
    if not path.exists():
        raise HTTPException(404, "Test Bench UI not found")

    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            }
        )


@app.get("/ui/js/test_bench.js", response_class=HTMLResponse, include_in_schema=False)
async def serve_test_bench_js():
    """Serve Test Bench JavaScript file"""
    path = WEB_UI_DIR / "js" / "test_bench.js"
    if not path.exists():
        raise HTTPException(404, "Test Bench JS not found")

    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            }
        )


@app.get("/ui/test_bench_v2.html", response_class=HTMLResponse, include_in_schema=False)
@app.get("/web_ui/test_bench_v2.html", response_class=HTMLResponse, include_in_schema=False)
async def serve_test_bench_v2_html():
    """Serve Test Bench v2 UI page"""
    path = WEB_UI_DIR / "test_bench_v2.html"
    if not path.exists():
        raise HTTPException(404, "Test Bench v2 UI not found")

    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            }
        )


@app.get("/ui/js/test_bench_v2.js", response_class=HTMLResponse, include_in_schema=False)
@app.get("/web_ui/js/test_bench_v2.js", response_class=HTMLResponse, include_in_schema=False)
async def serve_test_bench_v2_js():
    """Serve Test Bench v2 JavaScript file"""
    path = WEB_UI_DIR / "js" / "test_bench_v2.js"
    if not path.exists():
        raise HTTPException(404, "Test Bench v2 JS not found")

    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            }
        )


@app.get("/ui/test_bench_v3.html", response_class=HTMLResponse, include_in_schema=False)
@app.get("/test", response_class=HTMLResponse, include_in_schema=False)
async def serve_test_bench_v3_html():
    """Serve Test Bench v3 (Enhanced Pipeline) UI page"""
    path = WEB_UI_DIR / "test_bench_v3.html"
    if not path.exists():
        raise HTTPException(404, "Test Bench v3 UI not found")

    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(
            content=f.read(),
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            }
        )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Drum Trainer API service...")
    print("=" * 60)
    print("")
    print("📊 System Information:")
    print(f"  - PyTorch: {torch.__version__}")

    if torch.backends.mps.is_available():
        print("  - Device: Apple Silicon (Metal Acceleration) ✅")
    elif torch.cuda.is_available():
        print("  - Device: CUDA GPU ✅")
    else:
        print("  - Device: CPU (slower performance)")

    print("  - Default model: htdemucs (4-stem)")
    print("  - Storage directory: storage/uploaded/")
    print("")
    print("🔗 API URL: http://localhost:8000")
    print("📄 Docs: http://localhost:8000/docs")
    print("📝 ReDoc: http://localhost:8000/redoc")
    print("🖥️  Web UI: http://localhost:8000/ui")
    print("")
    print("🧹 Cleanup: Old files (>24 hours) will be automatically cleaned on startup")
    print("      Manual cleanup: GET /cleanup?max_age_hours=N")
    print("")
    print("=" * 60)

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
