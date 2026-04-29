"""
Drum Transcription Endpoint - Automatic Drum Transcription (ADT)

Supports multiple transcription methods:
1. Librosa - Traditional spectral analysis method
2. TCN (Temporal Convolutional Network) - Deep learning-based high-accuracy method

References:
- Librosa: https://librosa.org/
- TCN: https://arxiv.org/abs/1803.04807
"""

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import time
from collections import Counter
from typing import Optional, Tuple

from core.rhythm_detector import RhythmDetector
from api.config import get_storage_dir

try:
    from core.tcn_transcriber import TCNTranscriber
    TCN_AVAILABLE = True
except ImportError:
    TCN_AVAILABLE = False
    print("⚠️  TCN Transcriber is not available")
from api.models import (
    TranscriptionResponse,
    TranscriptionResult,
    HitModel,
    FillModel,
    MidiExportResponse,
    MidiExportRequest
)

router = APIRouter(prefix="/transcription", tags=["Drum Transcription"])

# Storage directories
SEPARATED_DIR = get_storage_dir() / "uploaded" / "separated"
SEPARATED_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DIR = get_storage_dir() / "demo"

# File resolution function
def resolve_file_path(filename: str) -> Tuple[Path, str]:
    """
    Resolve file path from either demo or separated directory

    Returns:
        (full_path, source_type) where source_type is 'demo' or 'separated'
    """
    # First try separated directory
    separated_path = SEPARATED_DIR / filename
    if separated_path.exists():
        return separated_path, 'separated'

    # Then try demo directory
    demo_path = DEMO_DIR / filename
    if demo_path.exists():
        return demo_path, 'demo'

    # File not found
    raise HTTPException(
        status_code=404,
        detail=f"File not found: {filename}. Please check if the file exists in storage/demo/ or storage/uploaded/separated/ directory."
    )

# Initialize detectors (singletons)
_detector = None
_tcn_transcriber = None
_enhanced_detector = None


def get_detector() -> RhythmDetector:
    """Get or create RhythmDetector instance (Librosa method)"""
    global _detector
    if _detector is None:
        _detector = RhythmDetector()
    return _detector


def get_tcn_transcriber():
    """Get or create TCNTranscriber instance (TCN method)"""
    global _tcn_transcriber
    if not TCN_AVAILABLE:
        return None
    if _tcn_transcriber is None:
        try:
            _tcn_transcriber = TCNTranscriber()
        except Exception as e:
            print(f"⚠️ TCN model failed to load: {e}")
            _tcn_transcriber = None
    return _tcn_transcriber


def get_enhanced_detector():
    """Get or create EnhancedDrumDetector instance"""
    global _enhanced_detector
    if _enhanced_detector is None:
        from core.enhanced_detector import EnhancedDrumDetector
        _enhanced_detector = EnhancedDrumDetector()
    return _enhanced_detector


