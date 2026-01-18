import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:drum_trainer_web/services/api_service.dart';
import 'package:drum_trainer_web/models/api_models.dart';
import 'package:drum_trainer_web/models/track_model.dart';

class AnalysisScreen extends StatefulWidget {
  final Track track;

  const AnalysisScreen({
    super.key,
    required this.track,
  });

  @override
  State<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends State<AnalysisScreen> {
  bool _isAnalyzing = false;
  AnalysisResponse? _result;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _analyzeTrack();
  }

  Future<void> _analyzeTrack() async {
    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
      _result = null;
    });

    try {
      // For this demo, we'll create a mock result
      // In production, this would call the API
      await Future.delayed(const Duration(seconds: 2));

      // Simulate analysis result
      setState(() {
        _result = AnalysisResponse(
          status: 'success',
          message: 'Analysis complete',
          analysis: AnalysisResult(
            bpm: 128.0,
            style: 'Rock',
            mood: 'Energetic',
            energy: 0.85,
            key: 'C',
            structure: MusicStructure(
              totalSections: 4,
              types: {
                'intro': 1,
                'verse': 1,
                'chorus': 2,
              },
              sections: [
                Section(type: 'intro', start: 0, end: 16, duration: 16),
                Section(type: 'verse', start: 16, end: 48, duration: 32),
                Section(type: 'chorus', start: 48, end: 80, duration: 32),
                Section(type: 'chorus', start: 80, end: 112, duration: 32),
              ],
            ),
            rhythmProfile: RhythmProfile(
              mainPattern: 'rock_standard',
              complexity: 0.45,
              recommendedPractice: '基础节奏练习：保持稳定的四分音符',
            ),
          ),
        );
        _isAnalyzing = false;
      });
    } catch (e) {
      setState(() {
        _isAnalyzing = false;
        _errorMessage = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0F),
      appBar: AppBar(
        title: const Text('音乐分析'),
        backgroundColor: const Color(0xFF12121A),
        elevation: 1,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _analyzeTrack,
            tooltip: '重新分析',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Track Header
            _buildTrackHeader(),

            const SizedBox(height: 24),

            // Content
            _buildContent(),
          ],
        ),
      ),
    );
  }

  Widget _buildTrackHeader() {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: const Color(0xFF8B5CF6).withOpacity(0.2),
                borderRadius: BorderRadius.circular(12),
              ),
              alignment: Alignment.center,
              child: Text(
                widget.track.icon,
                style: const TextStyle(fontSize: 28),
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
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: Color(0xFFF8FAFC),
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    widget.track.formattedDuration,
                    style: const TextStyle(
                      fontSize: 13,
                      color: Color(0xFF94A3B8),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_isAnalyzing) {
      return Container(
        padding: const EdgeInsets.all(40),
        child: const Column(
          children: [
            CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF8B5CF6)),
              strokeWidth: 4,
            ),
            SizedBox(height: 20),
            Text(
              '分析中...',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Color(0xFFCBD5E1),
              ),
            ),
            SizedBox(height: 8),
            Text(
              '正在进行 BPM 检测、风格识别、情绪分析等',
              style: TextStyle(
                fontSize: 13,
                color: Color(0xFF94A3B8),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          children: [
            const Icon(
              Icons.error_outline,
              size: 48,
              color: Color(0xFFEF4444),
            ),
            const SizedBox(height: 16),
            Text(
              _errorMessage!,
              style: const TextStyle(
                color: Color(0xFFCBD5E1),
                fontSize: 16,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _analyzeTrack,
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    if (_result == null) {
      return const Center(
        child: Text(
          '暂无分析数据',
          style: TextStyle(
            color: Color(0xFF94A3B8),
            fontSize: 16,
          ),
        ),
      );
    }

    final analysis = _result!.analysis!;

    return Column(
      children: [
        // Overview Stats
        _buildStatsGrid(analysis),

        const SizedBox(height: 20),

        // BPM Display
        _buildBPMCard(analysis),

        const SizedBox(height: 20),

        // Structure
        if (analysis.structure != null) ...[
          _buildStructureCard(analysis.structure!),
          const SizedBox(height: 20),
        ],

        // Rhythm Profile
        if (analysis.rhythmProfile != null) ...[
          _buildRhythmCard(analysis.rhythmProfile!),
          const SizedBox(height: 20),
        ],

        // Info Box
        _buildInfoBox(),
      ],
    );
  }

  Widget _buildStatsGrid(AnalysisResult analysis) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '分析概览',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: Color(0xFFF8FAFC),
              ),
            ),
            const SizedBox(height: 16),
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.8,
              children: [
                _StatCard(
                  label: 'BPM',
                  value: analysis.bpmInt.toString(),
                  color: const Color(0xFF8B5CF6),
                  icon: Icons.speed,
                ),
                _StatCard(
                  label: '风格',
                  value: analysis.style,
                  color: const Color(0xFFF59E0B),
                  icon: Icons.style,
                ),
                _StatCard(
                  label: '情绪',
                  value: analysis.mood,
                  color: const Color(0xFF10B981),
                  icon: Icons.mood,
                ),
                _StatCard(
                  label: '调性',
                  value: analysis.key,
                  color: const Color(0xFF3B82F6),
                  icon: Icons.piano,
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Energy Bar
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF1A1A24),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        '能量',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFCBD5E1),
                        ),
                      ),
                      Text(
                        analysis.energyPercent,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF8B5CF6),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: analysis.energy,
                      backgroundColor: const Color(0xFF334155),
                      valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFF8B5CF6)),
                      minHeight: 8,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBPMCard(AnalysisResult analysis) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: const Color(0xFF8B5CF6).withOpacity(0.2),
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
            colors: [
              const Color(0xFF8B5CF6).withOpacity(0.3),
              const Color(0xFFA78BFA).withOpacity(0.3),
            ],
          ),
          border: Border.all(color: const Color(0xFF8B5CF6)),
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const Icon(
              Icons.speed,
              size: 36,
              color: Color(0xFFF8FAFC),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'BPM (每分钟节拍数)',
                    style: TextStyle(
                      fontSize: 13,
                      color: Color(0xFFCBD5E1),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    analysis.bpmInt.toString(),
                    style: const TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                      color: Color(0xFFF8FAFC),
                    ),
                  ),
                ],
              ),
            ),
            const Icon(
              Icons.favorite,
              size: 24,
              color: Color(0xFFFBBF24),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStructureCard(MusicStructure structure) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '歌曲结构',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: Color(0xFFF8FAFC),
              ),
            ),
            const SizedBox(height: 12),
            // Section Chips
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: structure.sections.map((section) {
                Color color;
                switch (section.type) {
                  case 'intro':
                    color = const Color(0xFF10B981);
                    break;
                  case 'verse':
                    color = const Color(0xFFF59E0B);
                    break;
                  case 'chorus':
                    color = const Color(0xFF8B5CF6);
                    break;
                  case 'bridge':
                    color = const Color(0xFFEF4444);
                    break;
                  default:
                    color = const Color(0xFF64748B);
                }
                return Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.2),
                    border: Border.all(color: color),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    children: [
                      Text(
                        section.type.toUpperCase(),
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: color,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${section.duration}s',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: color.withOpacity(0.8),
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 12),
            // Type Summary
            if (structure.types.isNotEmpty) ...[
              Text(
                '段落统计: ${structure.types.entries.map((e) => '${e.value}x ${e.key}').join(', ')}',
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF94A3B8),
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRhythmCard(RhythmProfile profile) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: const Color(0xFF1A1A24),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '节奏特征',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: Color(0xFFF8FAFC),
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF0A0A0F),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.music_note, size: 18, color: Color(0xFF94A3B8)),
                      const SizedBox(width: 8),
                      Text(
                        profile.mainPattern,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFF8FAFC),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '复杂度',
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF94A3B8),
                    ),
                  ),
                  const SizedBox(height: 4),
                  LinearProgressIndicator(
                    value: profile.complexity,
                    backgroundColor: const Color(0xFF334155),
                    valueColor: const AlwaysStoppedAnimation<Color>(Color(0xFFF59E0B)),
                    minHeight: 6,
                    borderRadius: BorderRadius.circular(3),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    profile.complexityPercent,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFFF59E0B),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            // Practice Tip
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF10B981).withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.lightbulb,
                    size: 18,
                    color: Color(0xFF10B981),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      profile.recommendedPractice,
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF10B981),
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoBox() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A24).withOpacity(0.5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: const Row(
        children: [
          Icon(Icons.info, size: 18, color: Color(0xFF94A3B8)),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              '这些分析结果基于 AI 算法生成，可用于练习参考和音乐理解',
              style: TextStyle(
                fontSize: 12,
                color: Color(0xFFCBD5E1),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;
  final IconData icon;

  const _StatCard({
    required this.label,
    required this.value,
    required this.color,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A24),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: color.withOpacity(0.8),
                ),
              ),
            ],
          ),
          const Spacer(),
          Text(
            value,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w800,
              color: color,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
