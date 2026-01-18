import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:just_audio/just_audio.dart';
import 'package:drum_trainer_web/models/track_model.dart';

/// Service for managing audio playback state and controls
class AudioService extends ChangeNotifier {
  final AudioPlayer _player = AudioPlayer();
  final AudioPlayer _drumPlayer = AudioPlayer();
  final AudioPlayer _backingPlayer = AudioPlayer();

  // Playback state
  Track? _currentTrack;
  bool _isPlaying = false;
  bool _isLooping = false;
  double _volume = 0.8;
  double _playbackSpeed = 1.0;
  Duration _position = Duration.zero;
  Duration _duration = Duration.zero;

  // Multi-track mixing state
  final List<SelectedTrack> _selectedTracks = [];
  bool _isMixing = false;

  // Stream subscriptions
  StreamSubscription<ProcessingState>? _processingStateSubscription;
  StreamSubscription<Duration>? _positionSubscription;
  StreamSubscription<Duration?>? _durationSubscription;

  Track? get currentTrack => _currentTrack;
  bool get isPlaying => _isPlaying;
  bool get isLooping => _isLooping;
  double get volume => _volume;
  double get playbackSpeed => _playbackSpeed;
  Duration get position => _position;
  Duration get duration => _duration;
  List<SelectedTrack> get selectedTracks => List.from(_selectedTracks);
  bool get isMixing => _isMixing;

  AudioService() {
    _initAudioPlayer();
  }

  void _initAudioPlayer() {
    // Set up stream listeners for the main player
    _processingStateSubscription = _player.processingStateStream.listen((state) {
      if (state == ProcessingState.completed) {
        if (_isLooping) {
          _player.seek(Duration.zero);
          _player.play();
        } else {
          _isPlaying = false;
          notifyListeners();
        }
      }
    });

    _positionSubscription = _player.positionStream.listen((position) {
      _position = position;
      notifyListeners();
    });

    _durationSubscription = _player.durationStream.listen((duration) {
      if (duration != null) {
        _duration = duration;
        notifyListeners();
      }
    });
  }

  /// Load and play a single track
  Future<bool> loadTrack(Track track, String audioUrl) async {
    try {
      _currentTrack = track;
      _isPlaying = false;
      _position = Duration.zero;
      _duration = Duration.zero;

      await _player.setUrl(audioUrl);
      await _player.setSpeed(_playbackSpeed);
      await _player.setVolume(_volume);

      notifyListeners();
      return true;
    } catch (e) {
      if (kDebugMode) {
        print('Error loading track: $e');
      }
      return false;
    }
  }

  /// Play current track
  Future<void> play() async {
    if (_currentTrack == null) return;
    await _player.play();
    _isPlaying = true;
    notifyListeners();
  }

  /// Pause current track
  Future<void> pause() async {
    await _player.pause();
    _isPlaying = false;
    notifyListeners();
  }

  /// Stop current track
  Future<void> stop() async {
    await _player.stop();
    await _player.seek(Duration.zero);
    _isPlaying = false;
    _position = Duration.zero;
    notifyListeners();
  }

  /// Seek to position
  Future<void> seek(Duration position) async {
    await _player.seek(position);
    _position = position;
    notifyListeners();
  }

  /// Set volume (0.0 to 1.0)
  Future<void> setVolume(double value) async {
    _volume = value.clamp(0.0, 1.0);
    await _player.setVolume(_volume);
    notifyListeners();
  }

  /// Set playback speed (0.5 to 2.0)
  Future<void> setPlaybackSpeed(double speed) async {
    _playbackSpeed = speed.clamp(0.5, 2.0);
    await _player.setSpeed(_playbackSpeed);
    notifyListeners();
  }

  /// Toggle loop mode
  Future<void> toggleLoop() async {
    _isLooping = !_isLooping;
    await _player.setLoopMode(_isLooping ? LoopMode.one : LoopMode.off);
    notifyListeners();
  }

  /// Get progress as percentage (0.0 to 1.0)
  double get progress {
    if (_duration.inSeconds == 0) return 0.0;
    return _position.inSeconds / _duration.inSeconds;
  }

