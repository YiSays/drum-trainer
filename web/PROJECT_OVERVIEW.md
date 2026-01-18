# 🥁 Drum Trainer Flutter Web - Project Overview

## Quick Start Guide

### Prerequisites
1. **Flutter SDK** (>= 3.3.0)
2. **FastAPI Backend** running on port 8000

### Step-by-Step Setup

#### 1. Install Flutter (if not installed)
```bash
# macOS
brew install flutter
flutter --version

# Or download from:
# https://flutter.dev/docs/get-started/install
```

#### 2. Enable Web Support
```bash
flutter config --enable-web
flutter doctor
```

#### 3. Start Backend
```bash
cd /Users/Sheldon/Dev/drum-trainer
uvicorn api.server:app --host 0.0.0.0 --port 8000
```

#### 4. Run Flutter App
```bash
cd /Users/Sheldon/Dev/drum-trainer/web
flutter pub get
flutter run -d chrome
```

The app will open in Chrome at `http://localhost:XXXX`

---

## 📁 File Structure

```
web/
├── lib/
│   ├── main.dart                          (125 lines)
│   │
│   ├── models/
│   │   ├── track_model.dart              (225 lines)
│   │   └── api_models.dart               (450 lines)
│   │
│   ├── services/
│   │   ├── api_service.dart              (180 lines)
│   │   └── audio_service.dart            (350 lines)
│   │
│   ├── screens/
│   │   ├── home_screen.dart              (220 lines)
│   │   ├── track_player_screen.dart      (380 lines)
│   │   ├── separation_screen.dart        (260 lines)
│   │   └── analysis_screen.dart          (350 lines)
│   │
│   └── widgets/
│       ├── track_card.dart                (150 lines)
│       ├── waveform_visualizer.dart       (220 lines)
│       └── volume_slider.dart             (60 lines)
│
├── web/
│   └── index.html                        (HTML config)
│
├── pubspec.yaml                          (Dependencies)
├── README.md                             (User Guide)
├── INDEX.md                              (Developer Index)
├── PROJECT_OVERVIEW.md                   (This file)
└── .gitignore                            (Git rules)
```

**Total**: 20 files, ~3,000 lines of Dart code

---

## 🎯 Core Screens

### 1. Home Screen (`home_screen.dart`)
**Purpose**: Track browser and dashboard

**Features**:
- API status indicator (connected/disconnected)
- Search/filter tracks
- List of all available tracks
- Track metadata display
- Quick actions: Play, Analyze

