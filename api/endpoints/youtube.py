"""
YouTube 下载和分离端点

支持从 YouTube URL 下载音频并进行鼓声分离
使用 storage/uploaded/ 作为主目录
分离结果保存在 storage/uploaded/separated/ 子目录
"""

from fastapi import APIRouter, HTTPException, Body, Form
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from typing import Optional, Dict
import json
import shutil

from core.youtube_downloader import YouTubeDownloader
from core.separator import DrumSeparator
from core.audio_io import AudioIO

router = APIRouter(prefix="/youtube", tags=["YouTube"])

# NEW: Upload directory (main storage for uploads)
UPLOAD_DIR = Path("storage/uploaded")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/download", summary="下载 YouTube 音频")
async def download_youtube_audio(
    url: str = Body(..., description="YouTube 视频 URL"),
    name: Optional[str] = Body(None, description="输出文件名 (可选)")
):
    """
    从 YouTube 下载音频并保存到 storage/uploaded/

    Args:
        url: YouTube 视频 URL
        name: 输出文件名 (不含扩展名)

    Returns:
        下载信息和文件路径
    """
    try:
        downloader = YouTubeDownloader(UPLOAD_DIR)
        result = downloader.download_audio(url, name)

        return {
            "status": "success",
            "message": "音频下载成功",
            "data": result
        }

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"下载失败: {str(e)}")


@router.post("/separate", summary="下载并分离 YouTube 音频")
async def separate_youtube_audio(
    url: str = Body(..., description="YouTube 视频 URL"),
    name: Optional[str] = Body(None, description="输出文件名 (可选)"),
    chunk_size: int = Body(30, description="音频分段处理时长 (秒)")
):
    """
    从 YouTube 下载音频并进行鼓声分离 (完整流程)

    下载文件到 storage/uploaded/
    移动到 storage/uploaded/separated/temp.mp3 进行分离
    分离结果保存在 storage/uploaded/separated/ 目录

    Args:
        url: YouTube 视频 URL
        name: 输出文件名 (不含扩展名)
        chunk_size: 音频分段处理时长 (秒)

    Returns:
        下载信息、分离结果和文件路径
    """
    try:
        # 步骤 1: 下载音频到 storage/uploaded/
        print(f"步骤 1: 下载 YouTube 音频")
        downloader = YouTubeDownloader(UPLOAD_DIR)
        download_result = downloader.download_audio(url, name)

        audio_path = Path(download_result["file_path"])

        # 步骤 2: Create separated directory and COPY file (keep original for playback)
        print(f"步骤 2: 复制文件进行处理（保留原文件）")
        separated_dir = UPLOAD_DIR / "separated"
        separated_dir.mkdir(parents=True, exist_ok=True)

        temp_file = separated_dir / "temp.mp3"
        shutil.copy2(str(audio_path), str(temp_file))

        try:
            # 步骤 3: 分离鼓声
            print(f"步骤 3: 分离鼓声 (chunk_size={chunk_size}s)")
            separator = DrumSeparator()

            # 检查音频时长，如果超过 chunk_size 则会自动分段处理
            audio_io = AudioIO()
            audio_info = audio_io.get_audio_info(temp_file)
            duration = audio_info["duration"]

            if duration > chunk_size:
                print(f"音频较长 ({duration}s)，将分段处理...")

            # 执行分离 - 保存到 separated_dir
            separator.separate(
                audio_path=temp_file,
                output_dir=separated_dir,
                chunk_size=chunk_size
            )

            # 步骤 4: 收集分离结果
            print(f"步骤 4: 收集分离结果")
            separated_files = {}
            for file in separated_dir.glob("*.wav"):
                key = file.stem  # e.g., "drum", "no_drums", "bass", etc.
                separated_files[key] = str(file.relative_to(UPLOAD_DIR.parent))

            # 步骤 5: 清理 temp.mp3
            temp_file.unlink(missing_ok=True)

            # 构建完整响应
            result = {
                "status": "success",
                "message": "YouTube 音频下载并分离成功",
                "original": download_result,
                "separated": separated_files,
                "processing_time": audio_info.get("duration", 0),
            }

            print(f"✅ 完整处理完成")
            print(f"   原始音频: {audio_path}")
            print(f"   分离结果: {separated_dir}")

            return result

        except Exception as e:
            # Cleanup on error
            if temp_file.exists():
                temp_file.unlink()
            shutil.rmtree(separated_dir, ignore_errors=True)
            raise

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"处理失败: {str(e)}")


@router.get("/list", summary="列出 storage/uploaded/ 中的文件")
async def list_uploaded_files():
    """
    列出 storage/uploaded/ 目录中的文件

    Returns:
        文件列表
    """
    supported_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".webm"}
    files = []

    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                # Skip temp files
                if file_path.name == "temp.mp3":
                    continue

                try:
                    audio_io = AudioIO()
                    info = audio_io.get_audio_info(file_path)

                    files.append({
                        "name": file_path.name,
                        "path": str(file_path.relative_to(UPLOAD_DIR.parent)),
                        "size": file_path.stat().st_size,
                        "duration": info["duration"],
                        "samplerate": info["samplerate"],
                        "channels": info["channels"],
                        "extension": file_path.suffix[1:],
                    })
                except Exception:
                    continue

    files.sort(key=lambda x: x["name"])
    return {
        "status": "success",
        "count": len(files),
        "files": files
    }
