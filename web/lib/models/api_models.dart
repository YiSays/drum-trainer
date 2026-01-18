/// Audio information response model
class AudioInfo {
  final String filename;
  final double duration;
  final int sampleRate;
  final int channels;
  final int frames;
  final double? bpm;
  final String? key;
  final String? style;
  final String? mood;
  final double? energy;

  AudioInfo({
    required this.filename,
    required this.duration,
    required this.sampleRate,
    required this.channels,
    required this.frames,
    this.bpm,
    this.key,
    this.style,
    this.mood,
    this.energy,
  });

  factory AudioInfo.fromJson(Map<String, dynamic> json) {
    return AudioInfo(
      filename: json['filename'] ?? '',
      duration: (json['duration'] as num).toDouble(),
      sampleRate: json['samplerate'],
      channels: json['channels'],
      frames: json['frames'],
      bpm: (json['bpm'] as num?)?.toDouble(),
      key: json['key'],
      style: json['style'],
      mood: json['mood'],
      energy: (json['energy'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'filename': filename,
      'duration': duration,
      'samplerate': sampleRate,
      'channels': channels,
      'frames': frames,
      'bpm': bpm,
      'key': key,
      'style': style,
      'mood': mood,
      'energy': energy,
    };
  }

  /// Get formatted duration (MM:SS)
  String get formattedDuration {
    final minutes = duration.floor() ~/ 60;
    final seconds = (duration % 60).floor();
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Get energy as percentage
  String get energyPercent {
    if (energy == null) return 'N/A';
    return '${(energy! * 100).toStringAsFixed(0)}%';
  }
}

/// Separation response model
class SeparationResponse {
  final String status;
  final String message;
  final SeparationResult? result;

  SeparationResponse({
    required this.status,
    required this.message,
    this.result,
  });

  factory SeparationResponse.fromJson(Map<String, dynamic> json) {
    return SeparationResponse(
      status: json['status'],
      message: json['message'],
      result: json['result'] != null
          ? SeparationResult.fromJson(json['result'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'message': message,
      'result': result?.toJson(),
    };
  }

  bool get isSuccess => status == 'success';
}

/// Separation result details
class SeparationResult {
  final String drum;
  final String noDrums;
  final String mixed;

  SeparationResult({
    required this.drum,
    required this.noDrums,
    required this.mixed,
  });

  factory SeparationResult.fromJson(Map<String, dynamic> json) {
    return SeparationResult(
      drum: json['drum'] ?? '',
      noDrums: json['no_drums'] ?? '',
      mixed: json['mixed'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'drum': drum,
      'no_drums': noDrums,
      'mixed': mixed,
    };
  }
}

/// Analysis response model
class AnalysisResponse {
  final String status;
  final String message;
  final AnalysisResult? analysis;

  AnalysisResponse({
    required this.status,
    required this.message,
    this.analysis,
  });

  factory AnalysisResponse.fromJson(Map<String, dynamic> json) {
    return AnalysisResponse(
      status: json['status'],
      message: json['message'],
      analysis: json['analysis'] != null
          ? AnalysisResult.fromJson(json['analysis'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'message': message,
      'analysis': analysis?.toJson(),
    };
  }

  bool get isSuccess => status == 'success';
}

/// Analysis result details
class AnalysisResult {
  final double bpm;
  final String style;
  final String mood;
  final double energy;
  final String key;
  final MusicStructure? structure;
  final RhythmProfile? rhythmProfile;

  AnalysisResult({
    required this.bpm,
    required this.style,
    required this.mood,
    required this.energy,
    required this.key,
    this.structure,
    this.rhythmProfile,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      bpm: (json['bpm'] as num).toDouble(),
      style: json['style'],
      mood: json['mood'],
      energy: (json['energy'] as num).toDouble(),
      key: json['key'],
      structure: json['structure'] != null
          ? MusicStructure.fromJson(json['structure'])
          : null,
      rhythmProfile: json['rhythm_profile'] != null
          ? RhythmProfile.fromJson(json['rhythm_profile'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'bpm': bpm,
      'style': style,
      'mood': mood,
      'energy': energy,
      'key': key,
      'structure': structure?.toJson(),
      'rhythm_profile': rhythmProfile?.toJson(),
    };
  }

  /// Get BPM as integer
  int get bpmInt => bpm.round();

  /// Get energy as percentage
  String get energyPercent => '${(energy * 100).toStringAsFixed(0)}%';
}

/// Music structure details
class MusicStructure {
  final int totalSections;
  final Map<String, int> types;
  final List<Section> sections;

  MusicStructure({
    required this.totalSections,
    required this.types,
    required this.sections,
  });

  factory MusicStructure.fromJson(Map<String, dynamic> json) {
    return MusicStructure(
      totalSections: json['total_sections'],
      types: Map<String, int>.from(json['types']),
      sections: (json['sections'] as List)
          .map((s) => Section.fromJson(s))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_sections': totalSections,
      'types': types,
      'sections': sections.map((s) => s.toJson()).toList(),
    };
  }
}

/// Music section (intro, verse, chorus, etc.)
class Section {
  final String type;
  final double start;
  final double end;
  final double duration;

  Section({
    required this.type,
    required this.start,
    required this.end,
    required this.duration,
  });

  factory Section.fromJson(Map<String, dynamic> json) {
    return Section(
      type: json['type'],
      start: (json['start'] as num).toDouble(),
      end: (json['end'] as num).toDouble(),
      duration: (json['duration'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type,
      'start': start,
      'end': end,
      'duration': duration,
    };
  }
}

/// Rhythm profile details
class RhythmProfile {
  final String mainPattern;
  final double complexity;
  final String recommendedPractice;

  RhythmProfile({
    required this.mainPattern,
    required this.complexity,
    required this.recommendedPractice,
  });

  factory RhythmProfile.fromJson(Map<String, dynamic> json) {
    return RhythmProfile(
      mainPattern: json['main_pattern'],
      complexity: (json['complexity'] as num).toDouble(),
      recommendedPractice: json['recommended_practice'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'main_pattern': mainPattern,
      'complexity': complexity,
      'recommended_practice': recommendedPractice,
    };
  }

  /// Get complexity as percentage
  String get complexityPercent => '${(complexity * 100).toStringAsFixed(0)}%';
}

/// Generation response model
class GenerationResponse {
  final String status;
  final String message;
  final GenerationResult? result;

  GenerationResponse({
    required this.status,
    required this.message,
    this.result,
  });

  factory GenerationResponse.fromJson(Map<String, dynamic> json) {
    return GenerationResponse(
      status: json['status'],
      message: json['message'],
      result: json['result'] != null
          ? GenerationResult.fromJson(json['result'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'message': message,
      'result': result?.toJson(),
    };
  }

  bool get isSuccess => status == 'success';
}

/// Generation result details
class GenerationResult {
  final String pattern;
  final double bpm;
  final String? filePath;

  GenerationResult({
    required this.pattern,
    required this.bpm,
    this.filePath,
  });

  factory GenerationResult.fromJson(Map<String, dynamic> json) {
    return GenerationResult(
      pattern: json['pattern'],
      bpm: (json['bpm'] as num).toDouble(),
      filePath: json['file_path'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'pattern': pattern,
      'bpm': bpm,
      'file_path': filePath,
    };
  }
}

/// Complete process response model
class CompleteProcessResponse {
  final String status;
  final String message;
  final AnalysisResult? analysis;
  final GenerationResult? generated;
  final SeparationResult? files;
  final double? processingTime;

  CompleteProcessResponse({
    required this.status,
    required this.message,
    this.analysis,
    this.generated,
    this.files,
    this.processingTime,
  });

  factory CompleteProcessResponse.fromJson(Map<String, dynamic> json) {
    return CompleteProcessResponse(
      status: json['status'],
      message: json['message'],
      analysis: json['analysis'] != null
          ? AnalysisResult.fromJson(json['analysis'])
          : null,
      generated: json['generated'] != null
          ? GenerationResult.fromJson(json['generated'])
          : null,
      files: json['files'] != null
          ? SeparationResult.fromJson(json['files'])
          : null,
      processingTime: (json['processing_time'] as num?)?.toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'message': message,
      'analysis': analysis?.toJson(),
      'generated': generated?.toJson(),
      'files': files?.toJson(),
      'processing_time': processingTime,
    };
  }

  bool get isSuccess => status == 'success';

  /// Get processing time as formatted string
  String get formattedProcessingTime {
    if (processingTime == null) return 'N/A';
    return '${processingTime!.toStringAsFixed(1)}s';
  }
}

/// Base API response model
class ApiResponse<T> {
  final String status;
  final String message;
  final T? data;

  ApiResponse({
    required this.status,
    required this.message,
    this.data,
  });

  bool get isSuccess => status == 'success';
}
