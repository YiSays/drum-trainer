# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Understanding the Codebase

**IMPORTANT**: This document contains the complete architecture overview, function listings, and data flow. Before reading individual source files, **read this file first** to understand the codebase structure and how components interact. This avoids unnecessary file reads and provides efficient context.

The Code Structure section above lists all functions and their purposes in each file - this is your primary reference for understanding what code exists and where to find it.

## Quick Reference

### Development Commands
```bash
# Install dependencies
uv sync

# Run API server
uv run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

# Use CLI tools
uv run drum-trainer info
uv run drum-trainer complete song.mp3 -o output/
uv run drum-trainer separate song.mp3 -o output/
uv run drum-trainer analyze song.mp3
uv run drum-trainer generate song.mp3 -o output/ --style rock

# Run Python scripts (ALWAYS use `uv run`)
uv run python test_complete_solution.py  # Full solution test
uv run python test_drum_sound.py         # Drum tone test
uv run python test_separation.py         # Separation quality test

# Pipe operations with uv run
# Use `uv run python` for scripts in a pipeline
uv run python -c "import torch; print(torch.__version__)" | head -1
cat data.txt | uv run python script.py  # Standard input piping
uv run python script.py | grep "output"  # Standard output piping
cat input.txt | uv run python script.py | tee output.txt  # Full pipeline

# For shell commands in pipes, use standard commands
# Only use `uv run` for Python scripts/commands
cat audio.mp3 | ffprobe -f mp3 - 2>&1 | grep Duration  # External tools
```