**UI Components**:
```
┌─────────────────────────────────────────────────────┐
│ 🥁 Drum Trainer Web                 [↻ Refresh]     │
├─────────────────────────────────────────────────────┤
│ ● API 已连接                         [📤上传&分离]  │
├─────────────────────────────────────────────────────┤
│ 🔍 搜索音轨...                                        │
├─────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🥁 drum.wav                                     │ │
│ │ ⏱1:23   📁5.2MB   🎵立体声                      │ │
│ │ [📊分析] [▶播放]                                │ │
│ └─────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 🎸 bass.wav                                     │ │
│ │ ⏱2:15   📁8.5MB   🎵立体声                      │ │
│ │ [📊分析] [▶播放]                                │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2. Track Player Screen (`track_player_screen.dart`)
**Purpose**: Audio playback with controls

**Features**:
- Now playing header with track info
- Waveform visualization
- Play/Pause/Stop controls
- Loop toggle
- Seek bar with time display
- Volume slider (0-100%)
- Speed slider (0.5x - 2.0x)

**UI Components**:
```
┌─────────────────────────────────────────────────────┐
│ ← drum.wav                                          │
├─────────────────────────────────────────────────────┤
│ 🥁 drum.wav                                         │
│ ⏱1:23   📁5.2MB   🎵立体声                         │
├─────────────────────────────────────────────────────┤
│ [⏹停止] [▶播放] [🔁循环]                            │
├─────────────────────────────────────────────────────┤
│ ▁▂▃▄▅▆▇█▆▄▃▂    ▂▃▄▅▆▇█▆▄▃▂                        │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│ 0:00                      / 1:23                    │
├─────────────────────────────────────────────────────┤
│ 🔊 音量                    80%                       │
│ ⚡ 速度                    1.0x                      │
└─────────────────────────────────────────────────────┘
```

### 3. Separation Screen (`separation_screen.dart`)
**Purpose**: Upload and separate audio files

**Features**:
- File picker (MP3, WAV, FLAC, OGG)
- File size validation (100MB limit)
- Progress indicator
- Status messages
- Results display
- Error handling

**UI Components**:
```
┌─────────────────────────────────────────────────────┐
│ 上传 & 分离 ←                                       │
├─────────────────────────────────────────────────────┤
│   📤                                              │
│   选择音频文件                                      │
│   MP3, WAV, FLAC, OGG (最大 100MB)                │
│                                                   │
│   [选择文件]                                       │
│                                                   │
│   drum.wav                                        │
├─────────────────────────────────────────────────────┤
│ 分离中... (AI 处理)        60%                     │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                   │
│ 正在使用 Demucs AI 进行鼓声分离...                 │
├─────────────────────────────────────────────────────┤
│ ✓ 分离完成!                                       │
│                                                   │
│ 生成的文件:                                        │
│ 🎵 鼓声 (Drums Only)  drum.wav                    │
│ 🎵 无鼓伴奏 (No Drums) no_drums.wav               │
│ 🎵 混合 (Mixed)       mixed.wav                   │
└─────────────────────────────────────────────────────┘
```

### 4. Analysis Screen (`analysis_screen.dart`)
**Purpose**: Music analysis results display

**Features**:
- BPM detection
- Style recognition
- Mood analysis
- Energy level
- Key/tonality
- Song structure (intro, verse, chorus)
- Rhythm pattern analysis
- Practice tips

**UI Components**:
```
┌─────────────────────────────────────────────────────┐
│ 音乐分析 ←                                      [↻] │
├─────────────────────────────────────────────────────┤
│ 🥁 drum.wav                                         │
│ ⏱1:23                                              │
├─────────────────────────────────────────────────────┤
│ 分析概览                                           │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │  BPM     │ │  风格    │ │  情绪    │ │  调性    │ │
│ │   128    │ │   Rock   │ │Energetic │ │    C     │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                    │
│ 能量                     85%                        │
│ ━━━━━━━━━━━━━━━━━━━━━━━━                           │
├─────────────────────────────────────────────────────┤
│ BPM (每分钟节拍数)                                 │
│           128               ♥                       │
├─────────────────────────────────────────────────────┤
│ 歌曲结构                                           │
│ [INTRO 16s] [VERSE 32s] [CHORUS 32s] [CHORUS 32s]  │
│ 段落统计: 1x intro, 1x verse, 2x chorus            │
├─────────────────────────────────────────────────────┤
│ 节奏特征                                           │
│ rock_standard     复杂度 45%                       │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━                          │
│ 💡 基础节奏练习：保持稳定的四分音符                 │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Key Components

### ApiService (`lib/services/api_service.dart`)
```dart
// Base URL
static const String baseUrl = 'http://localhost:8000';

// Methods:
- checkHealth()                    // GET /health
- getTracks()                      // GET /tracks/list
- getAudioUrl(filename)            // GET /tracks/audio/{name}
- getAudioInfo(filename)           // GET /tracks/info/{name}
- separateAudio(file)              // POST /separation/separate
- analyzeAudio(file)               // POST /analysis/analyze
- generateDrums(file)              // POST /generation/generate
- completeProcess(file)            // POST /generation/process
```

### AudioService (`lib/services/audio_service.dart`)
```dart
// Single Track Playback
- loadTrack(track, url)            // Load audio
- play()                           // Play
- pause()                          // Pause
- stop()                           // Stop & reset
- seek(position)                   // Jump to position
- setVolume(value)                 // 0.0 - 1.0
- setPlaybackSpeed(value)          // 0.5 - 2.0
- toggleLoop()                     // Loop on/off

// Multi-Track Mixing (Future)
- addTrackToMix(track, url)        // Select for mix
- startMix()                       // Play multiple
- stopMix()                        // Stop all
```

### Models
- **Track**: Name, duration, size, channels, sample rate
- **AudioInfo**: Detailed metadata + BPM, style, mood
- **AnalysisResult**: BPM, style, mood, energy, key, structure, rhythm
- **SeparationResult**: File paths for drums, no_drums, mixed

