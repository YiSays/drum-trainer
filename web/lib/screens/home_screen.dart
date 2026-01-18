import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:drum_trainer_web/services/api_service.dart';
import 'package:drum_trainer_web/services/audio_service.dart';
import 'package:drum_trainer_web/models/track_model.dart';
import 'package:drum_trainer_web/widgets/track_card.dart';
import 'package:drum_trainer_web/screens/track_player_screen.dart';
import 'package:drum_trainer_web/screens/separation_screen.dart';
import 'package:drum_trainer_web/screens/analysis_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isLoading = false;
  bool _apiConnected = false;
  String? _errorMessage;
  List<Track> _tracks = [];
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _checkApiAndLoadTracks();
  }

  Future<void> _checkApiAndLoadTracks() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final apiService = context.read<ApiService>();
      _apiConnected = await apiService.checkHealth();

      if (_apiConnected) {
        final response = await apiService.getTracks();
        setState(() {
          _tracks = response.tracks;
          _isLoading = false;
        });
      } else {
        setState(() {
          _isLoading = false;
          _errorMessage = '无法连接到 API 服务';
        });
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = '加载失败: $e';
      });
    }
  }

  List<Track> get _filteredTracks {
    if (_searchQuery.isEmpty) return _tracks;
    return _tracks
        .where((track) =>
            track.name.toLowerCase().contains(_searchQuery.toLowerCase()))
        .toList();
  }

  void _onTrackSelected(Track track) {
    final apiService = context.read<ApiService>();
    final audioUrl = apiService.getAudioUrl(track.name);
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => TrackPlayerScreen(
          track: track,
          audioUrl: audioUrl,
        ),
      ),
    );
  }

  void _onTrackAnalyzed(Track track) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AnalysisScreen(
          track: track,
        ),
      ),
    );
  }

  void _goToSeparation() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const SeparationScreen(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0F),
      appBar: AppBar(
        title: const Row(
          children: [
            Text('🥁 Drum Trainer'),
            SizedBox(width: 8),
            Text(
              'Web',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w400,
                color: Color(0xFF94A3B8),
              ),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF12121A),
        elevation: 1,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _checkApiAndLoadTracks,
            tooltip: '刷新',
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Column(
        children: [
          // API Status Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: _apiConnected
                ? const Color(0xFF1A1A24)
                : const Color(0xFF1A1A24),
            child: Row(
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _apiConnected
                        ? const Color(0xFF10B981)
                        : const Color(0xFFEF4444),
                    boxShadow: [
                      BoxShadow(
                        color: _apiConnected
                            ? const Color(0xFF10B981).withOpacity(0.5)
                            : const Color(0xFFEF4444).withOpacity(0.5),
                        blurRadius: 4,
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  _apiConnected ? 'API 已连接' : 'API 未连接',
                  style: TextStyle(
                    color: _apiConnected
                        ? const Color(0xFF10B981)
                        : const Color(0xFFEF4444),
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                ElevatedButton.icon(
                  onPressed: _goToSeparation,
                  icon: const Icon(Icons.upload_file, size: 18),
                  label: const Text('上传 & 分离'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF8B5CF6),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Search Bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              decoration: InputDecoration(
                hintText: '搜索音轨...',
                prefixIcon: const Icon(Icons.search, color: Color(0xFF94A3B8)),
                filled: true,
                fillColor: const Color(0xFF1A1A24),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 14,
                ),
              ),
              onChanged: (value) {
                setState(() {
                  _searchQuery = value;
                });
              },
            ),
          ),

          // Content Area
          Expanded(
            child: _buildContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
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
              '加载音轨中...',
              style: TextStyle(
                color: Color(0xFF94A3B8),
                fontSize: 16,
              ),
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
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
              onPressed: _checkApiAndLoadTracks,
              child: const Text('重试'),
            ),
          ],
        ),
      );
    }

    if (_filteredTracks.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.music_note,
              size: 64,
              color: Color(0xFF64748B),
            ),
            const SizedBox(height: 16),
            Text(
              _searchQuery.isEmpty ? '暂无音轨' : '未找到匹配的音轨',
              style: const TextStyle(
                color: Color(0xFF94A3B8),
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (_searchQuery.isEmpty) ...[
              const SizedBox(height: 8),
              const Text(
                '点击右上角 "上传 & 分离" 按钮添加音频文件',
                style: TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 14,
                ),
              ),
            ],
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: _filteredTracks.length,
      itemBuilder: (context, index) {
        final track = _filteredTracks[index];
        return Padding(
          padding: EdgeInsets.only(
            bottom: index == _filteredTracks.length - 1 ? 16 : 8,
          ),
          child: TrackCard(
            track: track,
            onPlay: () => _onTrackSelected(track),
            onAnalyze: () => _onTrackAnalyzed(track),
          ),
        );
      },
    );
  }
}
