import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:drum_trainer_web/models/track_model.dart';
import 'package:drum_trainer_web/models/api_models.dart';

/// Service for communicating with the FastAPI backend
class ApiService {
  static const String baseUrl = 'http://localhost:8000';

  /// Check if API is available
  Future<bool> checkHealth() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/health'))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }

  /// Fetch list of all available tracks
  Future<TrackListResponse> getTracks() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/tracks/list'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return TrackListResponse.fromJson(data);
      } else {
        throw Exception('Failed to load tracks: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Get audio stream URL for a specific track
  String getAudioUrl(String filename) {
    return '$baseUrl/tracks/audio/${Uri.encodeComponent(filename)}';
  }

  /// Get detailed information about an audio file
  Future<AudioInfo> getAudioInfo(String filename) async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/tracks/info/${Uri.encodeComponent(filename)}'))
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return AudioInfo.fromJson(data);
      } else {
        throw Exception('Failed to get audio info: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Upload and separate audio file
  Future<SeparationResponse> separateAudio(File file) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/separation/separate'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('file', file.path),
      );

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final data = json.decode(responseBody);
        return SeparationResponse.fromJson(data);
      } else {
        throw Exception('Separation failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Analyze music file for BPM, style, mood, etc.
  Future<AnalysisResponse> analyzeAudio(File file) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/analysis/analyze'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('file', file.path),
      );

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final data = json.decode(responseBody);
        return AnalysisResponse.fromJson(data);
      } else {
        throw Exception('Analysis failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Generate drums for a given audio file
  Future<GenerationResponse> generateDrums(
    File file, {
    String? styleHint,
    double? complexity,
  }) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/generation/generate'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('file', file.path),
      );

      if (styleHint != null) {
        request.fields['style_hint'] = styleHint;
      }
      if (complexity != null) {
        request.fields['complexity'] = complexity.toString();
      }

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final data = json.decode(responseBody);
        return GenerationResponse.fromJson(data);
      } else {
        throw Exception('Generation failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Complete processing: separate, analyze, and generate
  Future<CompleteProcessResponse> completeProcess(File file) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/generation/process'),
      );

      request.files.add(
        await http.MultipartFile.fromPath('file', file.path),
      );

      final response = await request.send();
      final responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final data = json.decode(responseBody);
        return CompleteProcessResponse.fromJson(data);
      } else {
        throw Exception('Complete processing failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
}