  /// Get formatted position string (MM:SS)
  String get formattedPosition {
    final minutes = _position.inMinutes;
    final seconds = _position.inSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Get formatted duration string (MM:SS)
  String get formattedDuration {
    final minutes = _duration.inMinutes;
    final seconds = _duration.inSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  // Multi-track mixing methods

  /// Add track to mix selection
  void addTrackToMix(Track track, String audioUrl, {double volume = 1.0}) {
    final existingIndex = _selectedTracks.indexWhere((t) => t.track.name == track.name);
    if (existingIndex == -1) {
      _selectedTracks.add(SelectedTrack(
        track: track,
        audioUrl: audioUrl,
        volume: volume,
      ));
      notifyListeners();
    }
  }

  /// Remove track from mix selection
  void removeFromMix(Track track) {
    _selectedTracks.removeWhere((t) => t.track.name == track.name);
    notifyListeners();
  }

  /// Update track volume in mix
  void updateMixTrackVolume(String trackName, double volume) {
    final index = _selectedTracks.indexWhere((t) => t.track.name == trackName);
    if (index != -1) {
      _selectedTracks[index] = _selectedTracks[index].copyWith(
        volume: volume.clamp(0.0, 1.0),
      );
      if (_isMixing) {
        // Update live player volume if mixing is active
        if (trackName == _selectedTracks.firstOrNull?.track.name) {
          _drumPlayer.setVolume(volume);
        } else if (trackName == _selectedTracks.lastOrNull?.track.name) {
          _backingPlayer.setVolume(volume);
        }
      }
      notifyListeners();
    }
  }

  /// Toggle mix selection for a track
  void toggleMixSelection(Track track, String audioUrl) {
    final index = _selectedTracks.indexWhere((t) => t.track.name == track.name);
    if (index != -1) {
      removeFromMix(track);
    } else {
      addTrackToMix(track, audioUrl);
    }
  }

  /// Check if track is in mix selection
  bool isInMixSelection(Track track) {
    return _selectedTracks.any((t) => t.track.name == track.name);
  }

  /// Get selected tracks count
  int get selectedTrackCount => _selectedTracks.length;

  /// Start mixing multiple tracks
  Future<bool> startMix() async {
    if (_selectedTracks.isEmpty) return false;

    try {
      _isPlaying = true;
      _isMixing = true;

      // Stop single track player
      await _player.stop();

      if (_selectedTracks.length == 1) {
        // Only one track, use main player
        final track = _selectedTracks.first;
        await _player.setUrl(track.audioUrl);
        await _player.setVolume(track.volume);
        await _player.play();
      } else if (_selectedTracks.length >= 2) {
        // Multiple tracks, use drum and backing players
        final drumTrack = _selectedTracks.first;
        final backingTrack = _selectedTracks.last;

        await _drumPlayer.setUrl(drumTrack.audioUrl);
        await _drumPlayer.setVolume(drumTrack.volume);

        await _backingPlayer.setUrl(backingTrack.audioUrl);
        await _backingPlayer.setVolume(backingTrack.volume);

        // Play simultaneously
        await Future.wait([
          _drumPlayer.play(),
          _backingPlayer.play(),
        ]);
      }

      notifyListeners();
      return true;
    } catch (e) {
      if (kDebugMode) {
        print('Error starting mix: $e');
      }
      _isPlaying = false;
      _isMixing = false;
      notifyListeners();
      return false;
    }
  }

  /// Stop mixing
  Future<void> stopMix() async {
    await _drumPlayer.stop();
    await _backingPlayer.stop();
    await _drumPlayer.seek(Duration.zero);
    await _backingPlayer.seek(Duration.zero);
    _isPlaying = false;
    _isMixing = false;
    notifyListeners();
  }

  /// Get mix progress
  double get mixProgress {
    if (_isMixing) {
      final maxDuration = _drumPlayer.duration ?? Duration.zero;
      if (maxDuration.inSeconds == 0) return 0.0;
      final position = _drumPlayer.position;
      return position.inSeconds / maxDuration.inSeconds;
    }
    return progress;
  }

  /// Get formatted mix position
  String get formattedMixPosition {
    if (_isMixing) {
      final position = _drumPlayer.position;
      final minutes = position.inMinutes;
      final seconds = position.inSeconds % 60;
      return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
    return formattedPosition;
  }

  /// Get formatted mix duration
  String get formattedMixDuration {
    if (_isMixing) {
      final duration = _drumPlayer.duration ?? Duration.zero;
      final minutes = duration.inMinutes;
      final seconds = duration.inSeconds % 60;
      return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
    return formattedDuration;
  }

  /// Seek in mix mode
  Future<void> seekMix(Duration position) async {
    if (_isMixing) {
      await Future.wait([
        _drumPlayer.seek(position),
        _backingPlayer.seek(position),
      ]);
      notifyListeners();
    } else {
      await seek(position);
    }
  }

  /// Clean up resources
  @override
  void dispose() {
    _processingStateSubscription?.cancel();
    _positionSubscription?.cancel();
    _durationSubscription?.cancel();
    _player.dispose();
    _drumPlayer.dispose();
    _backingPlayer.dispose();
    super.dispose();
  }
}

/// Model for selected track in mixing mode
class SelectedTrack {
  final Track track;
  final String audioUrl;
  final double volume;
  final bool isMuted;

  SelectedTrack({
    required this.track,
    required this.audioUrl,
    this.volume = 1.0,
    this.isMuted = false,
  });

  SelectedTrack copyWith({
    Track? track,
    String? audioUrl,
    double? volume,
    bool? isMuted,
  }) {
    return SelectedTrack(
      track: track ?? this.track,
      audioUrl: audioUrl ?? this.audioUrl,
      volume: volume ?? this.volume,
      isMuted: isMuted ?? this.isMuted,
    );
  }
}
