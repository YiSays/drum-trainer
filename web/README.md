# Drum Trainer Web (Flutter)

🥁 A modern Flutter web application for drum practice with AI-powered music analysis and drum separation.

## ✨ Features

- **Track Browser**: Browse and select audio tracks from the backend
- **Audio Player**: Play/pause, seek, volume control, speed adjustment
- **Waveform Visualization**: Real-time audio frequency visualization
- **Practice Mode**: Multi-track mixing, metronome/count-in, loop playback
- **Music Analysis**: BPM detection, style recognition, mood analysis
- **File Upload**: Upload audio files for drum separation via Demucs AI

## 🚀 Getting Started

### Prerequisites

- Flutter SDK (>= 3.3.0)
- FastAPI backend running on `http://localhost:8000`

### Backend Setup

Make sure the FastAPI backend is running:

```bash
cd /Users/Sheldon/Dev/drum-trainer
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

The backend should be accessible at `http://localhost:8000`. Verify with:
```bash
curl http://localhost:8000/health
```

### Running the App

**Note**: Flutter SDK is required to run the web app. If Flutter is not installed:

1. **Install Flutter**: Follow the [official Flutter installation guide](https://flutter.dev/docs/get-started/install)

2. **Enable Web Support**:
```bash
flutter config --enable-web
```

3. **Run the App**:
```bash
cd /Users/Sheldon/Dev/drum-trainer/web

# Get dependencies
flutter pub get

# Run on Chrome
flutter run -d chrome
```

The app will be available at `http://localhost:XXXX` (auto-assigned port).

### Building for Production

```bash
cd /Users/Sheldon/Dev/drum-trainer/web

# Build web app
flutter build web --release

# The built files will be in build/web/
# You can deploy them to any static hosting service
```

### Alternative: Manual Deployment

If Flutter is not available, you can:
1. Deploy the existing `web_ui/` directory (plain HTML/JS)
2. Or install Flutter and build the Flutter web app

### Pre-built Web App

If you need to use the Flutter web app without building:
1. Install Flutter SDK
2. Run `flutter pub get` in `web/` directory
3. Run `flutter run -d chrome`

## 📁 Project Structure

```
web/
├── lib/
│   ├── main.dart                      # Entry point
│   ├── screens/
│   │   ├── home_screen.dart           # Main dashboard
│   │   ├── track_player_screen.dart   # Audio player with controls
│   │   ├── separation_screen.dart     # File upload & separation
│   │   └── analysis_screen.dart       # Music analysis view
│   ├── widgets/
│   │   ├── track_card.dart            # Track list item
│   │   ├── audio_player_widget.dart   # Audio player widget
│   │   ├── waveform_visualizer.dart   # Waveform display
│   │   └── volume_slider.dart         # Volume control
│   ├── models/
│   │   ├── track_model.dart           # Track data model
│   │   └── api_models.dart            # API response models
│   └── services/
│       ├── api_service.dart           # API client
│       └── audio_service.dart         # Audio playback service
├── assets/
│   ├── images/                        # App images
│   └── fonts/                         # Custom fonts
├── web/
│   └── index.html                     # Web configuration
└── pubspec.yaml                       # Dependencies
```

## 🔌 API Endpoints Used

The Flutter app connects to the FastAPI backend at `http://localhost:8000`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/tracks/list` | GET | List all available tracks |
| `/tracks/audio/{filename}` | GET | Stream audio file |
| `/tracks/info/{filename}` | GET | Get audio metadata |
| `/separation/separate` | POST | Upload and separate audio |
| `/analysis/analyze` | POST | Analyze music (BPM, style, etc.) |

## 🎨 UI/UX Design

### Color Scheme
- **Primary**: Purple/Violet (#8B5CF6) - Musical theme
- **Accent**: Gold/Yellow (#FBBF24) - Controls and highlights
- **Background**: Dark theme (#0A0A0F) - Reduced eye strain for practice

### Layout
- **Desktop (> 1024px)**: Split view - Track list on left, player on right
- **Tablet (640-1024px)**: Single column layout
- **Mobile (< 640px)**: Compact controls, bottom player bar

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `Esc` | Stop |
| `←` / `→` | Seek -5s / +5s |
| `R` | Refresh track list |
| `U` | Toggle upload section |

## 🔧 Configuration

### API Base URL

The API base URL is configured in `lib/services/api_service.dart`:

```dart
class ApiService {
  static const String baseUrl = 'http://localhost:8000';
  // ...
}
```

For production deployment, update this to your backend URL.

### CORS Configuration

The FastAPI backend should have CORS enabled:

```python
# In api/server.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🧪 Testing

### Unit Tests

```bash
flutter test
```

### Integration Tests

```bash
flutter drive \
  --driver=test_driver/integration_test.dart \
  --target=integration_test/app_test.dart \
  -d chrome
```

## 📚 Dependencies

Key packages used:

- **http**: API communication
- **provider**: State management
- **just_audio**: Audio playback
- **audio_video_progress_bar**: Seek bar UI
- **file_picker**: File selection for upload
- **shimmer**: Loading animations
- **flutter_hooks**: UI hooks

## 🐛 Troubleshooting

### CORS Issues

**Problem**: Browser blocks requests to the backend

**Solution**: Ensure FastAPI server is running and CORS is configured

### Audio Not Playing

**Problem**: Audio won't start in browser

**Solution**: Click the play button once to initialize the audio context (browser requires user interaction)

### API Connection Error

**Problem**: "Cannot connect to API"

**Solution**: Check that FastAPI server is running at `http://localhost:8000`

## 📝 Development Notes

### Audio Handling on Web

The `just_audio` package uses the Web Audio API for audio playback. Note that:
- Audio context requires user interaction to start
- Some browsers may have limitations on audio playback
- CORS headers are required for audio streaming

### State Management

This app uses Provider for state management:
- `TrackProvider`: Manages track list and selection
- `PlayerProvider`: Manages audio playback state
- `AnalysisProvider`: Manages music analysis data

### Performance Considerations

- Waveform visualization uses requestAnimationFrame for smooth 60fps
- Lazy loading for track data
- Efficient audio buffer management

## 🎯 Roadmap

### Phase 1: Core Player (MVP)
- [x] Track browser
- [x] Audio playback controls
- [x] Volume control
- [x] Waveform visualization

### Phase 2: Practice Features
- [ ] Multi-track mixing
- [ ] Loop functionality
- [ ] Tempo adjustment
- [ ] Metronome/count-in

### Phase 3: Integration
- [ ] File upload UI
- [ ] Separation progress
- [ ] Analysis results display
- [ ] Theme switching

## 🤝 Contributing

Contributions are welcome! Please read the main project README for guidelines.

## 📄 License

MIT License - See main project license

## 🎵 Credits

Built with ❤️ for drummers and music enthusiasts.