### Environment Setup
- Uses **uv** for dependency management (install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Optimized for **Apple Silicon** (MPS acceleration for PyTorch)
- Python 3.10+ required
- Models download to `storage/models/` (Demucs model ~1.5GB)

## Architecture Overview

### Code Structure
```
drum-trainer/
├── api/
│   ├── __init__.py
│   ├── server.py                    # FastAPI main server
│   │   ├── app                      # FastAPI application instance
│   │   ├── root()                   # Health/status endpoint
│   │   ├── health()                 # Health check endpoint
│   │   ├── download_file()          # File download endpoint
│   │   ├── test_analyze()           # Test analysis endpoint
│   │   ├── info()                   # System info endpoint
│   │   └── UI endpoints (/ui, /ui/css/style.css, /ui/js/app.js)
│   ├── models.py                    # Pydantic data models (HealthResponse, etc.)
│   └── endpoints/
│       ├── separation.py            # Drum separation routes
│       │   ├── separate_drums()     # POST /separation/separate
│       │   └── preview_separation() # POST /separation/preview
│       ├── analysis.py              # Music analysis routes
│       ├── generation.py            # Drum generation routes
│       │   ├── generate_drums()     # POST /generation/generate
│       │   └── process_complete()   # POST /generation/process (recommended)
│       ├── tracks.py                # Track management routes
│       └── youtube.py               # YouTube download routes
│
├── core/
│   ├── __init__.py
│   ├── audio_io.py                  # Audio loading/saving utilities
│   │   ├── AudioIO class
│   │   ├── load_audio()             # Load audio file
│   │   ├── save_audio()             # Save audio file
│   │   ├── get_duration()           # Get audio duration
│   │   ├── to_mono()                # Convert to mono
│   │   ├── to_stereo()              # Convert to stereo
│   │   └── split_long_audio()       # Split long audio into chunks
│   ├── separator.py                 # Drum separation (Demucs)
│   │   ├── DrumSeparator class
│   │   ├── _detect_device()         # Auto-detect CPU/MPS/CUDA
│   │   ├── _load_model()            # Lazy-load Demucs model
│   │   ├── separate()               # Main separation method
│   │   ├── _separate_chunk()        # Process single chunk
│   │   ├── _merge_results()         # Merge chunks and save
│   │   ├── _highpass_filter()       # Low-frequency cleanup filter
│   │   └── preview_sources()        # Quick 30s preview
│   ├── music_analyzer.py            # Music analysis (v1 - basic)
│   │   ├── MusicAnalyzer class
│   │   ├── analyze()                # Full music analysis
│   │   ├── detect_bpm()             # BPM detection (Librosa)
│   │   ├── detect_style()           # Style classification
│   │   ├── detect_structure()       # Section detection
│   │   ├── _classify_section_smart()# Section type classification
│   │   ├── analyze_rhythm()         # Rhythm profile
│   │   ├── analyze_energy()         # Energy analysis
│   │   ├── detect_key()             # Key detection
│   │   └── analyze_mood()           # Mood analysis
│   ├── music_analyzer_v2.py         # Music analysis (v2 - with beats)
│   │   ├── MusicAnalyzerV2 class
│   │   ├── analyze()                # Full analysis with beats
│   │   ├── detect_beats()           # Beat position detection
│   │   ├── detect_time_signature()  # Time signature detection
│   │   └── find_downbeats()         # Downbeat detection
│   ├── rhythm_detector.py           # Advanced rhythm detection
│   ├── structure_detector.py        # Structure detection utilities
│   ├── drum_generator.py            # Drum track generation
│   │   ├── DrumPattern dataclass    # Pattern definition
│   │   ├── GeneratedDrumTrack dataclass  # Output track
│   │   ├── DrumGenerator class
│   │   ├── _init_pattern_library()  # 20+ predefined patterns
│   │   ├── generate_from_analysis() # Main generation method
│   │   ├── _select_pattern()        # Pattern selection algorithm
│   │   ├── _synthesize_drums()      # Basic 4/4 synthesis
│   │   ├── _synthesize_drums_advanced()  # Advanced synthesis (supports any time signature)
│   │   ├── _add_kick()              # Kick sound synthesis (60+40Hz)
│   │   ├── _add_snare()             # Snare sound synthesis (180+330Hz + noise)
│   │   ├── _add_hihat()             # Hi-hat sound synthesis (high-freq noise)
│   │   ├── _add_fill()              # Fill/roll generation
│   │   ├── _save_drums()            # Save generated audio
│   │   └── generate_variant()       # Generate pattern variant
│   └── youtube_downloader.py        # YouTube audio download
│       ├── download_audio()         # Download audio from YouTube URL
│       └── extract_audio()          # Extract audio with yt-dlp
│
├── drum_trainer/
│   ├── __init__.py
│   └── cli.py                       # Click-based CLI
│       ├── main()                   # Command group
│       ├── separate()               # `drum-trainer separate`
│       ├── analyze()                # `drum-trainer analyze`
│       ├── generate()               # `drum-trainer generate`
│       ├── complete()               # `drum-trainer complete`
│       └── info()                   # `drum-trainer info`
│
├── scripts/
│   ├── install.sh                   # Installation script for macOS/Apple Silicon
│   └── run.sh                       # API server startup script
│
├── storage/
│   ├── uploaded/                    # Main upload directory
│   │   ├── filename.mp3             # Original uploaded file
│   │   └── separated/               # Separation results (created after processing)
│   │       ├── temp.mp3             # Temp file during separation (deleted after)
│   │       ├── drum.wav             # Isolated drum track
│   │       ├── no_drums.wav         # Backing track (no drums)
│   │       ├── bass.wav             # Isolated bass
│   │       ├── vocals.wav           # Isolated vocals
│   │       └── other.wav            # Other instruments
│   ├── generated/                   # User output files (timestamped)
│   ├── models/                      # Demucs model cache (~1.5GB)
│   └── demo/                        # Demo tracks (future use)
│
├── web_ui/                          # Simple web interface
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
│
├── web/                             # Flutter frontend (in development)
│
├── test_*.py                        # Test scripts
│   ├── test_complete_solution.py    # Full pipeline test
│   ├── test_drum_sound.py           # Drum tone frequency verification
│   ├── test_separation.py           # Separation quality test
│   └── test_separation_improved.py  # Filter parameter testing
│
└── pyproject.toml                   # uv/Python dependencies
```

### High-Level Data Flow
1. **Input Audio** → 2. **Drum Separation** → 3. **Music Analysis** → 4. **Drum Generation** → 5. **Output Audio**

### Core Modules (`core/`)

**`separator.py`** - Demucs-based drum separation
- `DrumSeparator` class uses Facebook's Demucs v4.0.1 model
- Supports long audio chunking (default 30s) to avoid memory issues
- **Key feature**: High-pass filter option to remove low-frequency drum bleed in "no_drums" output
- Default device: CPU (Demucs has MPS compatibility issues, but user can force metal)

**Track Separation Output Options**:

For **4-source models** (`htdemucs`, `htdemucs_ft`):
- **`original.wav`** - Full original track (drums + bass + other + vocals)
- **`drum.wav`** - Isolated drum track only
- **`no_drums.wav`** - Audio without drums (backing track: bass + other + vocals)
- **`no_vocals.wav`** - Audio without vocals (drums + bass + other)
- **`bass.wav`** - Isolated bass track
- **`vocals.wav`** - Isolated vocal track
- **`other.wav`** - Other instruments (everything except drums, bass, vocals)

For **6-source models** (`htdemucs_6s`):
- **`original.wav`** - Full original track (drums + bass + piano + guitar + other + vocals)
- **`drum.wav`** - Isolated drum track only
- **`no_drums.wav`** - Audio without drums (backing track: bass + piano + guitar + other + vocals)
- **`no_vocals.wav`** - Audio without vocals (drums + bass + piano + guitar + other)
- **`bass.wav`** - Isolated bass track
- **`vocals.wav`** - Isolated vocal track
- **`other.wav`** - Other instruments (guitars, synths, horns, strings, etc. - excludes drums, bass, piano, guitar, vocals)
- **`piano.wav`** - Isolated piano track (if using 6-source model)
- **`guitar.wav`** - Isolated guitar track (if using 6-source model)

**Separation Parameters**:
- `clean_no_drums=True` - Apply high-pass filter (default: 180Hz) to "no_drums" output to remove drum bleed
- `cutoff_freq=180.0` - Adjustable cutoff frequency for low-frequency cleanup

**`music_analyzer.py`** / **`music_analyzer_v2.py`** - Music analysis
- `MusicAnalyzer` / `MusicAnalyzerV2` classes
- **BPM Detection**: Multi-algorithm fusion (Librosa + optional madmom/essentia)
- **Style Detection**: Rule-based classification using MFCC, onset strength, spectral contrast
- **Structure Detection**: Identifies intro/verse/chorus/bridge/outro via energy/spectral/onset changes
- **Rhythm Profile**: Pattern type (straight/swing), stability, complexity
- **Key Detection**: Essentia (if available) or Librosa chroma
- **Time Signature**: Beat position analysis (v2 only)

**`drum_generator.py`** - Intelligent drum track generation
- `DrumGenerator` class with 20+ pre-defined rhythm patterns
- Pattern library organized by style (rock, funk, jazz, pop, electronic, hip_hop, etc.)
- **Pattern Selection**: Based on style, BPM, energy, complexity
- **Synthesis Methods**:
  - `_synthesize_drums()`: Basic 4/4 generation
  - `_synthesize_drums_advanced()`: Supports custom time signatures, downbeats
- **Sound Generation**: Synthesized kick (60+40Hz), snare (180+330Hz + noise), hihat (high-freq noise)
- **Dynamic Volumes**: Different volumes per section type (chorus/verse/intro)
- **Fills**: Automatic rolls at end of sections (40% probability if complexity > 0.5)

**`audio_io.py`** - Audio I/O utilities
- Loading/saving with proper format handling
- Mono/stereo conversion
- Long audio chunking for processing

**`youtube_downloader.py`** - YouTube audio extraction
- Uses yt-dlp for downloading

### API Layer (`api/`)

**`server.py`** - FastAPI main server
- Endpoints registered via routers:
  - `/separation/*` - Drum separation endpoints
  - `/analysis/*` - Music analysis endpoints
  - `/generation/*` - Drum generation endpoints
  - `/tracks/*` - Track management
  - `/youtube/*` - YouTube download endpoints
- CORS enabled for all origins (development only)
- Web UI served from `web_ui/`

**Endpoints**:
- `POST /generation/process` - Complete flow (separate + analyze + generate) - **Recommended**
- `POST /generation/generate` - Analyze + generate only
- `POST /separation/separate` - Drum separation (upload + process)
- `POST /separation/separate_by_name` - Process already uploaded file
- `POST /separation/preview` - Quick 30s preview
- `POST /separation/clear` - **NEW**: Delete entire `storage/uploaded/` directory
- `POST /analysis/analyze` - Music analysis only
- `GET /tracks/list` - List tracks from `storage/uploaded/separated/`
- `GET /tracks/status` - **NEW**: Check upload state
- `GET /tracks/audio/{filename}` - Get audio file
- `GET /tracks/info/{filename}` - Get audio info
- `POST /youtube/download` - Download YouTube audio to `storage/uploaded/`
- `POST /youtube/separate` - Download + separate YouTube audio
- `GET /health` - Service health check
- `GET /ui` - Web UI interface

**`endpoints/`** - Route-specific logic:
- `separation.py` - Drum separation endpoint with temp file cleanup
  - `separate_drums()` - POST /separation/separate - Upload + separate
  - `clear()` - POST /separation/clear - Delete uploaded directory
  - `separate_by_name()` - POST /separation/separate_by_name - Process existing file
  - `preview_separation()` - POST /separation/preview - Quick preview
- `generation.py` - Generation endpoints using `MusicAnalyzerV2` and `DrumGenerator`
- `analysis.py` - Analysis endpoint
- `youtube.py` - YouTube download endpoint (saves to `storage/uploaded/`)
- `tracks.py` - Track management endpoint (scans only `storage/uploaded/separated/`)

### CLI Layer (`drum_trainer/`)

**`cli.py`** - Click-based command line interface
- `drum-trainer separate` - Drum separation
- `drum-trainer analyze` - Music analysis
- `drum-trainer generate` - Drum generation
- `drum-trainer complete` - Full processing pipeline
- `drum-trainer info` - System information (PyTorch, device, etc.)

### Web UI (`web_ui/`)
- Simple HTML/CSS/JS interface for API testing
- Served from FastAPI at `/ui` endpoint
- **State Management**: Tracks upload status to control UI panel visibility

#### Web UI State Flow
```
Initial State:
  - trackList: Shows empty state (no tracks)
  - uploadPanel: Visible and enabled
  - uploadBtn: Enabled (clickable)

After File Upload:
  - Upload to server → saved to storage/uploaded/
  - Show file preview info
  - User clicks "Confirm Process"

After Separation (separate_by_name):
  - File moved: uploaded/filename.mp3 → uploaded/separated/temp.mp3
  - Separation runs, creates drum.wav, no_drums.wav, etc.
  - temp.mp3 deleted
  - trackList: Unfolds and shows tracks
  - uploadPanel: Folds and becomes disabled (locked)

After Clear:
  - storage/uploaded/ directory deleted
  - trackList: Shows empty state
  - uploadPanel: Unfolds and becomes enabled (unlocked)
```

#### Web UI JavaScript State Variables
```javascript
let state = {
    selectedFile: null,      // Currently selected file info
    selectedTracks: [],      // Active audio tracks
    uploadVisible: true,     // Upload panel visibility
    uploadLocked: false,     // Upload panel lock state
    apiConnected: false,     // API connection status
};
```

#### Web UI JavaScript Functions
- `handleFileSelect()` - Upload file immediately to server
- `uploadFileForPreview()` - Upload and get preview info
- `processSelectedFile()` - Call separate_by_name to process uploaded file
- `updateAfterSeparation()` - Update UI after separation completes
- `clearSelection()` - Clear all files and reset UI
- `loadTracks()` - Load tracks from `storage/uploaded/separated/`
- `handleYouTubeDownload()` - Download YouTube audio to `storage/uploaded/`
- `updateTrackListUI()` - Update track list display

## Key Implementation Details

### Drum Pattern Library
- 15+ pre-defined patterns in `DrumGenerator._init_pattern_library()`
- Each pattern includes: kick, snare, hihat positions (16th note grid), BPM range, complexity
- **Pattern Selection Algorithm**: Multi-factor scoring (BPM match, energy, complexity)

### Separation Quality Optimization
The `separator.py` includes high-pass filtering to address Demucs' low-frequency bleed:
```python
separator.separate(
    audio_path,
    output_dir,
    clean_no_drums=True,    # Apply high-pass filter
    cutoff_freq=180.0       # Remove <180Hz from "no_drums" output
)
```

### Apple Silicon (MPS) Optimization
- PyTorch automatically uses Metal Performance Shaders when available
- `torch.backends.mps.is_available()` check in `info` command
- Demucs defaults to CPU for stability (can force metal with `device="metal"`)

### Audio Synthesis
- **Kick**: 60Hz + 40Hz sine waves, 120ms duration, transient noise
- **Snare**: 180Hz + 330Hz sines + broadband noise, 100ms duration
- **Hi-hat**: High-frequency noise (8kHz+), 50ms duration
- All sounds use exponential decay envelopes

### Testing Scripts
- `test_complete_solution.py` - Full pipeline test (recommended)
- `test_drum_sound.py` - Verifies kick/snare/hihat frequency characteristics
- `test_separation.py` - Tests separation quality
- `test_separation_improved.py` - Tests different filter cutoff values

## Configuration

### Environment Variables
```bash
DEVICE=auto              # auto, mps, cuda, cpu
CHUNK_DURATION=30        # Long audio split duration (seconds)
MAX_FILE_SIZE=500        # Max upload size (MB)
```

### Dependencies
- **Core**: torch, librosa, soundfile, numpy, scipy, demucs (Git)
- **API**: fastapi, uvicorn, pydantic, python-multipart
- **Optional**: essentia, madmom (improved analysis, may require compilation)
- **YouTube**: yt-dlp

## Common Tasks

### Fixing a Bug
1. Identify which module is affected (separator, analyzer, generator, API)
2. Check the corresponding file in `core/` or `api/endpoints/`
3. Add logging with `print()` statements for debugging
4. Test with `uv run python test_complete_solution.py`

### Adding a New Rhythm Pattern
Edit `core/drum_generator.py` → `_init_pattern_library()`:
```python
"your_pattern_name": DrumPattern(
    name="your_pattern_name",
    style="genre_name",  # Must match existing style
    bpm_range=(min_bpm, max_bpm),
    kick_pattern=[0, 4, 8, 12],    # 16th note positions
    snare_pattern=[4, 12],
    hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],
    complexity=0.5
)
```

### Modifying Drum Sound Synthesis
Edit the `_add_kick()`, `_add_snare()`, `_add_hihat()` methods in `core/drum_generator.py`:
- Adjust frequencies, envelopes, noise characteristics
- Test with `test_drum_sound.py` to verify frequency distribution

### Adjusting Separation Quality
Edit `core/separator.py` → `_merge_results()`:
- Change `cutoff_freq` default from 180.0
- Adjust high-pass filter order in `_highpass_filter()`

### Adding New API Endpoint
1. Create endpoint file in `api/endpoints/`
2. Import in `api/server.py`
3. Add `app.include_router(router)` to register

## Important Notes

- **Demucs v4.0.1** is pinned in `pyproject.toml` - still SOTA for drum separation
- **Essentia** is optional - core functionality works without it
- **Model downloads** happen automatically on first run (~1.5GB, stored in `storage/models/`)
- **Temp files** are automatically cleaned up after processing
- **Apple Silicon** support is primary focus (MPS acceleration)
- **Demucs device selection**: Defaults to CPU for stability; MPS can be forced but may have issues

## Troubleshooting

### Issue: "Demucs 未安装"
```bash
uv add demucs @ git+https://github.com/facebookresearch/demucs.git@v4.0.1
```

### Issue: PyTorch MPS not available
```bash
# Check version
uv run python -c "import torch; print(torch.__version__)"
# Should be >= 2.0.0
# If not, reinstall: rm -rf .venv && uv sync
```

### Issue: Low memory with long audio
```bash
# Reduce chunk duration
uv run drum-trainer complete song.mp3 --chunk-size 15
```

### Issue: Essentia installation fails
- Skip it - not required for core functionality
- Run `uv sync` without optional dependencies

## Test Audio
- Use songs with clear structure (2-5 minutes recommended)
- Formats: mp3, wav, flac
- Good genres: Rock, pop, jazz (for testing analysis accuracy)
