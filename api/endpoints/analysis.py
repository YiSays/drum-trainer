"""
Analysis endpoint - Music analysis using V2 analyzer
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import tempfile
import shutil
from datetime import datetime
import time
import json

from api.config import get_storage_dir
from core.music_analyzer_v2 import MusicAnalyzerV2

router = APIRouter(prefix="/analysis", tags=["Analysis"])

TEMP_DIR = get_storage_dir() / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze", summary="Full music analysis")
async def analyze_music(
    file: UploadFile = File(..., description="Audio file"),
    bpm_hint: int = Form(None, description="Optional BPM hint (speeds up analysis)")
):
    """
    Complete music analysis

    **Analysis includes**:
    - Style detection (rock/jazz/pop/electronic etc.)
    - BPM detection
    - Song structure (intro/verse/chorus/bridge)
    - Rhythm features
    - Key detection
    - Mood analysis
    - Energy level
    """
    start_time = time.time()

    temp_file = TEMP_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        analyzer = MusicAnalyzerV2()
        analysis = analyzer.analyze(temp_file)

        if bpm_hint:
            analysis["bpm"] = bpm_hint

        processing_time = time.time() - start_time
        analysis["timestamp"] = datetime.now().isoformat()

        temp_file.unlink(missing_ok=True)

        return {
            "status": "success",
            "analysis": analysis,
            "processing_time": round(processing_time, 2)
        }

    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@router.post("/structure", summary="Structure analysis")
async def analyze_structure(
    file: UploadFile = File(...)
):
    """Detailed song structure analysis with section boundaries and types."""
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
        raise HTTPException(500, f"Structure analysis failed: {str(e)}")


@router.post("/rhythm", summary="Rhythm analysis")
async def analyze_rhythm(
    file: UploadFile = File(...),
    bpm: int = Form(..., description="BPM (required)")
):
    """Rhythm feature analysis - identifies main rhythm patterns and percussion patterns."""
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
        raise HTTPException(500, f"Rhythm analysis failed: {str(e)}")
