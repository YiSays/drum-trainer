# 🥁 Drum Trainer Flutter Web App - Index

This directory contains the Flutter web application for Drum Trainer.

## 📁 Project Structure

```
web/
├── lib/
│   ├── main.dart                 # Main entry point
│   ├── screens/                  # UI Screens
│   │   ├── home_screen.dart      # Track browser & dashboard
│   │   ├── track_player_screen.dart  # Audio player with controls
│   │   ├── separation_screen.dart    # File upload & drum separation
│   │   └── analysis_screen.dart      # Music analysis view
│   ├── widgets/                  # Reusable UI Components
│   │   ├── track_card.dart       # Track list item
│   │   ├── waveform_visualizer.dart  # Waveform display
│   │   ├── volume_slider.dart    # Volume control widget
│   └── models/                   # Data Models
│       ├── track_model.dart      # Track data model
│       └── api_models.dart       # API response models
│   └── services/                 # Business Logic
│       ├── api_service.dart      # API client for FastAPI
│       └── audio_service.dart    # Audio playback service
│
├── assets/                       # Static Assets
│   ├── images/                   # App images
│   └── fonts/                    # Custom fonts (optional)
│
├── web/                          # Web-specific Configuration
│   └── index.html                # HTML entry point
│
├── pubspec.yaml                  # Flutter Dependencies
├── README.md                     # Detailed Documentation
├── INDEX.md                      # This file
└── .gitignore                    # Git ignore rules
```

## 🎯 Core Features

### 1. Track Browser (Home Screen)
- Browse all tracks from the backend
- Search/filter functionality
- Quick play/analyze actions
- API connection status indicator

### 2. Audio Player
- **Controls**: Play, Pause, Stop, Loop toggle
- **Seek Bar**: Timeline navigation
- **Volume Control**: 0-100% adjustment
- **Speed Control**: 0.5x - 2.0x playback speed
- **Waveform Visualization**: Real-time frequency bars

### 3. Music Analysis
- **BPM Detection**: Beat-per-minute analysis
- **Style Recognition**: Rock, Jazz, Pop, etc.
- **Mood Analysis**: Emotional classification
- **Key Detection**: Musical key
- **Energy Level**: 0-100% intensity
- **Structure**: Intro/Verse/Chorus/Bridge segments
- **Rhythm Profile**: Pattern analysis & practice tips

### 4. File Upload & Separation
- Upload audio files via file picker
- Automatic drum separation using Demucs AI
- Progress indicator during processing
- Results display with file paths

### 5. API Integration
- Health check
- Track listing
- Audio streaming
- Music analysis
- Drum separation
- Drum generation

## 🔧 Key Components

### API Service (`lib/services/api_service.dart`)
```dart
class ApiService {
  static const String baseUrl = 'http://localhost:8000';

  // Methods:
  - checkHealth()
  - getTracks()
  - getAudioUrl(filename)
  - getAudioInfo(filename)
  - separateAudio(file)
  - analyzeAudio(file)
  - generateDrums(file)
  - completeProcess(file)
}
```

### Audio Service (`lib/services/audio_service.dart`)
```dart
class AudioService extends ChangeNotifier {
  // Single track playback
  - loadTrack(track, url)
  - play()
  - pause()
  - stop()
  - seek(position)
  - setVolume(value)
  - setPlaybackSpeed(value)
  - toggleLoop()

  // Multi-track mixing
  - addTrackToMix(track, url)
  - startMix()
  - stopMix()
}
```

## 🔌 API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check API connectivity |
| `/tracks/list` | GET | Get all available tracks |
| `/tracks/audio/{name}` | GET | Stream audio file |
| `/tracks/info/{name}` | GET | Get audio metadata |
| `/separation/separate` | POST | Upload & separate audio |
| `/analysis/analyze` | POST | Analyze music |
| `/generation/generate` | POST | Generate drums |

## 📦 Dependencies

Key packages in `pubspec.yaml`:

```yaml
dependencies:
  http: ^1.2.0                    # API calls
  provider: ^6.1.1                # State management
  just_audio: ^0.9.37             # Audio playback
  audio_video_progress_bar: ^2.0.0  # Seek bar UI
  file_picker: ^6.1.1             # File selection
  shimmer: ^3.0.0                 # Loading animations
  flutter_hooks: ^0.20.5          # UI hooks
  universal_platform: ^1.1.0      # Platform detection
```

