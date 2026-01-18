import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:audio_video_progress_bar/audio_video_progress_bar.dart';
import 'package:drum_trainer_web/services/api_service.dart';
import 'package:drum_trainer_web/services/audio_service.dart';
import 'package:drum_trainer_web/models/track_model.dart';
import 'package:drum_trainer_web/widgets/waveform_visualizer.dart';

class TrackPlayerScreen extends StatefulWidget {
  final Track track;
  final String audioUrl;

  const TrackPlayerScreen({
    super.key,
    required this.track,
    required this.audioUrl,
  });

  @override
  State<TrackPlayerScreen> createState() => _TrackPlayerScreenState();
}

class _TrackPlayerScreenState extends State<TrackPlayerScreen> {
  bool _isLoading = true;
  bool _hasError = false;
  String? _errorMessage;
  Timer? _progressTimer;

  @override
  void initState() {
    super.initState();
    _loadTrack();
  }

  @override
  void dispose() {
    _progressTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadTrack() async {
    final audioService = context.read<AudioService>();
    final success = await audioService.loadTrack(widget.track, widget.audioUrl);

    setState(() {
      _isLoading = false;
      _hasError = !success;
      _errorMessage = success ? null : '无法加载音频文件';
    });
  }

  Future<void> _playPause() async {
    final audioService = context.read<AudioService>();
    if (audioService.isPlaying) {
      await audioService.pause();
    } else {
      await audioService.play();
    }
  }

  Future<void> _stop() async {
    final audioService = context.read<AudioService>();
    await audioService.stop();
  }

  Future<void> _seek(Duration position) async {
    final audioService = context.read<AudioService>();
    await audioService.seek(position);
  }

  Future<void> _setVolume(double value) async {
    final audioService = context.read<AudioService>();
    await audioService.setVolume(value);
  }

  Future<void> _setPlaybackSpeed(double value) async {
    final audioService = context.read<AudioService>();
    await audioService.setPlaybackSpeed(value);
  }

  Future<void> _toggleLoop() async {
    final audioService = context.read<AudioService>();
    await audioService.toggleLoop();
  }

  @override
  Widget build(BuildContext context) {
    final audioService = context.watch<AudioService>();

    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0F),
      appBar: AppBar(
        title: Text(
          widget.track.name,
          overflow: TextOverflow.ellipsis,
        ),
        backgroundColor: const Color(0xFF12121A),
        elevation: 1,
      ),
      body: Column(
        children: [
          // Now Playing Header
          _buildNowPlayingHeader(),

          // Waveform Visualization
          const WaveformVisualizer(),

          // Player Controls
          Expanded(
            child: _buildPlayerControls(audioService),
          ),
        ],
      ),
    );
  }

  Widget _buildNowPlayingHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF1A1A24),
            Color(0xFF0A0A0F),
          ],
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: const Color(0xFF8B5CF6).withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: const Color(0xFF8B5CF6).withOpacity(0.4),
              ),
            ),
            alignment: Alignment.center,
            child: Text(
              widget.track.icon,
              style: const TextStyle(fontSize: 32),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.track.name,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFFF8FAFC),
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 6),
                Row(
                  children: [
                    _InfoChip(
                      icon: Icons.access_time,
                      label: widget.track.formattedDuration,
                    ),
                    const SizedBox(width: 8),
                    _InfoChip(
                      icon: Icons.folder_file,
                      label: '${widget.track.sizeInMB} MB',
                    ),
                    const SizedBox(width: 8),
                    _InfoChip(
                      icon: Icons.spatial_audio_off,
                      label: widget.track.channelDescription,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlayerControls(AudioService audioService) {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF8B5CF6)),
            ),
            SizedBox(height: 16),
            Text(
              '初始化音频...',
              style: TextStyle(color: Color(0xFF94A3B8)),
            ),
          ],
        ),
      );
    }

    if (_hasError) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 48,
              color: Color(0xFFEF4444),
            ),
            const SizedBox(height: 16),
            Text(
              _errorMessage ?? '加载失败',
              style: const TextStyle(
                color: Color(0xFFCBD5E1),
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _loadTrack,
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Main Controls
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1A1A24).withOpacity(0.5),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Column(
              children: [
                // Play/Pause/Stop Buttons
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Stop Button
                    ElevatedButton.icon(
                      onPressed: _stop,
                      icon: const Icon(Icons.stop, size: 20),
                      label: const Text('停止'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFEF4444).withOpacity(0.2),
                        foregroundColor: const Color(0xFFEF4444),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 14,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: const BorderSide(
                            color: Color(0xFFEF4444),
                            width: 1,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),

                    // Play/Pause Button
                    ElevatedButton.icon(
                      onPressed: _playPause,
                      icon: Icon(
                        audioService.isPlaying ? Icons.pause : Icons.play_arrow,
                        size: 28,
                      ),
                      label: Text(
                        audioService.isPlaying ? '暂停' : '播放',
                        style: const TextStyle(fontSize: 16),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF8B5CF6),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 32,
                          vertical: 16,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 4,
                      ),
                    ),
                    const SizedBox(width: 16),

                    // Loop Button
                    ElevatedButton.icon(
                      onPressed: _toggleLoop,
                      icon: Icon(
                        Icons.loop,
                        size: 20,
                        color: audioService.isLooping
                            ? const Color(0xFF8B5CF6)
                            : const Color(0xFF94A3B8),
                      ),
                      label: Text(
                        '循环',
                        style: TextStyle(
                          color: audioService.isLooping
                              ? const Color(0xFF8B5CF6)
                              : const Color(0xFF94A3B8),
                        ),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: audioService.isLooping
                            ? const Color(0xFF8B5CF6).withOpacity(0.2)
                            : const Color(0xFF1A1A24),
                        foregroundColor: const Color(0xFF94A3B8),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 20,
                          vertical: 14,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: BorderSide(
                            color: audioService.isLooping
                                ? const Color(0xFF8B5CF6)
                                : const Color(0xFF334155),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                // Progress Bar
                ProgressBar(
                  progress: audioService.position,
                  total: audioService.duration,
                  onSeek: _seek,
                  barHeight: 8,
                  thumbRadius: 10,
                  thumbGlowRadius: 15,
                  progressBarColor: const Color(0xFF8B5CF6),
                  baseBarColor: const Color(0xFF334155),
                  thumbColor: const Color(0xFF8B5CF6),
                  timeLabelLocation: TimeLabelLocation.sides,
                  timeLabelType: TimeLabelType.totalTime,
                  timeLabelTextStyle: const TextStyle(
                    color: Color(0xFF94A3B8),
                    fontSize: 12,
                  ),
                ),

                const SizedBox(height: 16),

                // Time Display
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      audioService.formattedPosition,
                      style: const TextStyle(
                        color: Color(0xFFF8FAFC),
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        fontFamily: 'monospace',
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Text(
                      '/',
                      style: TextStyle(
                        color: Color(0xFF64748B),
                        fontSize: 16,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      audioService.formattedDuration,
                      style: const TextStyle(
                        color: Color(0xFF94A3B8),
                        fontSize: 16,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          // Secondary Controls
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1A1A24).withOpacity(0.5),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF334155)),
            ),
            child: Column(
              children: [
                // Volume Control
                _SliderControl(
                  label: '音量',
                  value: audioService.volume,
                  min: 0.0,
                  max: 1.0,
                  onChanged: _setVolume,
                  valueDisplay: '${(audioService.volume * 100).toStringAsFixed(0)}%',
                  icon: Icons.volume_up,
                ),

                const SizedBox(height: 16),

                // Speed Control
                _SliderControl(
                  label: '速度',
                  value: audioService.playbackSpeed,
                  min: 0.5,
                  max: 2.0,
                  onChanged: _setPlaybackSpeed,
                  valueDisplay: '${audioService.playbackSpeed.toStringAsFixed(1)}x',
                  icon: Icons.speed,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final IconData icon;
  final String label;

  const _InfoChip({
    required this.icon,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A24),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: const Color(0xFF94A3B8),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF94A3B8),
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _SliderControl extends StatelessWidget {
  final String label;
  final double value;
  final double min;
  final double max;
  final ValueChanged<double> onChanged;
  final String valueDisplay;
  final IconData icon;

  const _SliderControl({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.onChanged,
    required this.valueDisplay,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 18, color: const Color(0xFF94A3B8)),
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Color(0xFFCBD5E1),
              ),
            ),
            const Spacer(),
            Text(
              valueDisplay,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Color(0xFF8B5CF6),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Slider(
          value: value,
          min: min,
          max: max,
          onChanged: onChanged,
          activeColor: const Color(0xFF8B5CF6),
          inactiveColor: const Color(0xFF334155),
          thumbColor: const Color(0xFF8B5CF6),
        ),
      ],
    );
  }
}
