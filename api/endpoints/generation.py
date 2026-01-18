"""
生成端点 - 鼓演奏生成功能（使用 V2 分析器，支持节拍检测）
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import time
import json
import numpy as np

from core.music_analyzer_v2 import MusicAnalyzerV2
from core.music_analyzer import MusicAnalyzer
from core.drum_generator import DrumGenerator
from core.audio_io import AudioIO

router = APIRouter(prefix="/generation", tags=["生成"])

TEMP_DIR = Path("storage/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = Path("storage/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_temp_files(temp_files: list[Path]):
    """清理临时文件"""
    for temp_file in temp_files:
        temp_file.unlink(missing_ok=True)


@router.post("/generate", summary="生成鼓演奏")
async def generate_drums(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="音频文件"),
    style_hint: str = Form(None, description="风格提示（如 rock, jazz）"),
    complexity: float = Form(0.5, description="复杂度 (0.0 - 1.0)", ge=0.0, le=1.0)
):
    """
    智能生成鼓演奏（纯自动模式）

    **工作流程**:
    1. 分析歌曲风格、BPM、结构
    2. 选择合适的节奏模式
    3. 生成鼓演奏音频
    4. 返回分析报告 + 音频文件

    **返回数据**:
    - analysis: 完整音乐分析
    - generated: 生成的鼓轨信息
    - files: 可下载的音频文件
    """
    start_time = time.time()
    temp_files = []

    # 保存上传文件
    temp_audio = TEMP_DIR / f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    temp_files.append(temp_audio)
    try:
        with open(temp_audio, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        # 1. 音乐分析（V2 - 包含节拍检测）
        print("📊 步骤 1: 音乐分析（含节拍检测）...")
        analyzer = MusicAnalyzerV2()
        analysis = analyzer.analyze(temp_audio)

        # 应用用户提示
        if style_hint:
            analysis["style"] = style_hint

        # 2. 鼓生成
        print("🥁 步骤 2: 生成鼓演奏...")
        generator = DrumGenerator()

        # 创建输出子目录
        output_subdir = OUTPUT_DIR / f"drums_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_subdir.mkdir(parents=True, exist_ok=True)

        # 生成
        drum_track = generator.generate_from_analysis(analysis, output_subdir)

        # 3. 混合音频（原曲 + 生成的鼓）
        print("🎵 步骤 3: 创建混合音频...")
        audio_io = AudioIO()
        original_audio, sr = audio_io.load_audio(temp_audio)

        # 确保长度一致
        min_length = min(original_audio.shape[-1], drum_track.audio.shape[-1])
        original_audio = original_audio[:, :min_length]
        drum_audio = drum_track.audio[:min_length]

        # 混合
        if original_audio.shape[0] == 2:  # 立体声
            drum_stereo = audio_io.to_stereo(drum_audio[np.newaxis, :])[:, :min_length]
            mixed = original_audio + drum_stereo * 0.5  # 鼓声50%音量
        else:
            mixed = original_audio + drum_audio * 0.5

        # 保存混合音频
        mixed_path = output_subdir / "original_with_generated_drums.wav"
        audio_io.save_audio(mixed, mixed_path, sr)

        # 4. 准备返回数据
        processing_time = time.time() - start_time

        result = {
            "status": "success",
            "analysis": {
                "style": analysis["style"],
                "bpm": analysis["bpm"],
                "energy": analysis["energy"],
                "key": analysis["key"],
                "mood": analysis["mood"],
                "structure": analysis["structure"],
                "rhythm_profile": analysis["rhythm_profile"],
                # 新增：节拍检测信息
                "time_signature": analysis.get("time_signature", {"numerator": 4, "denominator": 4, "confidence": 0.0}),
                "downbeats": analysis.get("downbeats", []),
                "beats": analysis.get("beats", []),
                "beat_positions": analysis.get("beat_positions", [])
            },
            "generated": {
                "pattern": drum_track.pattern,
                "bpm": drum_track.bpm,
                "sections": drum_track.sections
            },
            "files": {
                "generated_drums": str(output_subdir / "generated_drums.wav"),
                "original_with_drums": str(mixed_path),
                "generated": str(output_subdir / "generated_drums.wav")
            },
            "processing_time": round(processing_time, 2)
        }

        # 清理临时文件
        background_tasks.add_task(cleanup_temp_files, temp_files)

        return result

    except Exception as e:
        # 清理临时文件
        background_tasks.add_task(cleanup_temp_files, temp_files)
        raise HTTPException(500, f"生成失败: {str(e)}")


@router.post("/process", summary="完整处理（推荐）")
async def process_complete(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_duration: float = Form(30.0, description="分离处理时长（秒）")
):
    """
    完整处理流程（一站式API）

    **包含**:
    - 鼓声分离 (Demucs)
    - 音乐理解 (A+B)
    - 智能生成 (纯自动)

    **返回**: 所有处理结果 + 文件
    """
    start_time = time.time()
    temp_files = []

    # 保存文件
    temp_audio = TEMP_DIR / f"complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    temp_files.append(temp_audio)
    try:
        with open(temp_audio, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        output_subdir = OUTPUT_DIR / f"complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_subdir.mkdir(parents=True, exist_ok=True)

        # 1. 分离
        print("🔪 步骤 1: 分离鼓声...")
        from core.separator import DrumSeparator
        separator = DrumSeparator()
        separated_files = separator.separate(temp_audio, output_subdir / "separated", chunk_duration)

        # 2. 分析
        print("📊 步骤 2: 音乐分析...")
        analyzer = MusicAnalyzer()
        analysis = analyzer.analyze(temp_audio)

        # 3. 生成
        print("🥁 步骤 3: 生成鼓演奏...")
        generator = DrumGenerator()
        drum_track = generator.generate_from_analysis(analysis, output_subdir / "generated")

        # 4. 混合（原曲 + 生成的鼓）
        audio_io = AudioIO()
        original_audio, sr = audio_io.load_audio(temp_audio)
        drum_audio = drum_track.audio

        min_length = min(original_audio.shape[-1], len(drum_audio))
        original_audio = original_audio[:, :min_length]
        drum_audio = drum_audio[:min_length]

        if original_audio.shape[0] == 2:
            drum_stereo = audio_io.to_stereo(drum_audio[np.newaxis, :])[:, :min_length]
            mixed = original_audio + drum_stereo * 0.5
        else:
            mixed = original_audio + drum_audio * 0.5

        mixed_path = output_subdir / "original_with_generated_drums.wav"
        audio_io.save_audio(mixed, mixed_path, sr)

        processing_time = time.time() - start_time

        result = {
            "status": "success",
            "message": "完整处理完成",
            "analysis": analysis,
            "generated": {
                "pattern": drum_track.pattern,
                "bpm": drum_track.bpm
            },
            "files": {
                **separated_files,  # Demucs分离的
                "generated_drums": str(output_subdir / "generated_drums.wav"),
                "original_with_generated_drums": str(mixed_path),
                "rhythm_info": str(output_subdir / "generated" / "rhythm_info.json")
            },
            "processing_time": round(processing_time, 2)
        }

        background_tasks.add_task(cleanup_temp_files, temp_files)

        return result

    except Exception as e:
        background_tasks.add_task(cleanup_temp_files, temp_files)
        raise HTTPException(500, f"完整处理失败: {str(e)}")