---

## 🎨 Visual Design

### Color Palette
```dart
Background:    #0A0A0F  (Dark)
Primary:       #8B5CF6  (Purple)
Accent:        #FBBF24  (Gold)
Success:       #10B981  (Green)
Error:         #EF4444  (Red)
Text Primary:  #F8FAFC  (White)
Text Muted:    #94A3B8  (Gray)
Border:        #334155  (Dark Gray)
```

### Typography
- **Inter** font family
- Sizes: 11px, 12px, 13px, 14px, 16px, 18px, 20px, 24px, 32px
- Weights: 400, 500, 600, 700, 800, 900
- Monospace for time/numerical data

### Spacing
- 4px, 8px, 12px, 16px, 20px, 24px, 32px (8pt grid)

---

## 🔌 API Integration Flow

```
App Start
   ↓
Check Health (/health)
   ↓
Load Tracks (/tracks/list)
   ↓
Display Track List
   ↓
User Interaction
   ├─▶ Play Track
   │   ↓
   │   Get Audio URL (/tracks/audio/{name})
   │   ↓
   │   AudioService.play()
   │   ↓
   │   Waveform Visualization
   │
   ├─▶ Analyze Track
   │   ↓
   │   Analyze API (/analysis/analyze)
   │   ↓
   │   Display Analysis Results
   │
   └─▶ Upload & Separate
       ↓
       File Picker
       ↓
       Separation API (/separation/separate)
       ↓
       Display Results
```

---

## 📦 Dependencies (pubspec.yaml)

```yaml
dependencies:
  flutter:                    # Flutter SDK
  http: ^1.2.0               # API calls
  provider: ^6.1.1           # State management
  just_audio: ^0.9.37        # Audio playback
  audio_video_progress_bar: ^2.0.0  # Seek bar
  file_picker: ^6.1.1        # File selection
  shimmer: ^3.0.0            # Loading animations
  flutter_hooks: ^0.20.5     # UI hooks
  universal_platform: ^1.1.0 # Platform detection
```

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `Esc` | Stop |
| `←` | Seek -5s |
| `→` | Seek +5s |
| `R` | Refresh tracks |
| `U` | Toggle upload |

---

## 🧪 Testing Checklist

### Before Running
- [ ] Flutter SDK installed
- [ ] Flutter web enabled (`flutter config --enable-web`)
- [ ] FastAPI backend running on port 8000
- [ ] Browser (Chrome) available

### After Running
- [ ] App loads in browser
- [ ] API status shows "已连接" (green)
- [ ] Track list displays (6 tracks)
- [ ] Search/filter works
- [ ] Clicking track opens player
- [ ] Play/Pause controls work
- [ ] Waveform visualizes
- [ ] Volume slider adjusts
- [ ] Speed slider adjusts
- [ ] Loop toggle works
- [ ] Navigate back to home
- [ ] Click "上传 & 分离" opens screen
- [ ] Click "📊分析" on track opens analysis

---

## 🚀 Deployment

### Development
```bash
flutter run -d chrome
```

### Production Build
```bash
flutter build web --release
# Output: build/web/ (deploy to hosting)
```

### Deploy Options
- **GitHub Pages**: Push `build/web/` to `gh-pages` branch
- **Netlify**: Drag & drop `build/web/` folder
- **Vercel**: Connect GitHub repo with `web/` directory
- **Firebase**: `firebase deploy --only hosting`

---

## 📝 Notes

1. **Flutter Required**: This is a Flutter web app, requiring Flutter SDK
2. **Backend Required**: FastAPI backend must be running
3. **CORS**: Already configured in backend
4. **AudioContext**: Browser requires user interaction to start audio
5. **Mobile Support**: Layout adapts to mobile screens

---

## 🎉 Quick Reference

### Run App
```bash
flutter pub get && flutter run -d chrome
```

### Build App
```bash
flutter build web --release
```

### Fix Issues
```bash
flutter clean
flutter pub get
flutter doctor
```

---

**Last Updated**: 2026-01-15
**Version**: 1.0.0
**Status**: Ready for Flutter installation
