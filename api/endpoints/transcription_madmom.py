from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
import time
import torch
import torchaudio
import librosa
from collections import Counter

from api.models import TranscriptionResponse, TranscriptionResult, HitModel
from api.config import get_storage_dir

router = APIRouter(prefix="/transcription", tags=["Drum Transcription (Madmom)"])

# Storage directories
SEPARATED_DIR = get_storage_dir() / "uploaded" / "separated"

@router.post("/transcribe_madmom", response_model=TranscriptionResponse, summary="Transcribe using Madmom + PyTorch hybrid")
async def transcribe_madmom(
    filename: str = Query("drums.wav", description="Drum audio filename")
):
    """
    Drum transcription using Madmom (CNN/RNN) for onset detection
    combined with PyTorch for instrument classification.
    """
    start_time = time.time()
    drum_path = SEPARATED_DIR / filename
    
    if not drum_path.exists():
        raise HTTPException(404, f"File not found: {filename}")
        
    try:
        # 1. Initialize Madmom
        from core.models.madmom_adapter import MadmomTranscriber
        adapter = MadmomTranscriber()
        
        # 2. Detect Onsets using Madmom CNN (Very accurate)
        abs_path = drum_path.resolve()
        print(f"DEBUG: Processing {abs_path}")
        
        raw_hits = adapter.transcribe(str(abs_path))
        print(f"DEBUG: raw_hits type: {type(raw_hits)}, len: {len(raw_hits)}")
        if len(raw_hits) > 0:
            print(f"DEBUG: raw_hits[0]: {raw_hits[0]}")
            
        beat_info = adapter.detect_beats(str(abs_path))
        print(f"DEBUG: beat_info: {beat_info.keys()}")
        
        # 3. Use PyTorch for Instrument Classification at Madmom's time points
        # Load audio for feature extraction
        waveform, sr = torchaudio.load(drum_path)
        
        # Setup PyTorch model for classification
        # Reuse logic from transcription_torch but inline to avoid circular import
        from core.models.adt import DrumTranscriber
        
        device = torch.device("cpu")
        if torch.backends.mps.is_available():
            device = torch.device("mps")
        elif torch.cuda.is_available():
            device = torch.device("cuda")
            
        model = DrumTranscriber()
        model.to(device)
        model.eval()
        
        # Mix to mono and move to device
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        waveform = waveform.to(device)
        
        # We need to manually trigger feature extraction at Madmom's timestamps
        # To simplify, we run our model's forward pass to get the full feature maps
        with torch.no_grad():
            features_map = model(waveform)
            
        # Instead of our model's onsets, we use Madmom's onsets
        # Map Madmom times to frame indices
        # FORCE INT conversion to avoid numpy scalars causing torch issues
        madmom_frames = [int(librosa.time_to_frames(h["time"], sr=model.sample_rate, hop_length=model.hop_length)) for h in raw_hits]
        
        if not madmom_frames:
            hits = []
        else:
            madmom_frames_tensor = torch.tensor(madmom_frames, dtype=torch.long).to(device)
            
            # Extract features at Madmom onsets
            with torch.no_grad():
                features_map = model.extract_features_at_onsets(waveform, madmom_frames_tensor)
                
            # Classify using the extracted features
            pytorch_res = model.classify_hits(features_map)
            
            # Merge results
            hits = []
            for i, mh in enumerate(raw_hits):
                # We have 1-to-1 correspondence now
                ph = pytorch_res[i]
                mh["instrument"] = ph["instrument"]
                mh["confidence"] = ph["confidence"]
                hits.append(HitModel(**mh))

        # --- Downbeat Detection using Madmom's Beats ---
        # Assume 4/4 and align with Kicks
        kick_times = [h.time for h in hits if h.instrument == 'kick']
        beat_times = beat_info["beats"]
        bpm = beat_info["bpm"]
        
        # BPM Correction: Halve if too fast compared to genre norms (e.g. > 140 for pop/rock)
        if bpm > 140:
            bpm /= 2
        
        best_phase = 0
        max_score = -1
        if len(beat_times) > 0 and len(kick_times) > 0:
            for phase in range(min(4, len(beat_times))):
                score = 0
                downbeat_candidates = beat_times[phase::4]
                for db in downbeat_candidates:
                    if any(abs(k - db) < 0.1 for k in kick_times): score += 1
                if score > max_score:
                    max_score = score
                    best_phase = phase
            downbeats = beat_times[best_phase::4]
            
            # --- Context-Aware Classification Correction (Same as PyTorch Endpoint) ---
            # Rule: In 4/4 Rock/Pop, beats 2 and 4 are usually Snare.
            backbeat_indices = []
            curr = best_phase + 1 # 2nd beat
            while curr < len(beat_times):
                backbeat_indices.append(curr)
                if curr + 2 < len(beat_times):
                    backbeat_indices.append(curr + 2) # 4th beat
                curr += 4 
                
            backbeat_times = [beat_times[i] for i in backbeat_indices]
            
            for hit in hits:
                if hit.instrument == 'tom':
                    is_on_backbeat = any(abs(hit.time - bb) < 0.1 for bb in backbeat_times)
                    if is_on_backbeat:
                        hit.instrument = 'snare'
                        hit.confidence = 0.85
        else:
            downbeats = []

        transcription = TranscriptionResult(
            bpm=bpm, # Use corrected BPM
            time_signature_numerator=4,
            time_signature_denominator=4,
            duration=float(waveform.shape[1] / sr),
            hits=hits,
            downbeats=downbeats,
            total_hits=len(hits),
            instrument_distribution=dict(Counter(h.instrument for h in hits)),
            pattern_name="madmom_hybrid",
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
        import os
        error_msg = traceback.format_exc()
        print(error_msg)
        
        with open("MADMOM_TRACEBACK.txt", "w") as f:
            f.write(error_msg)
            
        raise HTTPException(500, f"Madmom transcription failed: {str(e)}")
