"""
Generation Endpoint - Drum Performance Generation (uses V2 analyzer with beat detection)
"""

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
    Request,
)
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
from api.config import get_storage_dir
from api.rate_limiter import separation_limit

router = APIRouter(prefix="/generation", tags=["Generation"])

TEMP_DIR = get_storage_dir() / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = get_storage_dir() / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_temp_files(temp_files: list[Path]):
    """Clean up temporary files"""
    for temp_file in temp_files:
        temp_file.unlink(missing_ok=True)


@router.post("/generate", summary="Generate drum performance")
async def generate_drums(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file"),
    style_hint: str = Form(None, description="Style hint (e.g., rock, jazz)"),
    complexity: float = Form(0.5, description="Complexity (0.0 - 1.0)", ge=0.0, le=1.0),
):
    """
    Smart drum performance generation (fully automatic mode)

    **Workflow**:
    1. Analyze song style, BPM, structure
    2. Select appropriate rhythm patterns
    3. Generate drum performance audio
    4. Return analysis report + audio files

    **Returned Data**:
    - analysis: Complete music analysis
    - generated: Generated drum track info
    - files: Downloadable audio files
    """
    start_time = time.time()
    temp_files = []

    # Save uploaded file
    temp_audio = (
        TEMP_DIR / f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    )
    temp_files.append(temp_audio)
    try:
        with open(temp_audio, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        # 1. Music analysis (V2 - includes beat detection)
        print("📊 Step 1: Music analysis (with beat detection)...")
        analyzer = MusicAnalyzerV2()
        analysis = analyzer.analyze(temp_audio)

        # Apply user hints
        if style_hint:
            analysis["style"] = style_hint

        # 2. Drum generation
        print("🥁 Step 2: Generating drum performance...")
        generator = DrumGenerator()

        # Create output subdirectory
        output_subdir = OUTPUT_DIR / f"drums_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_subdir.mkdir(parents=True, exist_ok=True)

        # Generate
        drum_track = generator.generate_from_analysis(analysis, output_subdir)

        # 3. Mix audio (original + generated drums)
        print("🎵 Step 3: Creating mixed audio...")
        audio_io = AudioIO()
        original_audio, sr = audio_io.load_audio(temp_audio)

        # Ensure matching lengths
        min_length = min(original_audio.shape[-1], drum_track.audio.shape[-1])
        original_audio = original_audio[:, :min_length]
        drum_audio = drum_track.audio[:min_length]

        # Mix
        if original_audio.shape[0] == 2:  # Stereo
            drum_stereo = audio_io.to_stereo(drum_audio[np.newaxis, :])[:, :min_length]
            mixed = original_audio + drum_stereo * 0.5  # Drums at 50% volume
        else:
            mixed = original_audio + drum_audio * 0.5

        # Save mixed audio
        mixed_path = output_subdir / "original_with_generated_drums.wav"
        audio_io.save_audio(mixed, mixed_path, sr)

        # 4. Prepare return data
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
                # New: beat detection info
                "time_signature": analysis.get(
                    "time_signature",
                    {"numerator": 4, "denominator": 4, "confidence": 0.0},
                ),
                "downbeats": analysis.get("downbeats", []),
                "beats": analysis.get("beats", []),
                "beat_positions": analysis.get("beat_positions", []),
            },
            "generated": {
                "pattern": drum_track.pattern,
                "bpm": drum_track.bpm,
                "sections": drum_track.sections,
            },
            "files": {
                "generated_drums": str(output_subdir / "generated_drums.wav"),
                "original_with_drums": str(mixed_path),
                "generated": str(output_subdir / "generated_drums.wav"),
            },
            "processing_time": round(processing_time, 2),
        }

        # Clean up temporary files
        background_tasks.add_task(cleanup_temp_files, temp_files)

        return result

    except Exception as e:
        # Clean up temporary files
        background_tasks.add_task(cleanup_temp_files, temp_files)
        raise HTTPException(500, f"Generation failed: {str(e)}")


@router.post("/process", summary="Full pipeline (recommended)")
@separation_limit
async def process_complete(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    chunk_duration: float = Form(
        30.0, description="Separation processing duration (seconds)"
    ),
    model: str = Form(
        "htdemucs",
        description="Separation model: htdemucs (4-stem) or htdemucs_ft (fine-tuned 4-stem) or htdemucs_6s (6-stem)",
    ),
    shifts: int = Form(1, description="Number of time-shift augmentations"),
):
    """
    Full processing pipeline (one-stop API)

    **Includes**:
    - Drum Separation (Demucs)
    - Music Analysis (A+B)
    - Smart Generation (fully automatic)

    **Model Selection**:
    - `htdemucs`: 4-stem separation (drums, bass, other, vocals) - **Recommended**
    - `htdemucs_ft`: Fine-tuned 4-stem separation (drums, bass, other, vocals)
    - `htdemucs_6s`: 6-stem separation (drums, bass, piano, guitar, other, vocals)

    **Quality Enhancement**:
    - `shifts`: Number of time-shift augmentations

    **Returns**: All processing results + files
    """
    start_time = time.time()
    temp_files = []

    # Save file
    temp_audio = (
        TEMP_DIR
        / f"complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    )
    temp_files.append(temp_audio)
    try:
        with open(temp_audio, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        output_subdir = (
            OUTPUT_DIR / f"complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        output_subdir.mkdir(parents=True, exist_ok=True)

        # 1. Separation
        print("🔪 Step 1: Separating drums...")
        from core.separator import DrumSeparator

        separator = DrumSeparator(model_name=model)
        separated_files = separator.separate(
            temp_audio, output_subdir / "separated", chunk_duration, shifts=shifts
        )

        # 2. Analysis
        print("📊 Step 2: Music analysis...")
        analyzer = MusicAnalyzer()
        analysis = analyzer.analyze(temp_audio)

        # 3. Generation
        print("🥁 Step 3: Generating drum performance...")
        generator = DrumGenerator()
        drum_track = generator.generate_from_analysis(
            analysis, output_subdir / "generated"
        )

        # 4. Mixing (original + generated drums)
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
            "message": "Full pipeline complete",
            "analysis": analysis,
            "generated": {"pattern": drum_track.pattern, "bpm": drum_track.bpm},
            "files": {
                **separated_files,  # Demucs separated
                "generated_drums": str(output_subdir / "generated_drums.wav"),
                "original_with_generated_drums": str(mixed_path),
                "rhythm_info": str(output_subdir / "generated" / "rhythm_info.json"),
            },
            "processing_time": round(processing_time, 2),
        }

        background_tasks.add_task(cleanup_temp_files, temp_files)

        return result

    except Exception as e:
        background_tasks.add_task(cleanup_temp_files, temp_files)
        raise HTTPException(500, f"Full pipeline failed: {str(e)}")
