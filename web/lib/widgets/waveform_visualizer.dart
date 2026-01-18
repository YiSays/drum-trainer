import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:drum_trainer_web/services/audio_service.dart';

class WaveformVisualizer extends StatefulWidget {
  const WaveformVisualizer({super.key});

  @override
  State<WaveformVisualizer> createState() => _WaveformVisualizerState();
}

class _WaveformVisualizerState extends State<WaveformVisualizer>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  List<double> _waveformPoints = [];
  final Random _random = Random();

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
    )..addListener(_updateWaveform);

    // Generate initial waveform points
    _generateWaveformPoints();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _generateWaveformPoints() {
    _waveformPoints = List.generate(64, (index) {
      return _random.nextDouble() * 0.5 + 0.1;
    });
  }

  void _updateWaveform() {
    if (!mounted) return;
    setState(() {
      // Simulate waveform animation by slightly varying points
      _waveformPoints = _waveformPoints.map((point) {
        double newValue = point + (_random.nextDouble() - 0.5) * 0.1;
        return newValue.clamp(0.05, 1.0);
      }).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    final audioService = context.watch<AudioService>();

    // Start/stop animation based on playback state
    if (audioService.isPlaying && !_controller.isAnimating) {
      _controller.repeat();
    } else if (!audioService.isPlaying && _controller.isAnimating) {
      _controller.stop();
    }

    return Container(
      margin: const EdgeInsets.all(16),
      height: 160,
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A24),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Stack(
        children: [
          // Background grid lines
          Positioned.fill(
            child: CustomPaint(
              painter: _GridPainter(),
            ),
          ),

          // Waveform visualization
          Positioned.fill(
            child: CustomPaint(
              painter: _WaveformPainter(
                points: _waveformPoints,
                isPlaying: audioService.isPlaying,
                progress: audioService.progress,
              ),
            ),
          ),

          // Playhead indicator
          Positioned(
            left: 16,
            bottom: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: audioService.isPlaying
                    ? const Color(0xFF8B5CF6).withOpacity(0.3)
                    : const Color(0xFF334155),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    audioService.isPlaying ? Icons.podcasts : Icons.pause_circle_outline,
                    size: 14,
                    color: audioService.isPlaying
                        ? const Color(0xFF8B5CF6)
                        : const Color(0xFF94A3B8),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    audioService.isPlaying ? '实时频谱' : '暂停',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: audioService.isPlaying
                          ? const Color(0xFF8B5CF6)
                          : const Color(0xFF94A3B8),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Empty state
          if (!audioService.isPlaying && audioService.currentTrack == null)
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.waves,
                    size: 48,
                    color: const Color(0xFF64748B).withOpacity(0.5),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '选择音轨开始播放',
                    style: TextStyle(
                      color: const Color(0xFF64748B).withOpacity(0.8),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0xFF334155).withOpacity(0.5)
      ..strokeWidth = 1;

    // Draw horizontal grid lines
    for (int i = 0; i <= 4; i++) {
      final y = (size.height / 4) * i;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }

    // Draw vertical grid lines
    for (int i = 0; i <= 10; i++) {
      final x = (size.width / 10) * i;
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _WaveformPainter extends CustomPainter {
  final List<double> points;
  final bool isPlaying;
  final double progress;

  _WaveformPainter({
    required this.points,
    required this.isPlaying,
    required this.progress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;

    final barWidth = size.width / points.length;
    final centerY = size.height / 2;
    final maxHeight = size.height * 0.4;

    for (int i = 0; i < points.length; i++) {
      final x = i * barWidth + barWidth / 2;
      final barHeight = points[i] * maxHeight;
      final isPlayed = (i / points.length) <= progress;

      final color = isPlayed
          ? const Color(0xFF8B5CF6)
          : const Color(0xFF4B5563);

      final paint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;

      // Draw bar
      final rect = Rect.fromCenter(
        center: Offset(x, centerY),
        width: barWidth * 0.8,
        height: barHeight * 2,
      );

      // Rounded corners
      final rrect = RRect.fromRectAndRadius(rect, const Radius.circular(2));
      canvas.drawRRect(rrect, paint);

      // Add glow for played bars
      if (isPlayed && isPlaying) {
        final glowPaint = Paint()
          ..color = const Color(0xFF8B5CF6).withOpacity(0.3)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

        canvas.drawRRect(rrect, glowPaint);
      }
    }

    // Draw playhead line
    final playheadX = progress * size.width;
    final playheadPaint = Paint()
      ..color = const Color(0xFFFBBF24)
      ..strokeWidth = 2;

    canvas.drawLine(
      Offset(playheadX, 0),
      Offset(playheadX, size.height),
      playheadPaint,
    );

    // Playhead glow
    if (isPlaying) {
      final glowPaint = Paint()
        ..color = const Color(0xFFFBBF24).withOpacity(0.3)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6);

      canvas.drawLine(
        Offset(playheadX, 0),
        Offset(playheadX, size.height),
        glowPaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _WaveformPainter oldDelegate) {
    return oldDelegate.points != points ||
        oldDelegate.isPlaying != isPlaying ||
        oldDelegate.progress != progress;
  }
}
