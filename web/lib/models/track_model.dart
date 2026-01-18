/// Model representing a single audio track
class Track {
  final String name;
  final String? path;
  final int? size;
  final double? duration;
  final int? sampleRate;
  final int? channels;

  Track({
    required this.name,
    this.path,
    this.size,
    this.duration,
    this.sampleRate,
    this.channels,
  });

  factory Track.fromJson(Map<String, dynamic> json) {
    return Track(
      name: json['name'] ?? '',
      path: json['path'],
      size: json['size'],
      duration: (json['duration'] as num?)?.toDouble(),
      sampleRate: json['samplerate'],
      channels: json['channels'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'path': path,
      'size': size,
      'duration': duration,
      'samplerate': sampleRate,
      'channels': channels,
    };
  }

  /// Get file size in MB
  String get sizeInMB {
    if (size == null) return 'N/A';
    return (size! / (1024 * 1024)).toStringAsFixed(1);
  }

  /// Get duration as formatted string (MM:SS)
  String get formattedDuration {
    if (duration == null) return 'N/A';
    final minutes = duration!.floor() ~/ 60;
    final seconds = (duration! % 60).floor();
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Get channel description
  String get channelDescription {
    if (channels == null) return 'N/A';
    return channels == 2 ? 'Stereo' : 'Mono';
  }

  /// Get sample rate description
  String get sampleRateDescription {
    if (sampleRate == null) return 'N/A';
    return '${(sampleRate! / 1000).toStringAsFixed(1)} kHz';
  }

  /// Determine icon based on track name
  String get icon {
    final lowerName = name.toLowerCase();
    if (lowerName.contains('drum')) return '🥁';
    if (lowerName.contains('bass')) return '🎸';
    if (lowerName.contains('vocal')) return '🎤';
    if (lowerName.contains('mixed')) return '🎶';
    return '🎵';
  }

  /// Determine track type for filtering
  TrackType get type {
    final lowerName = name.toLowerCase();
    if (lowerName.contains('drum')) return TrackType.drums;
    if (lowerName.contains('bass')) return TrackType.bass;
    if (lowerName.contains('no_drum') || lowerName.contains('backing')) {
      return TrackType.backing;
    }
    return TrackType.other;
  }

  @override
  String toString() {
    return 'Track(name: $name, duration: ${duration?.toStringAsFixed(1)}s, size: ${sizeInMB}MB)';
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Track &&
          runtimeType == other.runtimeType &&
          name == other.name;

  @override
  int get hashCode => name.hashCode;
}

/// Track type enum for filtering
enum TrackType {
  drums,
  bass,
  backing,
  other,
}

/// Response model for track list
class TrackListResponse {
  final List<Track> tracks;

  TrackListResponse({required this.tracks});

  factory TrackListResponse.fromJson(Map<String, dynamic> json) {
    final tracksList = json['tracks'] as List<dynamic>;
    return TrackListResponse(
      tracks: tracksList.map((t) => Track.fromJson(t)).toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'tracks': tracks.map((t) => t.toJson()).toList(),
    };
  }

  /// Get tracks filtered by type
  List<Track> getTracksByType(TrackType type) {
    return tracks.where((t) => t.type == type).toList();
  }

  /// Get all drum tracks
  List<Track> get drumTracks => getTracksByType(TrackType.drums);

  /// Get all bass tracks
  List<Track> get bassTracks => getTracksByType(TrackType.bass);

  /// Get all backing tracks (no drums)
  List<Track> get backingTracks => getTracksByType(TrackType.backing);
}
