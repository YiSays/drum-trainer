"""
节奏检测器 - 拍号识别、Downbeat检测、Beat Tracking、鼓模式分析

支持多种拍号识别、精确的节拍对齐和鼓手演奏模式分析。
"""

import numpy as np
import librosa
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import Counter
import warnings

warnings.filterwarnings("ignore")


@dataclass
class TimeSignature:
    """拍号数据类"""
    numerator: int  # 分子：4, 3, 6, 5, 7 等
    denominator: int  # 分母：4, 8 等
    confidence: float  # 置信度


@dataclass
class BeatInfo:
    """节拍信息"""
    bpm: int
    time_signature: TimeSignature
    downbeats: List[float]  # 小节起始时间（强拍位置）
    beats: List[float]  # 所有节拍位置
    beat_positions: List[int]  # 每个节拍在小节内的位置（0-based）


@dataclass
class Hit:
    """打击事件"""
    time: float
    velocity: float  # 0.0 - 1.0
    instrument: str  # kick, snare, hihat, cymbal, tom
    confidence: float


@dataclass
class RhythmPattern:
    """节奏模式"""
    name: str
    hits: List[Hit]
    bpm: int
    subdivision: str  # "4th", "8th", "16th", "triplet"
    complexity: float


class RhythmDetector:
    """节奏检测器"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def detect_rhythm_info(self, audio: np.ndarray, sr: int) -> BeatInfo:
        """
        检测完整的节奏信息（BPM、拍号、downbeat、节拍位置）

        Args:
            audio: 音频数据
            sr: 采样率

        Returns:
            BeatInfo 包含 BPM、拍号、downbeats、beats
        """
        # 1. 检测 BPM
        bpm = self._detect_bpm(audio, sr)

        # 2. 检测节拍位置（Beat Tracking）
        beats = self._detect_beats(audio, sr, bpm)

        # 3. 检测拍号
        time_sig = self._detect_time_signature(audio, sr, beats, bpm)

        # 4. 检测 downbeats（小节起始）
        downbeats = self._detect_downbeats(beats, time_sig)

        # 5. 计算每个节拍在小节内的位置
        beat_positions = self._calculate_beat_positions(beats, downbeats, time_sig)

        return BeatInfo(
            bpm=bpm,
            time_signature=time_sig,
            downbeats=downbeats,
            beats=beats,
            beat_positions=beat_positions
        )

    def _detect_bpm(self, audio: np.ndarray, sr: int) -> int:
        """检测 BPM（使用 Librosa）"""
        tempo, _ = librosa.beat.beat_track(y=audio, sr=sr, start_bpm=120)

        # 修正双倍/一半
        if tempo > 140:
            tempo = tempo // 2
        elif tempo < 60:
            tempo = tempo * 2

        return int(tempo)

    def _detect_beats(self, audio: np.ndarray, sr: int, bpm: int) -> List[float]:
        """
        检测节拍位置

        使用 onset strength + 强制节拍对齐
        """
        # 计算起音强度
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)

        # 使用 beat_track 获取节拍帧
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            start_bpm=bpm
        )

        # 转换为时间
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)

        # 简单后处理：过滤过于密集的节拍
        filtered_beats = []
        min_interval = 60.0 / (bpm * 2)  # 最小间隔（16分音符）

        for i, t in enumerate(beat_times):
            if i == 0 or t - filtered_beats[-1] >= min_interval:
                filtered_beats.append(float(t))

        return filtered_beats

    def _detect_time_signature(self, audio: np.ndarray, sr: int,
                               beats: List[float], bpm: int) -> TimeSignature:
        """
        检测拍号

        主要算法：
        1. 分析节拍间隔分布
        2. 检测周期性模式
        3. 基于能量峰值识别小节边界
        """
        if len(beats) < 4:
            return TimeSignature(4, 4, 0.5)  # 默认 4/4

        # 1. 计算节拍间隔
        intervals = np.diff(beats)

        # 2. 计算平均间隔
        median_interval = np.median(intervals)

        # 3. 检测长间隔（可能的小节边界）
        # 如果某个间隔 > 1.5倍中位数，可能是小节结尾
        long_intervals = intervals > (median_interval * 1.5)

        if np.sum(long_intervals) > len(intervals) * 0.1:
            # 可能是 3/4 或 6/8
            # 分析这些长间隔的分布
            long_interval_values = intervals[long_intervals]
            avg_long = np.mean(long_interval_values)
            ratio = avg_long / median_interval

            if 2.8 < ratio < 3.2:
                # 约3倍，很可能是 3/4 或 6/8
                # 进一步分析内部节奏
                return self._analyze_compound_time(audio, sr, beats)
            elif 1.8 < ratio < 2.2:
                # 约2倍，可能是 2/4
                return TimeSignature(2, 4, 0.7)
            elif 4.5 < ratio < 5.5:
                # 约5倍，可能是 5/4
                return TimeSignature(5, 4, 0.6)
            elif 6.8 < ratio < 7.2:
                # 约7倍，可能是 7/8
                return TimeSignature(7, 8, 0.6)

        # 4. 默认为 4/4，但分析内部复杂度
        return self._analyze_quadruple_time(audio, sr, beats)

    def _analyze_quadruple_time(self, audio: np.ndarray, sr: int,
                                beats: List[float]) -> TimeSignature:
        """
        分析 4/4 拍的变体
        """
        if len(beats) < 8:
            return TimeSignature(4, 4, 0.6)

        # 计算间隔变化系数
        intervals = np.diff(beats[:16])
        cv = np.std(intervals) / np.mean(intervals)

        # 如果变化很大，可能是摇摆或不规则
        if cv > 0.15:
            # 检查是否为摇摆（swing）模式
            odd_intervals = intervals[::2]
            even_intervals = intervals[1::2]

            if len(odd_intervals) > 3 and len(even_intervals) > 3:
                odd_mean = np.mean(odd_intervals)
                even_mean = np.mean(even_intervals)

                if abs(odd_mean - even_mean) / max(odd_mean, even_mean) > 0.2:
                    return TimeSignature(4, 4, 0.7)

        return TimeSignature(4, 4, 0.8)

    def _analyze_compound_time(self, audio: np.ndarray, sr: int,
                               beats: List[float]) -> TimeSignature:
        """
        分析复合拍号：6/8, 9/8, 12/8 或 3/4
        """
        if len(beats) < 6:
            return TimeSignature(6, 8, 0.6)

        # 分析内部节奏模式
        intervals = np.diff(beats[:20])

        # 使用直方图分析
        hist, bins = np.histogram(intervals, bins=5)
        peaks = np.where(hist > hist.max() * 0.3)[0]

        if len(peaks) >= 2:
            # 多个峰值，可能是 6/8 的两种间隔
            return TimeSignature(6, 8, 0.7)

        # 默认 3/4
        return TimeSignature(3, 4, 0.6)

    def _detect_downbeats(self, beats: List[float],
                          time_sig: TimeSignature) -> List[float]:
        """
        检测 downbeats（每个小节的第1拍）
        """
        if len(beats) < 3:
            return []

        downbeats = [beats[0]]  # 第一个节拍肯定是 downbeat

        # 分析节拍间隔，寻找显著的长间隔
        intervals = np.diff(beats)

        # 计算阈值：平均间隔的1.5倍
        if len(intervals) > 0:
            threshold = np.mean(intervals) * 1.5

            for i, interval in enumerate(intervals):
                if interval > threshold:
                    # 这是一个小节边界
                    downbeats.append(beats[i + 1])

        # 如果检测到的 downbeats 太少，使用周期性假设
        if len(downbeats) < len(beats) / 4:
            # 根据拍号周期推断
            if time_sig.numerator == 4:
                period = 4
            elif time_sig.numerator == 3:
                period = 3
            elif time_sig.numerator == 6:
                period = 2
            elif time_sig.numerator == 5:
                period = 5
            else:
                period = 4

            downbeats = beats[::period]

        return downbeats

    def _calculate_beat_positions(self, beats: List[float],
                                  downbeats: List[float],
                                  time_sig: TimeSignature) -> List[int]:
        """
        计算每个节拍在小节内的位置（0-based）
        """
        if not downbeats or not beats:
            return []

        positions = []
        current_downbeat_idx = 0

        for beat_time in beats:
            # 如果超过当前downbeat，移动到下一个
            while (current_downbeat_idx + 1 < len(downbeats) and
                   beat_time >= downbeats[current_downbeat_idx + 1]):
                current_downbeat_idx += 1

            current_downbeat_time = downbeats[current_downbeat_idx]

            # 找到下一个downbeat
            next_downbeat_time = (downbeats[current_downbeat_idx + 1]
                                  if current_downbeat_idx + 1 < len(downbeats)
                                  else beat_time + 10)

            # 估算节拍位置
            beat_interval = (next_downbeat_time - current_downbeat_time) / time_sig.numerator

            if beat_interval > 0:
                pos_float = (beat_time - current_downbeat_time) / beat_interval
                pos = int(round(pos_float))
                # 确保在范围内
                pos = max(0, min(pos, time_sig.numerator - 1))
            else:
                pos = 0

            positions.append(pos)

        return positions

    def detect(self, audio: np.ndarray, sr: int, bpm: int) -> List[RhythmPattern]:
        """
        检测节奏模式（旧版本，保留兼容性）

        Args:
            audio: 音频数据（应该是分离后的鼓轨）
            sr: 采样率
            bpm: 已知BPM

        Returns:
            节奏模式列表
        """
        # 1. 检测所有打击事件
        hits = self._detect_hits(audio, sr)

        # 2. 分类乐器类型
        hits = self._classify_instruments(hits, audio, sr)

        # 3. 分析节奏结构
        patterns = self._analyze_patterns(hits, bpm)

        return patterns

    def _detect_hits(self, audio: np.ndarray, sr: int) -> List[Hit]:
        """
        检测所有可能的打击事件
        """
        # 提取起音点
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_frames = librosa.util.peak_pick(
            onset_env,
            pre_max=20, post_max=20,
            pre_avg=20, post_avg=20,
            delta=0.1, wait=10
        )

        # 转换为时间
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)

        # 提取能量（用于Velocity）
        rms = librosa.feature.rms(y=audio)[0]

        hits = []
        for frame, time in zip(onset_frames, onset_times):
            velocity = rms[frame] if frame < len(rms) else 0.1
            hits.append(Hit(
                time=time,
                velocity=float(np.clip(velocity, 0, 1)),
                instrument="unknown",
                confidence=0.5
            ))

        return hits

    def _classify_instruments(self, hits: List[Hit], audio: np.ndarray, sr: int) -> List[Hit]:
        """
        使用频谱特征分类乐器类型
        """
        if not hits:
            return hits

        # 预分析整个音频的频谱特征
        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]

        for hit in hits:
            # 获取该时间点的频谱特征
            frame = librosa.time_to_frames(hit.time, sr=sr)
            if frame >= len(spectral_centroids):
                frame = len(spectral_centroids) - 1

            centroid = spectral_centroids[frame]
            bandwidth = spectral_bandwidth[frame]

            # 分类规则
            if centroid < 150:  # 低频
                if bandwidth < 200:
                    hit.instrument = "kick"
                    hit.confidence = 0.85
                else:
                    hit.instrument = "tom"
                    hit.confidence = 0.75
            elif centroid < 800:  # 中低频
                if bandwidth > 400:
                    hit.instrument = "snare"
                    hit.confidence = 0.8
                else:
                    hit.instrument = "cymbal"
                    hit.confidence = 0.7
            else:  # 高频
                if bandwidth < 300:
                    hit.instrument = "hihat"
                    hit.confidence = 0.9
                else:
                    hit.instrument = "cymbal"
                    hit.confidence = 0.75

        return hits

    def _analyze_patterns(self, hits: List[Hit], bpm: int) -> List[RhythmPattern]:
        """
        分析节奏模式
        """
        if len(hits) < 4:
            return []

        patterns = []

        # 计算节拍间隔
        beat_duration = 60.0 / bpm

        # 将打击事件量化到最近的节拍网格
        quantized = self._quantize_hits(hits, beat_duration)

        # 分析主要模式
        main_pattern = self._analyze_main_pattern(quantized, beat_duration)
        patterns.append(main_pattern)

        # 如果有明显的变奏，检测变奏模式
        variations = self._detect_variations(quantized, beat_duration)
        patterns.extend(variations)

        return patterns

    def _quantize_hits(self, hits: List[Hit], beat_duration: float) -> List[Tuple[int, int, Hit]]:
        """
        量化打击事件到16分音符网格
        """
        quantized = []

        for hit in hits:
            # 找到最近的节拍
            beat_position = hit.time / beat_duration
            nearest_beat = round(beat_position)

            # 16分音符精度 (每个节拍4个16分音符)
            sixteenth_position = (beat_position - nearest_beat) * 4
            nearest_sixteenth = round(sixteenth_position)

            # 归一化到0-15范围
            if nearest_sixteenth < 0:
                nearest_sixteenth = 4 + nearest_sixteenth

            grid_pos = (nearest_beat % 4) * 4 + nearest_sixteenth
            quantized.append((nearest_beat, int(grid_pos), hit))

        return quantized

    def _analyze_main_pattern(self, quantized: List[Tuple[int, int, Hit]], beat_duration: float) -> RhythmPattern:
        """
        分析主要节奏模式
        """
        if not quantized:
            return RhythmPattern("unknown", [], 0, "4th", 0.0)

        # 按乐器分组
        hits_by_instrument = {}
        for _, grid_pos, hit in quantized:
            if hit.instrument not in hits_by_instrument:
                hits_by_instrument[hit.instrument] = []
            hits_by_instrument[hit.instrument].append((grid_pos, hit))

        # 确定主节奏模式
        pattern_name = "unknown"
        subdivision = "4th"
        complexity = 0.5

        # 基于Kick和Snare的模式
        kick_hits = hits_by_instrument.get("kick", [])
        snare_hits = hits_by_instrument.get("snare", [])

        if len(kick_hits) > 0:
            kick_positions = [pos for pos, _ in kick_hits]
            kick_counter = Counter(kick_positions)

            # 检测常见模式
            if kick_counter[0] > 0 and kick_counter[3] > 0:  # 1 & 3
                pattern_name = "rock_basic"
                subdivision = "4th"
                complexity = 0.3
            elif kick_counter[0] > 0 and kick_counter[2] > 0:  # 1 & 2
                pattern_name = "four_on_floor"
                subdivision = "4th"
                complexity = 0.2
            elif any(kick_counter[i] > 0 for i in [1, 3]):  # 反拍
                pattern_name = "funk_16th"
                subdivision = "16th"
                complexity = 0.7
            else:
                pattern_name = "custom_kick"
                subdivision = "8th"
                complexity = 0.5

        # 检查Snare
        if len(snare_hits) > 0:
            snare_positions = [pos for pos, _ in snare_hits]
            if 4 in snare_positions or 12 in snare_positions:  # 2 & 4
                if pattern_name == "rock_basic":
                    pattern_name = "rock_standard"
                elif pattern_name == "unknown":
                    pattern_name = "backbeat_snare"

        # 计算复杂度
        total_hits = len(quantized)
        if total_hits > 0:
            density = total_hits / (quantized[-1][0] + 1)  # 每节拍平均
            complexity = min(0.9, density * 0.3 + complexity)

        # 提取打击列表
        pattern_hits = [hit for _, _, hit in quantized]

        return RhythmPattern(
            name=pattern_name,
            hits=pattern_hits,
            bpm=int(np.mean([h.velocity for h in pattern_hits]) * bpm) if pattern_hits else bpm,
            subdivision=subdivision,
            complexity=complexity
        )

    def _detect_variations(self, quantized: List[Tuple[int, int, Hit]], beat_duration: float) -> List[RhythmPattern]:
        """
        检测节奏变奏
        """
        # 简化实现：检测密度变化
        if len(quantized) < 8:
            return []

        # 计算滑动窗口的密度
        window_size = 4  # 每4个节拍一个窗口
        variations = []

        for i in range(0, len(quantized) - window_size, window_size):
            window = quantized[i:i+window_size]
            density = len(window) / window_size

            if density > 0.7:  # 高密度
                hits = [hit for _, _, hit in window]
                variations.append(RhythmPattern(
                    name="high_energy_variation",
                    hits=hits,
                    bpm=120,  # 临时
                    subdivision="16th",
                    complexity=0.8
                ))

        return variations

    def get_rhythm_report(self, patterns: List[RhythmPattern]) -> Dict:
        """生成节奏报告"""
        if not patterns:
            return {"status": "no_patterns_detected"}

        main = patterns[0]
        return {
            "main_pattern": main.name,
            "bpm": main.bpm,
            "subdivision": main.subdivision,
            "complexity": round(main.complexity, 2),
            "total_hits": len(main.hits),
            "pattern_distribution": self._get_pattern_distribution(main.hits),
            "recommended_practice": self._get_practice_recommendation(main)
        }

    def _get_pattern_distribution(self, hits: List[Hit]) -> Dict:
        """统计乐器分布"""
        distribution = {}
        for hit in hits:
            distribution[hit.instrument] = distribution.get(hit.instrument, 0) + 1
        return distribution

    def _get_practice_recommendation(self, pattern: RhythmPattern) -> str:
        """生成练习建议"""
        if pattern.complexity < 0.3:
            return "基础节奏练习：保持稳定的四分音符"
        elif pattern.complexity < 0.6:
            return "中级节奏练习：注意反拍和八分音符"
        else:
            return "高级节奏练习：注意十六分音符的精确性和动态"

    def generate_midi_pattern(self, pattern: RhythmPattern, output_path: str):
        """
        生成MIDI文件（可选功能）
        需要 midiutil 库
        """
        try:
            from midiutil import MIDIFile

            midi = MIDIFile(1)
            midi.addTempo(0, 0, pattern.bpm)

            # 将每个命中转换为MIDI音符
            # Kick: 36, Snare: 38, Hi-hat: 42
            note_map = {
                "kick": 36,
                "snare": 38,
                "hihat": 42,
                "cymbal": 49,
                "tom": 45,
                "unknown": 38
            }

            for hit in pattern.hits:
                note = note_map.get(hit.instrument, 38)
                time = hit.time / 60.0 * pattern.bpm  # 转换为节拍
                midi.addNote(0, 0, note, time, 0.25, int(hit.velocity * 100))

            with open(output_path, 'wb') as f:
                midi.writeFile(f)

            print(f"MIDI 文件已生成: {output_path}")

        except ImportError:
            print("需要安装 midiutil: pip install midiutil")