## 🚀 Quick Start

### 1. Start Backend
```bash
cd /Users/Sheldon/Dev/drum-trainer
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

### 2. Run Flutter App
```bash
cd /Users/Sheldon/Dev/drum-trainer/web
flutter pub get
flutter run -d chrome
```

### 3. Verify Connection
- App should show "API 已连接" (green indicator)
- Track list should load automatically
- Click a track to start playing

## 🎨 UI/UX Design

### Color Scheme
- **Background**: #0A0A0F (Dark)
- **Primary**: #8B5CF6 (Purple/Violet)
- **Accent**: #FBBF24 (Gold/Yellow)
- **Success**: #10B981 (Green)
- **Error**: #EF4444 (Red)
- **Text**: #F8FAFC (White), #CBD5E1 (Light gray)

### Typography
- **Inter** (Primary font)
  - Regular, Medium, SemiBold, Bold
- **Monospace** (for time/numerical data)

### Layout
- **Desktop**: Split view (Track list left, Player right)
- **Mobile**: Single column, bottom player bar
- **Responsive**: Adapts to screen size

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `Esc` | Stop |
| `←` / `→` | Seek -5s / +5s |
| `R` | Refresh tracks |
| `U` | Toggle upload panel |

## 📊 State Management

The app uses **Provider** for state management:

- **ApiService**: Singleton API client
- **AudioService**: Manages all audio playback state
  - Current track
  - Playback state (playing/paused)
  - Volume & speed
  - Loop mode
  - Position & duration
  - Multi-track mixing state

## 🧪 Testing

### Unit Tests
```bash
flutter test
```

### Manual Testing Checklist
- [ ] API connection detected
- [ ] Track list loads
- [ ] Search/filter works
- [ ] Play audio starts
- [ ] Pause/resume works
- [ ] Stop resets position
- [ ] Seek bar updates position
- [ ] Volume slider adjusts volume
- [ ] Speed slider adjusts playback rate
- [ ] Loop toggle works
- [ ] Waveform visualizes during playback
- [ ] Analysis screen shows data
- [ ] File upload works (if Flutter installed)

## 🔧 Configuration

### API Base URL
File: `lib/services/api_service.dart`
```dart
static const String baseUrl = 'http://localhost:8000';
```

### CORS Requirements
Ensure FastAPI backend has CORS enabled:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🐛 Troubleshooting

### "Cannot connect to API"
- Check backend is running: `curl http://localhost:8000/health`
- Check CORS configuration in FastAPI
- Verify port 8000 is accessible

### "Audio won't play"
- Click play button once (browser requires user interaction)
- Check that audio file exists in backend
- Verify CORS headers on audio endpoint

### "Flutter not found"
- Install Flutter: https://flutter.dev/docs/get-started/install
- Enable web: `flutter config --enable-web`
- Run: `flutter doctor` to verify installation

## 📝 Deployment

### Local Development
```bash
flutter run -d chrome
```

### Production Build
```bash
flutter build web --release
# Output: build/web/
```

### Deploy to Hosting
- **GitHub Pages**: `gh-pages` branch
- **Netlify**: Drag and drop build/web/
- **Vercel**: Connect GitHub repository
- **Firebase Hosting**: `firebase deploy`

## 🎯 Success Criteria

### MVP Features (Complete)
- [x] Track browser with search
- [x] Audio playback controls
- [x] Volume control
- [x] Seek bar with time display
- [x] Waveform visualization
- [x] API integration
- [x] Music analysis view
- [x] File upload & separation UI

### Advanced Features (Planned)
- [ ] Multi-track mixing (drums + backing)
- [ ] Loop functionality
- [ ] Tempo adjustment
- [ ] Metronome/count-in
- [ ] Theme switching (dark/light)

## 📚 Resources

- [Flutter Documentation](https://flutter.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [Drum Trainer Backend](../api/)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - See main project license

---

**Last Updated**: 2026-01-15
**Version**: 1.0.0
**Status**: In Development
