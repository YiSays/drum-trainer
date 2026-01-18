"""
分析端点 - 音乐理解功能 (A+B优先级) - 使用 V2 分析器

V2 分析器集成了完整的节拍检测（拍号、downbeat、节拍位置）
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import time
import json

from core.music_analyzer_v2 import MusicAnalyzerV2

router = APIRouter(prefix="/analysis", tags=["分析"])

TEMP_DIR = Path("storage/temp")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze", summary="完整音乐分析")
async def analyze_music(
    file: UploadFile = File(..., description="音频文件"),
    bpm_hint: int = Form(None, description="可选的BPM提示（加速分析）")
):
    """
    完整的音乐理解分析

    **分析内容**:
    - 风格识别 (rock/jazz/pop/electronic 等)
    - BPM 检测
    - 段落结构 (intro/verse/chorus/bridge)
    - 节奏特征
    - 键/调性
    - 情绪分析
    - 能量水平

    **返回数据**: 完整的分析报告
    """
    start_time = time.time()

    # 保存文件
    temp_file = TEMP_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        # V2 音乐分析器（包含完整节拍检测）
        analyzer = MusicAnalyzerV2()
        analysis = analyzer.analyze(temp_file)

        # 如果有 BPM 提示，优先使用
        if bpm_hint:
            analysis["bpm"] = bpm_hint

        processing_time = time.time() - start_time

        # 添加时间戳
        analysis["timestamp"] = datetime.now().isoformat()

        # 清理
        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "analysis": analysis,
            "processing_time": round(processing_time, 2)
        }

    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(500, f"分析失败: {str(e)}")


@router.post("/structure", summary="段落结构分析")
async def analyze_structure(
    file: UploadFile = File(...)
):
    """
    专注的段落结构分析

    返回详细的段落边界和类型
    """
    temp_file = TEMP_DIR / f"structure_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        audio_io = AudioIO()
        audio, sr = audio_io.load_audio(temp_file)
        mono = audio_io.to_mono(audio)

        detector = StructureDetector()
        sections = detector.detect(mono, sr)
        summary = detector.get_section_summary(sections)

        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "structure": summary
        }

    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(500, f"段落分析失败: {str(e)}")


@router.post("/rhythm", summary="节奏分析")
async def analyze_rhythm(
    file: UploadFile = File(...),
    bpm: int = Form(..., description="BPM（必需）")
):
    """
    节奏特征分析

    识别主要节奏型和打击模式
    """
    temp_file = TEMP_DIR / f"rhythm_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        audio_io = AudioIO()
        audio, sr = audio_io.load_audio(temp_file)
        mono = audio_io.to_mono(audio)

        detector = RhythmDetector()
        patterns = detector.detect(mono, sr, bpm)
        report = detector.get_rhythm_report(patterns)

        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "rhythm": report
        }

    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(500, f"节奏分析失败: {str(e)}")
