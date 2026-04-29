"""
API Data Models
"""

from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


class TrackInfo(BaseModel):
    """Track information model"""
    name: str
    path: str
    size: int
    duration: float
    samplerate: int
    channels: int
    extension: str


class TrackListResponse(BaseModel):
    """Track list response model"""
    tracks: List[TrackInfo]


class AudioInfo(BaseModel):
    """Audio file information model"""
    name: str
    size: int
    samplerate: int
    channels: int
    duration: float
    format: Optional[str] = None
    subtype: Optional[str] = None


class AnalysisResult(BaseModel):
    """Analysis result model"""
    style: str
    bpm: int
    energy: float
    key: str
    mood: str
    structure: List[Dict]
    rhythm_profile: Dict
    timestamp: Optional[str] = None


class ProcessResponse(BaseModel):
    """Processing response model"""
    status: str
    analysis: Optional[AnalysisResult] = None
    files: Optional[Dict[str, str]] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    device: str
    model_loaded: bool
    default_model: Optional[str] = None
    shifts: Optional[int] = None


class HitModel(BaseModel):
    """Drum hit event model"""
    time: float
    velocity: float
    instrument: str  # kick, snare, hihat, cymbal, tom
    confidence: float


class FillModel(BaseModel):
    """Drum fill information model"""
    start: float
    end: float
    bar_index: int
    fill_type: str       # tom_roll, snare_roll, linear, syncopated, one_shot, mixed
    function: str        # build_up, reset, transition, climax, variation
    confidence: float
    duration: float
    density: float       # hits per second


class TranscriptionResult(BaseModel):
    bpm: float
    time_signature_numerator: int
    time_signature_denominator: int
    duration: float
    hits: List[HitModel]
    downbeats: List[float] = []  # Start times of each bar
    total_hits: int
    instrument_distribution: Dict[str, int]
    pattern_name: str
    complexity: float
    subdivision: str
    # Enhanced fields (optional, populated by 'enhanced' method)
    genre: Optional[str] = None
    genre_confidence: Optional[float] = None
    groove_template: Optional[str] = None
    groove_consistency: Optional[float] = None
    fills: Optional[List[FillModel]] = None
    fills_summary: Optional[Dict] = None
    phase_times: Optional[Dict[str, float]] = None
    notation_bars: Optional[List[Dict]] = None


class TranscriptionResponse(BaseModel):
    """Transcription response model"""
    status: str
    transcription: Optional[TranscriptionResult] = None
    message: Optional[str] = None
    processing_time: Optional[float] = None


class MidiExportRequest(BaseModel):
    """MIDI export request model"""
    hits: List[HitModel]
    bpm: int
    filename: Optional[str] = None


class MidiExportResponse(BaseModel):
    """MIDI export response model"""
    status: str
    midi_file: Optional[str] = None
    download_url: Optional[str] = None
    message: Optional[str] = None
