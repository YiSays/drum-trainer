"""
FastAPI 主服务器

智能鼓声分离与音乐理解服务
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import torch
import datetime

# 导入端点
from api.endpoints import separation, analysis, generation, tracks, youtube
from api.models import HealthResponse

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
        "timestamp": datetime.datetime.now().isoformat(),
        "device": device,
        "model_loaded": model_loaded
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


@app.post("/separation/separate_by_name", summary="分离已上传的文件")
async def separate_by_name(
    filename: str = Form(..., description="要分离的文件名"),
    chunk_duration: float = Form(30.0, description="分段处理时长（秒）")
):
    """
    分离已上传到 storage/uploaded/ 的文件

    用于前端：用户先上传文件预览，然后点击处理
    """
    from core.separator import DrumSeparator
    import time
    import shutil

    UPLOAD_DIR = Path("storage/uploaded")

    start_time = time.time()

    # 检查文件是否存在
    uploaded_file = UPLOAD_DIR / filename
    if not uploaded_file.exists():
        raise HTTPException(404, f"文件不存在: {filename}")

    # 创建分离目录
    separated_dir = UPLOAD_DIR / "separated"
    separated_dir.mkdir(parents=True, exist_ok=True)

    # 移动文件到 separated/temp.mp3
    temp_file = separated_dir / "temp.mp3"
    shutil.move(str(uploaded_file), str(temp_file))

    try:
        # 运行分离
        separator = DrumSeparator()
        results = separator.separate(temp_file, separated_dir, chunk_duration=chunk_duration)

        processing_time = time.time() - start_time

        # 清理 temp 文件
        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "message": "分离完成",
            "processing_time": round(processing_time, 2),
            "output_dir": str(separated_dir),
            "files": results,
        }

    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        shutil.rmtree(separated_dir, ignore_errors=True)
        raise HTTPException(500, f"分离失败: {str(e)}")


@app.post("/separation/clear", summary="清除上传文件")
async def clear_uploaded():
    """
    清除 storage/uploaded/ 目录及其所有内容
    """
    UPLOAD_DIR = Path("storage/uploaded")

    if UPLOAD_DIR.exists():
        import shutil
        shutil.rmtree(UPLOAD_DIR)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    return {"status": "success", "message": "上传文件已清除"}


@app.get("/info", summary="系统信息")
async def info():
    """获取系统信息"""
    info = {
        "torch_version": torch.__version__,
        "device": "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu"),
        "metal_available": torch.backends.mps.is_available(),
        "cuda_available": torch.cuda.is_available(),
        "python_version": "3.10+",
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
        return HTMLResponse(content=f.read())


@app.get("/ui/css/style.css", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui_css():
    """Serve CSS file"""
    css_path = WEB_UI_DIR / "css" / "style.css"
    if not css_path.exists():
        raise HTTPException(404, "CSS not found")

    with open(css_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="text/css")


@app.get("/ui/js/app.js", response_class=HTMLResponse, include_in_schema=False)
async def serve_ui_js():
    """Serve JavaScript file"""
    js_path = WEB_UI_DIR / "js" / "app.js"
    if not js_path.exists():
        raise HTTPException(404, "JavaScript not found")

    with open(js_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), media_type="application/javascript")


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

    print("")
    print("🔗 API 地址: http://localhost:8000")
    print("📄 文档: http://localhost:8000/docs")
    print("📝 ReDoc: http://localhost:8000/redoc")
    print("🖥️  Web UI: http://localhost:8000/ui")
    print("")
    print("=" * 60)

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
