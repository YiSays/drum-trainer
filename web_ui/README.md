# Drum Trainer Web UI

## 🥁 Overview

A modern web interface for the Drum Trainer project, featuring:
- Track browser with audio player
- Real-time audio waveform visualization
- Music analysis (BPM, style, mood, energy)
- File upload with automatic drum separation
- Multi-track mixing for practice sessions
- Keyboard shortcuts for efficient workflow

## ✨ Features

### 1. Track Browser
- List all audio tracks from the `separation_180hz/` folder
- Display track metadata (duration, size, channels)
- Quick play/analyze actions for each track

### 2. Audio Player
- **Playback controls**: Play, Pause, Stop
- **Seek bar**: Jump to any position in the track
- **Volume control**: Adjustable volume (0-100%)
- **Playback speed**: 0.5x to 2.0x speed adjustment
- **Loop mode**: Loop playback for practice
- **Real-time waveform visualization**: Using Web Audio API

### 3. Practice Mode
- **Multi-track mixing**: Play drums + backing track simultaneously
  - Select drum track
  - Select backing track (e.g., bass track)
  - Adjustable volumes for each
  - Sync playback

### 4. Music Analysis
- **BPM detection**: Beat-per-minute analysis
- **Style recognition**: Rock, jazz, pop, electronic, etc.
- **Mood analysis**: Emotional classification
- **Energy level**: 0-100% intensity
- **Key/tonality**: Musical key detection

### 5. File Upload
- Upload audio files (MP3, WAV, FLAC, OGG, M4A)
- Automatic drum separation via Demucs AI
- Integration with music analysis
- Progress indicators

**YouTube Download**: Downloads audio as M4A (AAC) format at 192kbps for universal browser compatibility.

### 6. Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `Esc` | Stop |
| `←` / `→` | Seek -5s / +5s |
| `R` | Refresh track list |
| `U` | Toggle upload section |

## 🚀 Usage

### Prerequisites
- FastAPI backend running on `http://localhost:8000`
- Audio tracks in `separation_180hz/` folder

### Start the Server

```bash
# Start the FastAPI backend
cd /Users/Sheldon/Dev/drum-trainer
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

### Access the Web UI

Open your browser and navigate to:

```
http://localhost:8000/ui
```

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────┐
│ Header: Drum Trainer                  [Status: Connected] │
├─────────────────────────────────────────────────────┤
│ LEFT PANEL (Track List)      │ RIGHT PANEL (Player) │
│                              │                      │
│ [📤 Upload] [🔄 Refresh]     │ ┌──────────────────┐ │
│                              │ │ Now Playing      │ │
│ Upload Section (collapsible) │ │ [Waveform]       │ │
│                              │ └──────────────────┘ │
│ Track Items:                 │ ┌──────────────────┐ │
│ - drums_only.wav             │ │ ▶️ ⏸️ ⏹️         │ │
│   [📊 Analyze] [▶️ Play]     │ │ Seek: ░░░░░░ 0:00/1:23 │ │
│ - bass.wav                   │ │ 🔊 Volume: 80%   │ │
│ - no_drums.wav               │ │ ⚡ Speed: 1.0x   │ │
│                              │ │ 🔁 Loop          │ │
│                              │ └──────────────────┘ │
│                              │ ┌──────────────────┐ │
│                              │ │ 🎯 Practice Mode │ │
│                              │ │ 🎚️ Mix Mode      │ │
│                              │ │   🥁 Drum: [sel] │ │
│                              │ │   🎵 Back: [sel] │ │
│                              │ │   [▶️ Play Mix]  │ │
│                              │ └──────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 🔌 API Endpoints Used

### Backend API (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check API status |
| `/tracks/list` | GET | List all tracks |
| `/tracks/audio/{name}` | GET | Stream audio file |
| `/analysis/analyze` | POST | Analyze music (BPM, style, etc.) |
| `/separation/separate` | POST | Upload and separate audio |

## 💻 Technology Stack

### Frontend
- **HTML5** - Structure
- **CSS3** - Styling (Dark theme, gradients, animations)
- **JavaScript (ES6+)** - Logic and interactivity
- **Web Audio API** - Real-time audio analysis and visualization

### Backend
- **FastAPI** - Web server and API
- **Demucs AI** - Drum separation
- **Music Analysis V2** - BPM and style detection
- **yt-dlp** - YouTube audio download (M4A format)

## 🎵 Audio Format Support

### Input Formats (Direct Upload)
| Format | Codec | Notes |
|--------|-------|-------|
| MP3 | MPEG-1/2 Audio Layer III | Most common, good compatibility |
| WAV | PCM (lossless) | Uncompressed, highest quality |
| FLAC | Free Lossless Audio Codec | Lossless compression |
| OGG | Vorbis | Open format, good compression |
| M4A | AAC | Apple format, good quality/size |

### YouTube Downloads
- **Format**: M4A (AAC codec)
- **Bitrate**: 192kbps
- **Why**: Universal browser compatibility (including Safari/iOS), Demucs compatible
- **Size**: ~5-10MB for 5min song

### Separation Output
- **Format**: WAV (uncompressed)
- **Tracks**: drums.wav, bass.wav, other.wav, vocals.wav (4-source)
- **Additional** (htdemucs_6s): piano.wav, guitar.wav
- **Size**: ~50MB per track
- **Note**: Lossless output for professional audio quality

### Browser Compatibility
| Browser | Playback | Upload | YouTube Download |
|---------|----------|--------|------------------|
| Chrome | ✅ Full | ✅ Full | ✅ Full |
| Firefox | ✅ Full | ✅ Full | ✅ Full |
| Safari | ✅ Full | ✅ Full | ✅ Full (M4A) |
| Edge | ✅ Full | ✅ Full | ✅ Full |

## 🎛️ Web Audio API Features

### Real-time Visualization
The waveform display uses the Web Audio API's `AnalyserNode` to provide:
- Frequency bars (FFT analysis)
- Color-coded gradients (blue → purple)
- Smooth animations at 60 FPS

### Audio Context
- Single `AudioContext` shared between players
- Efficient analysis without blocking the UI
- Automatic suspension/resumption for battery saving

## 📁 File Structure

```
web_ui/
├── index.html          # Main HTML file
├── css/
│   └── style.css       # Styling (Dark theme, responsive)
└── js/
    └── app.js          # JavaScript application logic
