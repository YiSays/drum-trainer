import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';
import 'package:drum_trainer_web/services/api_service.dart';
import 'package:drum_trainer_web/models/api_models.dart';

class SeparationScreen extends StatefulWidget {
  const SeparationScreen({super.key});

  @override
  State<SeparationScreen> createState() => _SeparationScreenState();
}

class _SeparationScreenState extends State<SeparationScreen> {
  bool _isProcessing = false;
  double _progress = 0.0;
  String _statusMessage = '';
  String? _fileName;
  SeparationResponse? _result;
  String? _errorMessage;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0F),
      appBar: AppBar(
        title: const Text('上传 & 分离'),
        backgroundColor: const Color(0xFF12121A),
        elevation: 1,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Upload Area
            _buildUploadArea(),

            const SizedBox(height: 24),

            // Progress Section
            if (_isProcessing) _buildProgressSection(),

            // Result Section
            if (_result != null) _buildResultSection(),

            // Error Section
            if (_errorMessage != null) _buildErrorSection(),
          ],
        ),
      ),
    );
  }

  Widget _buildUploadArea() {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Icon(
              Icons.cloud_upload,
              size: 64,
              color: Color(0xFF8B5CF6),
            ),
            const SizedBox(height: 16),
            const Text(
              '选择音频文件',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: Color(0xFFF8FAFC),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              '支持 MP3, WAV, FLAC, OGG (最大 100MB)',
              style: TextStyle(
                fontSize: 14,
                color: Color(0xFF94A3B8),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _isProcessing ? null : _pickAndSeparateFile,
              icon: const Icon(Icons.folder_open, size: 20),
              label: const Text('选择文件'),
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
              ),
            ),
            if (_fileName != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF1A1A24),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.audiotrack, size: 18, color: Color(0xFF94A3B8)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _fileName!,
                        style: const TextStyle(
                          color: Color(0xFFF8FAFC),
                          fontSize: 14,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildProgressSection() {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: const Color(0xFF1A1A24),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  _statusMessage,
                  style: const TextStyle(
                    color: Color(0xFFF8FAFC),
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  '${(_progress * 100).toStringAsFixed(0)}%',
                  style: const TextStyle(
                    color: Color(0xFF8B5CF6),
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: _progress,
              backgroundColor: const Color(0xFF334155),
              valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF8B5CF6)),
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
            ),
            const SizedBox(height: 16),
            const Text(
              '正在使用 Demucs AI 进行鼓声分离...',
              style: TextStyle(
                color: Color(0xFF94A3B8),
                fontSize: 13,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultSection() {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: const Color(0xFF1A1A24),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.check_circle,
                  size: 24,
                  color: Color(0xFF10B981),
                ),
                const SizedBox(width: 10),
                const Text(
                  '分离完成!',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: Color(0xFFF8FAFC),
                  ),
                ),
                const Spacer(),
                IconButton(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  icon: const Icon(Icons.close, size: 20),
                  color: const Color(0xFF94A3B8),
                ),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              '生成的文件:',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: Color(0xFFCBD5E1),
              ),
            ),
            const SizedBox(height: 8),
            _ResultFileRow(
              icon: Icons.music_note,
              label: '鼓声 (Drums Only)',
              path: _result!.result?.drumsOnly,
            ),
            const SizedBox(height: 6),
            _ResultFileRow(
              icon: Icons.music_off,
              label: '无鼓伴奏 (No Drums)',
              path: _result!.result?.noDrums,
            ),
            const SizedBox(height: 6),
            _ResultFileRow(
              icon: Icons.multitrack_audio,
              label: '混合 (Mixed)',
              path: _result!.result?.mixed,
            ),
            const SizedBox(height: 16),
            const Text(
              '提示: 刷新音轨列表查看新生成的文件',
              style: TextStyle(
                fontSize: 12,
                color: Color(0xFF94A3B8),
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorSection() {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: const Color(0xFF1A1A24).withOpacity(0.8),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Icon(
              Icons.error_outline,
              size: 48,
              color: Color(0xFFEF4444),
            ),
            const SizedBox(height: 12),
            const Text(
              '处理失败',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                color: Color(0xFFF8FAFC),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _errorMessage!,
              style: const TextStyle(
                fontSize: 14,
                color: Color(0xFFCBD5E1),
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                setState(() {
                  _errorMessage = null;
                  _isProcessing = false;
                  _progress = 0.0;
                });
              },
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('重试'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF8B5CF6),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 12,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _pickAndSeparateFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.audio,
      withData: true,
    );

    if (result == null || result.files.isEmpty) return;

    final file = result.files.first;
    final path = file.path;

    if (path == null) {
      setState(() {
        _errorMessage = '无法访问文件路径';
      });
      return;
    }

    final fileInfo = File(path);
    if (!fileInfo.existsSync()) {
      setState(() {
        _errorMessage = '文件不存在: $path';
      });
      return;
    }

    // Check file size (100MB limit)
    final fileSize = fileInfo.lengthSync();
    if (fileSize > 100 * 1024 * 1024) {
      setState(() {
        _errorMessage = '文件过大: ${(fileSize / (1024 * 1024)).toStringAsFixed(1)}MB (最大 100MB)';
      });
      return;
    }

    setState(() {
      _fileName = file.name;
      _isProcessing = true;
      _progress = 0.0;
      _statusMessage = '准备上传...';
      _errorMessage = null;
      _result = null;
    });

    await _uploadAndSeparate(fileInfo);
  }

  Future<void> _uploadAndSeparate(File file) async {
    try {
      final apiService = context.read<ApiService>();

      // Simulate progress updates
      setState(() {
        _statusMessage = '正在上传...';
        _progress = 0.2;
      });

      await Future.delayed(const Duration(seconds: 1));

      setState(() {
        _statusMessage = '分离中... (AI 处理)';
        _progress = 0.5;
      });

      // Call separation API
      final response = await apiService.separateAudio(file);

      setState(() {
        _progress = 1.0;
        _statusMessage = '完成!';
      });

      await Future.delayed(const Duration(milliseconds: 500));

      setState(() {
        _isProcessing = false;
        _result = response;
      });
    } catch (e) {
      setState(() {
        _isProcessing = false;
        _errorMessage = e.toString();
      });
    }
  }
}

class _ResultFileRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? path;

  const _ResultFileRow({
    required this.icon,
    required this.label,
    this.path,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF0A0A0F),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: const Color(0xFF94A3B8)),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFFF8FAFC),
                  ),
                ),
                Text(
                  path?.split('/').last ?? 'N/A',
                  style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFF64748B),
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
