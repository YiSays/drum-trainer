import 'package:flutter/material.dart';
import 'package:drum_trainer_web/models/track_model.dart';

class TrackCard extends StatelessWidget {
  final Track track;
  final VoidCallback onPlay;
  final VoidCallback onAnalyze;

  const TrackCard({
    super.key,
    required this.track,
    required this.onPlay,
    required this.onAnalyze,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onPlay,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Track Icon
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: const Color(0xFF8B5CF6).withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: const Color(0xFF8B5CF6).withOpacity(0.4),
                  ),
                ),
                alignment: Alignment.center,
                child: Text(
                  track.icon,
                  style: const TextStyle(fontSize: 28),
                ),
              ),
              const SizedBox(width: 16),

              // Track Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      track.name,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFFF8FAFC),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        _MetadataBadge(
                          icon: Icons.access_time,
                          text: track.formattedDuration,
                        ),
                        const SizedBox(width: 8),
                        _MetadataBadge(
                          icon: Icons.folder_file,
                          text: '${track.sizeInMB} MB',
                        ),
                        const SizedBox(width: 8),
                        _MetadataBadge(
                          icon: Icons.spatial_audio_off,
                          text: track.channelDescription,
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // Action Buttons
              Row(
                children: [
                  // Analyze Button
                  IconButton(
                    onPressed: onAnalyze,
                    icon: const Icon(Icons.analytics, size: 20),
                    color: const Color(0xFF94A3B8),
                    tooltip: '分析',
                  ),
                  const SizedBox(width: 8),

                  // Play Button
                  ElevatedButton.icon(
                    onPressed: onPlay,
                    icon: const Icon(Icons.play_arrow, size: 18),
                    label: const Text('播放'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF8B5CF6),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 10,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetadataBadge extends StatelessWidget {
  final IconData icon;
  final String text;

  const _MetadataBadge({
    required this.icon,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A24),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 12,
            color: const Color(0xFF94A3B8),
          ),
          const SizedBox(width: 4),
          Text(
            text,
            style: const TextStyle(
              fontSize: 11,
              color: Color(0xFF94A3B8),
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