@router.post("/transcribe", response_model=TranscriptionResponse, summary="Transcribe drum notation")
async def transcribe_drums(
    filename: str = Query("drums.wav", description="Drum file name (relative to storage/uploaded/separated/)"),
    method: str = Query("enhanced", description="Transcription method: 'enhanced' (enhanced), 'librosa' (traditional) or 'tcn' (deep learning)")
):
    """
    Transcribe isolated drum track to drum notation

    **Features**:
    - Automatic drum hit detection
    - Instrument classification (kick/snare/hihat/cymbal/tom)
    - BPM and time signature detection
    - Rhythm pattern analysis

    **Transcription Methods**:
    - **librosa** (default): Traditional spectral analysis method, fast but moderate accuracy
    - **tcn**: Temporal Convolutional Network-based deep learning method, higher accuracy but requires more compute

    **Input**: Separated drum file (default drums.wav)
    **Output**: Drum hit list with timestamps, instruments, and velocities
    """
    start_time = time.time()

    # Resolve file path (supports demo and separated directories)
    drum_path, source_type = resolve_file_path(filename)

    if not drum_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Drum file not found: {filename}"
        )

    try:
        import librosa
        import numpy as np

        # Load audio
        audio, sr = librosa.load(drum_path, sr=44100)

        # Select transcriber based on method
        if method == "enhanced":
            # Enhanced method (enhanced 5-stage pipeline)
            enhanced = get_enhanced_detector()
            result = enhanced.transcribe(str(drum_path))

            # Convert to API models
            flat_hits = result.to_flat_hits()

            fill_models = [
                FillModel(
                    start=f.start,
                    end=f.end,
                    bar_index=f.bar_index,
                    fill_type=f.fill_type,
                    function=f.function,
                    confidence=f.confidence,
                    duration=f.duration,
                    density=f.density
                )
                for f in result.fills
            ]

            transcription = TranscriptionResult(
                bpm=result.bpm,
                time_signature_numerator=result.time_signature_numerator,
                time_signature_denominator=result.time_signature_denominator,
                duration=result.duration,
                hits=[
                    HitModel(
                        time=h["time"],
                        velocity=h["velocity"],
                        instrument=h["instrument"],
                        confidence=h["confidence"]
                    ) for h in flat_hits
                ],
                downbeats=result.downbeats,
                total_hits=result.total_hits,
                instrument_distribution=result.instrument_distribution,
                pattern_name=result.groove_template,
                complexity=result.groove_consistency,
                subdivision="16th",
                genre=result.genre,
                genre_confidence=result.genre_confidence,
                groove_template=result.groove_template,
                groove_consistency=result.groove_consistency,
                fills=fill_models,
                fills_summary=result.fills_summary,
                phase_times=result.phase_times,
                notation_bars=result.notation_bars
            )

            return TranscriptionResponse(
                status="success",
                transcription=transcription,
                processing_time=round(result.processing_time, 2)
            )

        elif method == "tcn":
            # TCN method (deep learning)
            transcriber = get_tcn_transcriber()
            if transcriber is None:
                raise HTTPException(
                    status_code=503,
                    detail="TCN model not loaded or unavailable. Please use method='librosa'."
                )

            # TCN transcription (detects drum hits only, spectral classification based on TCN output)
            hits = transcriber.transcribe(audio, sr, confidence_threshold=0.32)

            # Use RhythmDetector to get BPM and time signature (TCN doesn't detect these)
            detector = get_detector()
            beat_info = detector.detect_rhythm_info(audio, sr)

            # Simplified rhythm pattern analysis (TCN focuses mainly on drum hit detection)
            pattern_name = "tcn_detection"
            complexity = 0.6  # TCN detection complexity is typically higher

        elif method == "librosa":
            # Librosa method (traditional spectral analysis)
            detector = get_detector()

            # Detect rhythm information
            beat_info = detector.detect_rhythm_info(audio, sr)

            # Detect and classify percussive events
            hits = detector._detect_hits(audio, sr)
            hits = detector._classify_instruments(hits, audio, sr)

            # Analyze rhythm patterns
            patterns = detector._analyze_patterns(hits, beat_info.bpm)
            pattern = patterns[0] if patterns else None
            pattern_name = pattern.name if pattern else "unknown"
            complexity = pattern.complexity if pattern else 0.5

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported transcription method: {method}. Supported methods: 'librosa', 'tcn'"
            )

        # Build response
        distribution = Counter(h.instrument for h in hits)

        transcription = TranscriptionResult(
            bpm=beat_info.bpm,
            time_signature_numerator=beat_info.time_signature.numerator,
            time_signature_denominator=beat_info.time_signature.denominator,
            duration=float(len(audio) / sr),
            hits=[
                HitModel(
                    time=h.time,
                    velocity=h.velocity,
                    instrument=h.instrument,
                    confidence=h.confidence
                ) for h in hits
            ],
            downbeats=beat_info.downbeats,  # Added downbeats field
            total_hits=len(hits),
            instrument_distribution=dict(distribution),
            pattern_name=pattern_name,
            complexity=complexity,
            subdivision="16th"
        )

        return TranscriptionResponse(
            status="success",
            transcription=transcription,
            processing_time=round(time.time() - start_time, 2)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.post("/transcribe_midi", response_model=MidiExportResponse, summary="Transcribe and export MIDI")
async def transcribe_to_midi(
    filename: str = Query("drums.wav", description="Drum file name (relative to storage/uploaded/separated/)"),
    method: str = Query("librosa", description="Transcription method: 'librosa' or 'tcn'")
):
    """
    Transcribe drum notation and generate MIDI file

    **Features**:
    - Transcribe drum hit positions and instruments
    - Generate standard MIDI file (General MIDI drum mapping)
    - Return MIDI file download link

    **MIDI Note Mapping**:
    - Kick: 36
    - Snare: 38
    - Hi-Hat: 42
    - Cymbal: 49
    - Tom: 45

    **Transcription Methods**:
    - **librosa** (default): Traditional spectral analysis method
    - **tcn**: Deep learning method with higher accuracy
    """
    drum_path, source_type = resolve_file_path(filename)

    if not drum_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Drum file not found: {filename}"
        )

    try:
        import librosa

        # Load audio
        audio, sr = librosa.load(drum_path, sr=44100)

        # Select transcriber based on method
        if method == "tcn":
            # TCN method
            transcriber = get_tcn_transcriber()
            if transcriber is None:
                raise HTTPException(
                    status_code=503,
                    detail="TCN model not loaded or unavailable. Please use method='librosa'."
                )

            hits = transcriber.transcribe(audio, sr, confidence_threshold=0.5)

            # Use RhythmDetector to get BPM (TCN doesn't detect BPM)
            detector = get_detector()
            bpm = detector._detect_bpm(audio, sr)

        elif method == "librosa":
            # Librosa method
            detector = get_detector()
            hits = detector._detect_hits(audio, sr)
            hits = detector._classify_instruments(hits, audio, sr)
            bpm = detector._detect_bpm(audio, sr)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported transcription method: {method}"
            )

        # Create RhythmPattern for MIDI generation
        from core.rhythm_detector import RhythmPattern
        pattern = RhythmPattern(
            name=f"{method}_transcription",
            hits=hits,
            bpm=bpm,
            subdivision="16th",
            complexity=0.6 if method == "tcn" else 0.5
        )

        # Generate MIDI file
        stem_name = Path(filename).stem
        output_path = SEPARATED_DIR / f"{stem_name}_{method}_transcription.mid"
        detector.generate_midi_pattern(pattern, str(output_path))

        return MidiExportResponse(
            status="success",
            midi_file=output_path.name,
            download_url=f"/tracks/audio/{output_path.name}",
            message=f"MIDI file generated successfully (method: {method})"
        )

    except HTTPException:
        raise
    except ImportError as e:
        if "midiutil" in str(e):
            raise HTTPException(
                status_code=500,
                detail="midiutil library is required: uv add midiutil"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Missing dependency library: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"MIDI export failed: {str(e)}"
        )


