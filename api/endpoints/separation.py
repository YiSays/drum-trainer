"""
分离端点 - 鼓声分离功能
使用 storage/uploaded/ 作为主目录
分离结果存储在 storage/uploaded/separated/ 子目录
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import StreamingResponse
from pathlib import Path
import shutil
import time
import json
import asyncio
import queue

from core.separator import DrumSeparator
from core.audio_io import AudioIO

router = APIRouter(prefix="/separation", tags=["分离"])

# NEW: Upload directory (main storage for uploads)
UPLOAD_DIR = Path("storage/uploaded")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/separate", summary="分离鼓声")
async def separate_drums(
    file: UploadFile = File(..., description="音频文件 (mp3, wav, flac)"),
    chunk_duration: float = Form(30.0, description="分段处理时长（秒），避免内存溢出"),
    model: str = Form("htdemucs", description="分离模型: htdemucs (4声道) 或 htdemucs_ft (微调4声道) 或 htdemucs_6s (6声道)"),
    shifts: int = Form(1, description="时间偏移增强次数")
):
    """
    分离音频中的鼓声部分

    **处理流程**:
    1. 保存文件到 storage/uploaded/filename
    2. **复制**到 storage/uploaded/separated/temp.mp3 进行分离（不删除原文件）
    3. 运行分离 (结果保存在 separated/ 目录)
    4. 删除 temp.mp3

    **模型选择**:
    - `htdemucs`: 4声道分离 (drums, bass, other, vocals) - **推荐**
    - `htdemucs_ft`: 微调版4声道分离 (drums, bass, other, vocals)
    - `htdemucs_6s`: 6声道分离 (drums, bass, piano, guitar, other, vocals)

    **质量增强**:
    - `shifts`: 时间偏移增强次数
    """
    start_time = time.time()

    # 验证文件类型
    if not file.content_type.startswith("audio/"):
        raise HTTPException(400, "请上传音频文件")

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
        results = separator.separate(temp_file, separated_dir, chunk_duration=chunk_duration, shifts=shifts)

        processing_time = time.time() - start_time

        # Step 4: Cleanup temp file
        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "message": "分离完成",
            "processing_time": round(processing_time, 2),
            "output_dir": str(separated_dir),
            "files": results,
            "note": "文件将保存在服务器上，可通过链接下载"
        }

    except Exception as e:
        # Cleanup on error
        if temp_file.exists():
            temp_file.unlink()
        shutil.rmtree(separated_dir, ignore_errors=True)
        raise HTTPException(500, f"分离失败: {str(e)}")


@router.post("/preview", summary="快速预览")
async def preview_separation(
    file: UploadFile = File(...),
    shifts: int = Form(1, description="时间偏移增强次数")
):
    """
    快速预览分离结果（不保存文件）

    只分析前30秒，返回各声部时长信息

    **质量增强**:
    - `shifts`: 时间偏移增强次数，值越高分离质量越好（默认2）
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

        # 清理
        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "preview": durations,
            "note": "预览基于前30秒"
        }

    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(500, f"预览失败: {str(e)}")


@router.post("/clear", summary="清除上传文件")
async def clear_uploaded():
    """
    清除 storage/uploaded/ 目录及其所有内容
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

    return {"status": "success", "message": "上传文件已清除"}


@router.post("/separate_by_name", summary="分离已上传的文件")
async def separate_by_name(
    filename: str = Form(..., description="要分离的文件名"),
    chunk_duration: float = Form(30.0, description="分段处理时长（秒）"),
    model: str = Form("htdemucs", description="分离模型: htdemucs (4声道) 或 htdemucs_ft (微调4声道) 或 htdemucs_6s (6声道)"),
    shifts: int = Form(1, description="时间偏移增强次数")
):
    """
    分离已上传到 storage/uploaded/ 的文件

    用于前端：用户先上传文件预览，然后点击处理

    文件将**复制**到 storage/uploaded/separated/temp.mp3 进行分离（不删除原文件）
    分离结果保存在 storage/uploaded/separated/ 目录

    **模型选择**:
    - `htdemucs`: 4声道分离 (drums, bass, other, vocals) - **推荐**
    - `htdemucs_ft`: 微调版4声道分离 (drums, bass, other, vocals)
    - `htdemucs_6s`: 6声道分离 (drums, bass, piano, guitar, other, vocals)

    **质量增强**:
    - `shifts`: 时间偏移增强次数
    """
    start_time = time.time()

    # Check if file exists
    uploaded_file = UPLOAD_DIR / filename
    if not uploaded_file.exists():
        raise HTTPException(404, f"文件不存在: {filename}")

    # Create separated directory
    separated_dir = UPLOAD_DIR / "separated"
    separated_dir.mkdir(parents=True, exist_ok=True)

    # Copy file instead of move - keep original for playback during processing
    temp_file = separated_dir / "temp.mp3"
    shutil.copy2(str(uploaded_file), str(temp_file))

    try:
        # Run separation - save results to separated_dir
        separator = DrumSeparator(model_name=model)
        results = separator.separate(temp_file, separated_dir, chunk_duration=chunk_duration, shifts=shifts)

        processing_time = time.time() - start_time

        # Cleanup temp file
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


@router.post("/separate_by_name_stream", summary="分离已上传的文件（流式进度）")
async def separate_by_name_stream(
    filename: str = Form(..., description="要分离的文件名"),
    chunk_duration: float = Form(30.0, description="分段处理时长（秒）"),
    model: str = Form("htdemucs", description="分离模型: htdemucs (4声道) 或 htdemucs_ft (微调4声道) 或 htdemucs_6s (6声道)"),
    shifts: int = Form(1, description="时间偏移增强次数")
):
    """
    分离已上传到 storage/uploaded/ 的文件，并通过 SSE 流式返回进度

    文件将**复制**到 storage/uploaded/separated/temp.mp3 进行分离（不删除原文件）

    **进度阶段**:
    - loading: 加载音频文件
    - chunk: 分段处理 (N/总片段数)
    - merging: 合并结果 (N/6 或 N/4)
    - saving: 保存文件 (N/6 或 N/4)
    - complete: 完成

    **模型选择**:
    - `htdemucs`: 4声道分离 (drums, bass, other, vocals) - **推荐**
    - `htdemucs_ft`: 微调版4声道分离 (drums, bass, other, vocals)
    - `htdemucs_6s`: 6声道分离 (drums, bass, piano, guitar, other, vocals)

    **质量增强**:
    - `shifts`: 时间偏移增强次数

    使用 SSE (Server-Sent Events) 流式返回进度，客户端需监听 text/event-stream
    """
    start_time = time.time()

    # Check if file exists
    uploaded_file = UPLOAD_DIR / filename
    if not uploaded_file.exists():
        raise HTTPException(404, f"文件不存在: {filename}")

    # Create separated directory
    separated_dir = UPLOAD_DIR / "separated"
    separated_dir.mkdir(parents=True, exist_ok=True)

    # Copy file instead of move - keep original for playback during processing
    temp_file = separated_dir / "temp.mp3"
    shutil.copy2(str(uploaded_file), str(temp_file))

    async def generate_progress():
        """生成 SSE 事件流"""
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
                "percentage": round((current / total) * 100, 1) if total > 0 else 0
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
                    progress_callback=progress_callback
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
                "percentage": 0
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
                "message": "分离完成",
                "processing_time": round(processing_time, 2),
                "output_dir": str(separated_dir),
                "files": separation_result,
                "percentage": 100
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
