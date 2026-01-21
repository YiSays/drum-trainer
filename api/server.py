"""
FastAPI 主服务器

智能鼓声分离与音乐理解服务
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import torch
import shutil
import asyncio
from datetime import datetime, timedelta

# 导入端点
from api.endpoints import separation, analysis, generation, tracks, youtube
from api.models import HealthResponse

# Upload directory configuration
UPLOAD_DIR = Path("storage/uploaded")
SEPARATED_DIR = UPLOAD_DIR / "separated"

# Cleanup configuration
CLEANUP_AGE_HOURS = 24  # Files older than this will be cleaned up on startup

# 创建应用
app = FastAPI(
    title="🥁 智能鼓声分离与音乐理解 API",
    description="""
    基于AI的音乐分析与鼓演奏生成服务

    **核心功能**:
    - 🎵 鼓声分离 (Demucs AI)
    - 📊 音乐理解 (风格/BPM/结构/节奏)
    - 🥁 智能生成 (纯自动鼓演奏)
    - 🔄 完整处理 (一站式API)

    **优化**:
    - Apple Silicon (Metal加速)
    - uv依赖管理
    - 跨平台支持
    """,
    version="0.1.0",
    contact={
        "name": "Drum Trainer Team",
        "url": "https://github.com/your-repo"
    }
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册端点
app.include_router(separation.router)
app.include_router(analysis.router)
app.include_router(generation.router)
app.include_router(tracks.router)
app.include_router(youtube.router)


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


@app.get("/cleanup", summary="手动清理旧文件", response_model=dict)
async def manual_cleanup(max_age_hours: int = 24):
    """
    手动触发清理旧文件（保留最近N小时的文件）

    Args:
        max_age_hours: 保留多少小时内的文件，默认24小时
    """
    stats = cleanup_old_uploads(max_age_hours)
    return {
        "status": "success",
        "message": f"清理完成",
        **stats
    }


@app.get("/", summary="根路径", response_model=HealthResponse)
async def root():
    """
    API 服务状态检查
    """
    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")

    # 检查核心库是否可用
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


@app.get("/health", summary="健康检查", response_model=HealthResponse)
async def health():
    """服务健康状态"""
    return await root()


@app.get("/download/{file_path:path}", summary="下载文件")
async def download_file(file_path: str):
    """
    下载处理后的文件

    Args:
        file_path: 文件路径（相对于storage目录）
    """
    base_path = Path("storage")
    full_path = base_path / file_path

    # 安全检查：防止路径遍历攻击
    full_path = full_path.resolve()
    if not str(full_path).startswith(str(base_path.resolve())):
        raise HTTPException(403, "不允许访问此路径")

    if not full_path.exists():
        raise HTTPException(404, "文件不存在")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type="audio/wav" if full_path.suffix in [".wav", ".mp3"] else "application/octet-stream"
    )


@app.post("/test/analyze", summary="测试端点")
async def test_analyze(file: UploadFile = File(...)):
    """快速测试分析功能"""
    from core.music_analyzer import MusicAnalyzer
    from core.audio_io import AudioIO
    import tempfile
    import shutil

    temp_dir = Path("storage/temp")
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


@app.post("/upload/preview", summary="上传文件用于预览")
async def upload_preview(file: UploadFile = File(...)):
    """
    上传文件到 storage/uploaded/ 并返回文件信息用于预览

    用于前端：用户上传文件后显示预览信息，然后点击处理
    """
    from core.audio_io import AudioIO
    from fastapi import Form

    UPLOAD_DIR = Path("storage/uploaded")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # 保存文件
    saved_path = UPLOAD_DIR / file.filename
    try:
        with open(saved_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # 获取文件信息
    try:
        audio_io = AudioIO()
        info = audio_io.get_audio_info(saved_path)

        return {
            "status": "success",
            "message": "文件上传成功",
            "file_info": {
                "name": file.filename,
                "path": str(saved_path.relative_to(UPLOAD_DIR.parent)),
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
        raise HTTPException(500, f"无法读取文件信息: {str(e)}")


@app.get("/info", summary="系统信息")
async def info():
    """获取系统信息"""
    info = {
        "torch_version": torch.__version__,
        "device": "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu"),
        "metal_available": torch.backends.mps.is_available(),
        "cuda_available": torch.cuda.is_available(),
        "python_version": "3.10+",
        "default_model": "htdemucs",
        "available_models": ["htdemucs", "htdemucs_ft", "htdemucs_6s"],
        "shifts": 1,
        "model_cache_dir": "storage/models",
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


if __name__ == "__main__":
    import uvicorn

    print("🚀 启动 Drum Trainer API 服务...")
    print("=" * 60)
    print("")
    print("📊 系统信息:")
    print(f"  - PyTorch: {torch.__version__}")

    if torch.backends.mps.is_available():
        print("  - 设备: Apple Silicon (Metal加速) ✅")
    elif torch.cuda.is_available():
        print("  - 设备: CUDA GPU ✅")
    else:
        print("  - 设备: CPU (性能较慢)")

    print(f"  - 默认模型: htdemucs (4声道)")
    print(f"  - 存储目录: storage/uploaded/")
    print("")
    print("🔗 API 地址: http://localhost:8000")
    print("📄 文档: http://localhost:8000/docs")
    print("📝 ReDoc: http://localhost:8000/redoc")
    print("🖥️  Web UI: http://localhost:8000/ui")
    print("")
    print("🧹 清理: 老文件(>24小时)将在启动时自动清理")
    print("      手动清理: GET /cleanup?max_age_hours=N")
    print("")
    print("=" * 60)

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
