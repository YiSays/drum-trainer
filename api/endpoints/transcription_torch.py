from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import time
import torch
import torchaudio
import librosa
from collections import Counter

from api.models import TranscriptionResponse, TranscriptionResult, HitModel
from api.config import get_storage_dir
from core.rhythm_detector import RhythmDetector # Use strictly for BPM/Pattern analysis post-detection

router = APIRouter(prefix="/transcription", tags=["Drum Transcription (PyTorch)"])

# Storage directories
SEPARATED_DIR = get_storage_dir() / "uploaded" / "separated"
DEMO_DIR = get_storage_dir() / "demo"

# Global model instance
_model = None
_device = None

def get_model():
    global _model, _device
    if _model is None:
        from core.models.adt import DrumTranscriber
        # Detect device
        if torch.backends.mps.is_available():
            _device = torch.device("mps")
            print("Using MPS (Metal) for ADT Model")
        elif torch.cuda.is_available():
            _device = torch.device("cuda")
            print("Using CUDA for ADT Model")
        else:
            _device = torch.device("cpu")
            print("Using CPU for ADT Model")
            
        _model = DrumTranscriber()
        _model.to(_device)
        _model.eval()
    return _model, _device

def resolve_file_path(filename: str) -> Path:
    """Resolve file path from either demo or separated directory"""
    # First try separated directory
    separated_path = SEPARATED_DIR / filename
    if separated_path.exists():
        return separated_path

    # Then try demo directory
    demo_path = DEMO_DIR / filename
    if demo_path.exists():
        return demo_path

    # File not found
    raise HTTPException(
        status_code=404,
        detail=f"File not found: {filename}"
    )

@router.post("/transcribe_torch", response_model=TranscriptionResponse, summary="Transcribe using PyTorch model")
async def transcribe_torch(
    filename: str = Query("drums.wav", description="Drum audio filename")
):
    """Drum transcription using PyTorch (GPU/MPS accelerated) - ADT Model"""
    start_time = time.time()
    drum_path = resolve_file_path(filename)
        
    try:
        model, device = get_model()
        
        # Load audio using torchaudio (faster, returns tensor)
        # normalize=True is default in load
        waveform, sr = torchaudio.load(drum_path)
        
        # Resample if needed
        if sr != model.sample_rate:
            resampler = torchaudio.transforms.Resample(sr, model.sample_rate).to(device)
            waveform = waveform.to(device)
            waveform = resampler(waveform)
        else:
            waveform = waveform.to(device)
            
        # Mix to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
            
        # Inference
        with torch.no_grad():
            features = model(waveform)
            
        # Decode hits
        hits_data = model.classify_hits(features)
        
        # Post-processing: Use RhythmDetector for BPM/Pattern (since our simple model doesn't do that yet)
        # In a real full-model scenario, the model might output grid directly
        detector = RhythmDetector()
        
        # We need numpy audio for RhythmDetector's BPM logic (Librosa based)
        # Move back to CPU for legacy analysis
        audio_np = waveform.cpu().numpy().squeeze()
        bpm = detector._detect_bpm(audio_np, model.sample_rate)
        
        # Convert to HitModel objects
        hits = [
            HitModel(
                time=h["time"],
                velocity=h["velocity"],
                instrument=h["instrument"],
                confidence=h["confidence"]
            ) for h in hits_data
        ]
        
        # --- Downbeat / Bar Detection (Simple Heuristic) ---
        # 1. Get Beat Grid using Librosa
        audio_np = waveform.cpu().numpy().squeeze()
        tempo, beat_frames = librosa.beat.beat_track(y=audio_np, sr=model.sample_rate)
        beat_times = librosa.frames_to_time(beat_frames, sr=model.sample_rate)
        
        # 2. Identify Kick positions
        kick_times = [h.time for h in hits if h.instrument == 'kick']
        
        # 3. Find the "Phase" (Offset) 
        # Assume 4/4 signature. We need to find which beat (0, 1, 2, or 3) is the Downbeat.
        # We look for the phase that aligns best with Kicks.
        best_phase = 0
        max_score = -1
        
        # Check 4 possible phases
        if len(beat_times) > 0 and len(kick_times) > 0:
            for phase in range(4):
                score = 0
                # Check every 4th beat starting from phase
                downbeat_candidates = beat_times[phase::4]
                
                for db in downbeat_candidates:
                    # Is there a kick near this beat? (within 100ms)
                    has_kick = any(abs(k - db) < 0.1 for k in kick_times)
                    if has_kick:
                        score += 1
                
                if score > max_score:
                    max_score = score
                    best_phase = phase
            
            # Generate Downbeats based on best phase
            downbeats = beat_times[best_phase::4].tolist()
            
            # --- Phase 2c: Context-Aware Classification Correction ---
            # Rule: In 4/4 Rock/Pop, beats 2 and 4 are usually Snare.
            # If we detect a "Tom" on beat 2 or 4, it's 95% likely a Snare.
            
            # Calculate Backbeat times (Beats 2 and 4 relative to downbeat)
            # beat_times indices: 0=1st, 1=2nd, 2=3rd, 3=4th...
            # Downbeat is at index `best_phase`
            # Backbeats are at `best_phase + 1`, `best_phase + 3`, `best_phase + 5`...
            
            backbeat_indices = []
            curr = best_phase + 1 # 2nd beat
            while curr < len(beat_times):
                backbeat_indices.append(curr)
                if curr + 2 < len(beat_times):
                    backbeat_indices.append(curr + 2) # 4th beat
                curr += 4 # Next bar
                
            backbeat_times = [beat_times[i] for i in backbeat_indices]
            
            for hit in hits:
                if hit.instrument == 'tom':
                    # Check if this Tom is on a backbeat (within 100ms tolerance)
                    is_on_backbeat = any(abs(hit.time - bb) < 0.1 for bb in backbeat_times)
                    
                    if is_on_backbeat:
                        # Correction: It's likely a Snare
                        hit.instrument = 'snare'
                        hit.confidence = 0.85  # Boost confidence
                        # print(f"Fixed Tom->Snare at {hit.time:.2f}s (Backbeat Context)")

        else:
            downbeats = []

        # Analyze pattern (optional)
        distribution = Counter(h.instrument for h in hits)
        
        transcription = TranscriptionResult(
            bpm=float(tempo),
            time_signature_numerator=4, 
            time_signature_denominator=4,
            duration=float(waveform.shape[1] / model.sample_rate),
            hits=hits,
            downbeats=downbeats,  # Added downbeats
            total_hits=len(hits),
            instrument_distribution=dict(distribution),
            pattern_name="pytorch_v2",
            complexity=0.5,
            subdivision="16th"
        )
        
        return TranscriptionResponse(
            status="success",
            transcription=transcription,
            processing_time=round(time.time() - start_time, 2)
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"PyTorch transcription failed: {str(e)}")