@router.post("/export_midi", response_model=MidiExportResponse, summary="Export transcription results as MIDI")
async def export_midi(request: MidiExportRequest):
    """
    Export existing transcription results as a MIDI file

    **Input**: Transcription results (HitModel list + BPM)
    **Output**: MIDI file download link
    """
    try:
        from core.rhythm_detector import Hit, RhythmPattern

        # Convert HitModel back to Hit objects
        hits = [
            Hit(
                time=h.time,
                velocity=h.velocity,
                instrument=h.instrument,
                confidence=h.confidence
            ) for h in request.hits
        ]

        pattern = RhythmPattern(
            name="export",
            hits=hits,
            bpm=request.bpm,
            subdivision="16th",
            complexity=0.5
        )

        # Generate file name
        timestamp = int(time.time())
        filename = request.filename or f"transcription_{timestamp}.mid"
        output_path = SEPARATED_DIR / filename

        # Generate MIDI
        detector = get_detector()
        detector.generate_midi_pattern(pattern, str(output_path))

        return MidiExportResponse(
            status="success",
            midi_file=output_path.name,
            download_url=f"/tracks/audio/{output_path.name}",
            message="MIDI export successful"
        )

    except ImportError as e:
        if "midiutil" in str(e):
            raise HTTPException(
                status_code=500,
                detail="midiutil library is required: uv add midiutil"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Missing dependency library: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"MIDI export failed: {str(e)}"
        )


@router.get("/info", summary="Transcription service information")
async def transcription_info():
    """
    Get transcription service information

    **Returns**: Available instruments list, MIDI note mapping, supported methods, etc.
    """
    # Check if TCN model is available
    tcn_transcriber = get_tcn_transcriber()
    tcn_available = tcn_transcriber is not None
    tcn_info = tcn_transcriber.get_model_info() if tcn_available else None

    return {
        "status": "available",
        "supported_instruments": ["kick", "snare", "hihat", "cymbal", "tom"],
        "midi_note_mapping": {
            "kick": 36,
            "snare": 38,
            "hihat_closed": 42,
            "hihat_open": 46,
            "tom_low": 41,
            "tom_mid": 43,
            "tom_high": 45,
            "crash": 49,
            "ride": 51
        },
        "output_formats": ["json", "midi"],
        "time_signatures": ["4/4", "3/4", "6/8", "5/4", "7/8"],
        "transcription_methods": {
            "librosa": {
                "available": True,
                "name": "Librosa (Traditional Method)",
                "description": "Spectral analysis-based drum hit detection, fast but moderate accuracy",
                "strengths": ["Fast", "Low resource consumption", "Stable"],
                "weaknesses": ["Limited ability to handle complex rhythms", "Moderate instrument classification accuracy"]
            },
            "tcn": {
                "available": tcn_available,
                "name": "TCN (Deep Learning Method)",
                "description": "High-accuracy drum hit detection based on Temporal Convolutional Network",
                "strengths": ["High accuracy", "Handles complex rhythms", "Machine learning optimized"],
                "weaknesses": ["High compute resource consumption", "Requires pre-trained model"],
                "model_info": tcn_info
            }
        },
        "features": {
            "onset_detection": {
                "librosa": "librosa.onset.onset_detect",
                "tcn": "trained_tcn_model"
            },
            "instrument_classification": {
                "librosa": "spectral_analysis",
                "tcn": "spectral_analysis"
            },
            "model_training": {
                "dataset": "E-GMD (1,251 drum performances, 45,537 sequences)",
                "architecture": "Temporal Convolutional Network",
                "input_features": "Mel spectrograms (128 bins × 200 frames)",
                "output": "Onset probabilities per frame"
            }
        },
        "recommended_usage": {
            "simple_patterns": "librosa (fast enough)",
            "complex_patterns": "tcn (higher accuracy)",
            "real_time": "librosa (low latency)",
            "offline_analysis": "tcn (quality first)"
        }
    }
