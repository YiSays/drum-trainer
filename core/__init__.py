"""
Core module for drum separation and music understanding.
Optimized for Apple Silicon (M-series chips) with Metal acceleration support.
"""

from .audio_io import AudioIO
from .separator import DrumSeparator
from .music_analyzer import MusicAnalyzer
from .structure_detector import StructureDetector
from .rhythm_detector import RhythmDetector
from .drum_generator import DrumGenerator

__all__ = [
    'AudioIO',
    'DrumSeparator',
    'MusicAnalyzer',
    'StructureDetector',
    'RhythmDetector',
    'DrumGenerator',
]
