---
title: Drum Trainer
emoji: 🥁
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# 🥁 Drum Trainer

AI-powered drum separation, transcription, and music analysis tool.

## ✨ Features

### 🎵 Drum Separation (Demucs AI)
- Facebook Demucs v4.0.1 for drum isolation
- Long audio chunked processing (avoids memory overflow)
- Output: drums only, backing track, full mix

### 📊 Music Analysis
- **Style detection**: rock, jazz, pop, electronic, hip_hop, funk, etc.
- **BPM detection**: multi-algorithm fusion
- **Song structure**: intro, verse, chorus, bridge, outro
- **Rhythm features**: pattern, stability, complexity
- **Key detection**: C, G, D, A, etc.
- **Mood analysis**: energetic, relaxed, happy, etc.

### 🥁 5-Phase Drum Transcription Pipeline
1. **Sub-band onset detection** — frequency band splitting + independent onset detection
2. **Hit decomposition** — cross-frequency correlation + spectral template matching
3. **Genre pattern matching** — rock/pop/funk/electronic templates, 16-step quantized grid
4. **Music theory post-processing** — downbeat kick, upbeat snare, hihat continuity rules
5. **Fill detection** — tom_roll, snare_roll, linear, syncopated, etc.

### 🎼 Notation & MIDI Export
- Drum notation JSON with staff position mapping
- Standard General MIDI drum mapping export
- Ghost notes, accents, open hat markers

### 🥁 Smart Generation
- AI-generated drum performances based on music analysis
- 20+ predefined rhythm patterns
- Auto-matches style, tempo, and complexity

## 🚀 Quick Start

### Local Development

```bash
# Install dependencies
uv sync

# Start API server
uv run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

Access:
- **Web UI**: http://localhost:8000/ui
- **API Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Docker

```bash
docker build -t drum-trainer .
docker run -p 7860:7860 drum-trainer
```

## 🔧 API Usage

### Full Processing (Recommended)
```bash
curl -X POST "http://localhost:8000/generation/process" \
  -F "file=@song.mp3" -o result.json
```

### Drum Transcription
```bash
curl -X POST "http://localhost:8000/transcription/transcribe?method=enhanced" \
  -F "file=@song.mp3"
```

### Drum Separation
```bash
curl -X POST "http://localhost:8000/separation/separate" \
  -F "file=@song.mp3" -F "chunk_duration=30"
```

## 🔧 Tech Stack

- **Python 3.10-3.12** + PyTorch 2.4.1
- **Demucs v4.0.1** — source separation (SOTA, SDR 9.2dB)
- **Librosa** — audio analysis
- **Madmom** — beat tracking
- **FastAPI** — web service
- **HTML5 / CSS3 / JS** — dark theme UI with Canvas visualization

## 📄 License

MIT License