```

## 🎯 Keyboard Shortcuts

For efficient practice sessions:

- **Space**: Toggle play/pause
- **Esc**: Stop playback
- **← / →**: Skip backward/forward 5 seconds
- **R**: Refresh track list
- **U**: Toggle upload section

## 🔧 Configuration

### API Base URL
Edit `API_BASE_URL` in `js/app.js` if running on a different host/port:

```javascript
const API_BASE_URL = 'http://localhost:8000';  // Default
```

### Canvas Waveform Size
In `index.html`:

```html
<canvas id="waveform" width="800" height="100"></canvas>
```

Adjust `width` and `height` for different display sizes.

## 📱 Responsive Design

The interface adapts to different screen sizes:

- **Desktop (>1024px)**: Split view with track list on left, player on right
- **Tablet (640-1024px)**: Single column layout
- **Mobile (<640px)**: Compact controls, stacked layout

## 🐛 Troubleshooting

### "API not connected"
- Check FastAPI server is running: `curl http://localhost:8000/health`
- Check CORS settings in `api/server.py`

### "No tracks found"
- Ensure `separation_180hz/` folder exists with audio files
- Check file permissions

### "Audio won't play"
- Browser requires user interaction to play audio
- Try clicking play button first
- Check browser console for errors

### Web Audio API Issues
- Some browsers require user gesture to start AudioContext
- Click the play button once to initialize

## 📝 Example Workflow

1. **Start server**: `uvicorn api.server:app --reload`
2. **Open browser**: `http://localhost:8000/ui`
3. **Load tracks**: Click "🔄 Refresh"
4. **Select track**: Click on a track item
5. **Play**: Press Space or click ▶️
6. **Mix**: Select drum + backing tracks, click "▶️ Play Mix"
7. **Analyze**: Click "📊 Analyze" on any track

## 🎼 Music Theory Integration

### BPM Display
When analyzing tracks, BPM is shown in the UI. This is useful for:
- Matching backing tracks
- Practicing at specific speeds

### Structure Visualization
The analysis shows:
- Intro/Verse/Chorus/Bridge sections
- Downbeat positions
- Rhythm patterns

## ⚡ Performance Tips

1. **Waveform**: Uses requestAnimationFrame for smooth 60fps
2. **Audio Context**: Shared between players for efficiency
3. **Lazy Loading**: Tracks loaded on demand
4. **Cache**: Browser caches audio files

## 📚 References

- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Drum Trainer Backend](../api/README.md)

---

**Note**: This is a frontend interface for the Drum Trainer backend. Ensure the FastAPI server is running before using the web UI.
