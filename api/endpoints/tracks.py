"""
Tracks 端点 - 用于 Flutter Web App 的文件浏览和音频播放

使用 storage/uploaded/ 作为主目录
分离结果保存在 storage/uploaded/separated/ 子目录
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Optional
import soundfile as sf

from core.audio_io import AudioIO

router = APIRouter(prefix="/tracks", tags=["Tracks"])

# Upload directory (main storage for uploads)
UPLOAD_DIR = Path("storage/uploaded")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Demo directory (for demo tracks - ignored in current implementation)
DEMO_DIR = Path("storage/demo")


@router.get("/list", summary="列出所有音轨", response_model=List[dict])
async def list_tracks():
    """
    列出 storage/uploaded/ 目录中的文件
    包括: 原始文件 (storage/uploaded/) 和分离文件 (storage/uploaded/separated/)

    **分离输出 (htdemucs 模型)**:
    - drums.wav - 鼓声
    - bass.wav - 贝斯
    - other.wav - 其他乐器
    - vocals.wav - 人声
    """
    from fastapi.responses import JSONResponse
    audio_io = AudioIO()
    supported_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"}

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
        for file_path in separated_dir.glob("*.wav"):
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
                    "is_separated": True,  # This is a separated track
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


@router.get("/status", summary="检查上传状态")
async def get_upload_status():
    """
    检查 uploaded/ 目录状态

    Returns:
        - has_uploaded: 是否有文件在 uploaded/ (原始文件)
        - has_separated: 是否有分离结果在 separated/ 文件夹
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


@router.get("/audio/{filename}", summary="获取音频文件")
async def get_audio_file(filename: str):
    """
    获取音频文件用于播放

    Args:
        filename: 音频文件名 (e.g., "drum.wav")

    Returns:
        音频文件流
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
            raise HTTPException(403, "不允许访问此路径")
    except Exception:
        raise HTTPException(403, "路径解析错误")

    # If not found in separated/, try uploaded/ directory
    if not file_path.exists():
        file_path = uploaded_dir / filename

        # Security check for uploaded directory
        try:
            file_path = file_path.resolve()
            uploaded_dir_resolved = uploaded_dir.resolve()
            if not str(file_path).startswith(str(uploaded_dir_resolved)):
                raise HTTPException(403, "不允许访问此路径")
        except Exception:
            raise HTTPException(403, "路径解析错误")

    # If not found in uploaded/, try demo directory
    if not file_path.exists():
        file_path = DEMO_DIR / filename

        # Verify demo path is still allowed
        try:
            file_path = file_path.resolve()
            demo_dir = DEMO_DIR.resolve()
            if not str(file_path).startswith(str(demo_dir)):
                raise HTTPException(403, "不允许访问此路径")
        except Exception:
            raise HTTPException(403, "路径解析错误")

    if not file_path.exists():
        raise HTTPException(404, f"文件不存在: {filename}")

    if not file_path.is_file():
        raise HTTPException(400, "不是文件")

    # 根据扩展名设置媒体类型
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
        # 启用范围请求（支持seek）和内联播放
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",  # Allow browser to play audio inline
        }
    )


@router.get("/info/{filename}", summary="获取音频文件信息")
async def get_audio_info(filename: str):
    """
    获取单个音频文件的详细信息

    Args:
        filename: 音频文件名

    Returns:
        文件信息
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
            raise HTTPException(403, "不允许访问此路径")
    except Exception:
        raise HTTPException(403, "路径解析错误")

    # If not found in separated/, try uploaded/ directory
    if not file_path.exists():
        file_path = uploaded_dir / filename

        # Security check for uploaded directory
        try:
            file_path = file_path.resolve()
            uploaded_dir_resolved = uploaded_dir.resolve()
            if not str(file_path).startswith(str(uploaded_dir_resolved)):
                raise HTTPException(403, "不允许访问此路径")
        except Exception:
            raise HTTPException(403, "路径解析错误")

    # If not found in uploaded/, try demo directory
    if not file_path.exists():
        file_path = DEMO_DIR / filename

        # Verify demo path is still allowed
        try:
            file_path = file_path.resolve()
            demo_dir = DEMO_DIR.resolve()
            if not str(file_path).startswith(str(demo_dir)):
                raise HTTPException(403, "不允许访问此路径")
        except Exception:
            raise HTTPException(403, "路径解析错误")

    if not file_path.exists():
        raise HTTPException(404, f"文件不存在: {filename}")

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
        raise HTTPException(500, f"无法读取文件信息: {str(e)}")


@router.get("/audio/original/{filename}", summary="获取原始音频文件")
async def get_original_audio(filename: str):
    """
    从 storage/uploaded/ 获取原始音频文件（用于播放预览）

    Args:
        filename: 音频文件名

    Returns:
        原始音频文件流
    """
    file_path = UPLOAD_DIR / filename

    # Security check: prevent path traversal
    try:
        file_path = file_path.resolve()
        upload_dir_resolved = UPLOAD_DIR.resolve()
        if not str(file_path).startswith(str(upload_dir_resolved)):
            raise HTTPException(403, "不允许访问此路径")
    except Exception:
        raise HTTPException(403, "路径解析错误")

    if not file_path.exists():
        raise HTTPException(404, f"文件不存在: {filename}")

    if not file_path.is_file():
        raise HTTPException(400, "不是文件")

    # 根据扩展名设置媒体类型
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
        # 启用范围请求（支持seek）和内联播放
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": "inline",  # Allow browser to play audio inline
        }
    )
