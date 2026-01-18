"""
鼓演奏生成器 - 基于音乐分析智能生成鼓点

使用预定义的节奏库和规则生成适合歌曲的鼓演奏。
"""

import numpy as np
import librosa
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")


@dataclass
class DrumPattern:
    """鼓模式定义"""
    name: str
    style: str
    bpm_range: Tuple[int, int]
    kick_pattern: List[int]  # 16分音符网格 (0-15)
    snare_pattern: List[int]
    hihat_pattern: List[int]
    complexity: float


@dataclass
class GeneratedDrumTrack:
    """生成的鼓轨道"""
    audio: np.ndarray
    bpm: int
    pattern: str
    sections: List[Dict]


class DrumGenerator:
    """鼓演奏生成器"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.pattern_library = self._init_pattern_library()

    def _init_pattern_library(self) -> Dict[str, DrumPattern]:
        """初始化预定义的节奏模式库"""
        patterns = {
            "rock_basic": DrumPattern(
                name="rock_basic",
                style="rock",
                bpm_range=(90, 140),
                kick_pattern=[0, 4, 8, 12],  # 1, 2, 3, 4
                snare_pattern=[4, 12],       # 2, 4
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],  # 8分音符
                complexity=0.3
            ),
            "rock_energy": DrumPattern(
                name="rock_energy",
                style="rock",
                bpm_range=(120, 160),
                kick_pattern=[0, 2, 4, 7, 8, 12],  # 1, 1&, 2, 2&, 3, 4
                snare_pattern=[4, 12],              # 2, 4
                hihat_pattern=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],  # 16分音符
                complexity=0.7
            ),
            "funk_basic": DrumPattern(
                name="funk_basic",
                style="funk",
                bpm_range=(100, 130),
                kick_pattern=[0, 3, 4, 7, 8, 11, 12],  # 紧凑的funk kick
                snare_pattern=[4, 12],                  # 2, 4
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],  # 8分音符开镲
                complexity=0.6
            ),
            "funk_advanced": DrumPattern(
                name="funk_advanced",
                style="funk",
                bpm_range=(100, 140),
                kick_pattern=[0, 2, 4, 6, 8, 11, 12],  # 1, 1&, 2, 2&, 3, 3&, 4
                snare_pattern=[4, 12, 14],              # 2, 4, 4&
                hihat_pattern=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],  # 16分音符
                complexity=0.9
            ),
            "jazz_swing": DrumPattern(
                name="jazz_swing",
                style="jazz",
                bpm_range=(60, 100),
                kick_pattern=[0, 5, 8, 13],  # 摇摆节奏
                snare_pattern=[2, 6, 10, 14],  # 轻柔的snare
                hihat_pattern=[0, 3, 4, 7, 8, 11, 12, 15],  # 踩镲
                complexity=0.5
            ),
            "jazz_ride": DrumPattern(
                name="jazz_ride",
                style="jazz",
                bpm_range=(70, 110),
                kick_pattern=[0, 8],  # 简单的kick
                snare_pattern=[4, 12, 14],  # 2, 4, 4&
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],  # 8分音符
                complexity=0.4
            ),
            "pop_standard": DrumPattern(
                name="pop_standard",
                style="pop",
                bpm_range=(100, 130),
                kick_pattern=[0, 4, 8, 12],
                snare_pattern=[4, 12],
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],
                complexity=0.3
            ),
            "pop_modern": DrumPattern(
                name="pop_modern",
                style="pop",
                bpm_range=(110, 140),
                kick_pattern=[0, 4, 6, 8, 12],  # 添加8&的kick
                snare_pattern=[4, 12],
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14, 15],  # 少量16分音符
                complexity=0.5
            ),
            "electronic_four": DrumPattern(
                name="electronic_four",
                style="electronic",
                bpm_range=(120, 140),
                kick_pattern=[0, 4, 8, 12],  # 4/4拍
                snare_pattern=[4, 12],
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14, 15],  # 高速开镲
                complexity=0.4
            ),
            "electronic_breaks": DrumPattern(
                name="electronic_breaks",
                style="electronic",
                bpm_range=(130, 180),
                kick_pattern=[0, 2, 4, 7, 8, 11, 12],  # 复杂kick
                snare_pattern=[4, 12, 14],              # 紧凑snare
                hihat_pattern=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],  # 16分音符
                complexity=0.8
            ),
            "hip_hop_basic": DrumPattern(
                name="hip_hop_basic",
                style="hip_hop",
                bpm_range=(70, 95),
                kick_pattern=[0, 8],  # 1, 3
                snare_pattern=[4, 12],  # 2, 4
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],  # 8分音符
                complexity=0.3
            ),
            "hip_hop_groove": DrumPattern(
                name="hip_hop_groove",
                style="hip_hop",
                bpm_range=(80, 100),
                kick_pattern=[0, 3, 7, 8, 11],  # 移位的kick
                snare_pattern=[4, 12, 14],  # 2, 4, 4&
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14, 15],  # 8分+16分
                complexity=0.6
            ),
            "reggae_one": DrumPattern(
                name="reggae_one",
                style="reggae",
                bpm_range=(70, 95),
                kick_pattern=[0, 8],  # One drop
                snare_pattern=[4, 12],  # 2, 4
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],  # 8分音符
                complexity=0.2
            ),
            "punk_fast": DrumPattern(
                name="punk_fast",
                style="punk",
                bpm_range=(140, 180),
                kick_pattern=[0, 4, 8, 12],
                snare_pattern=[4, 12],
                hihat_pattern=[0, 2, 4, 6, 8, 10, 12, 14],  # 8分音符
                complexity=0.4
            ),
        }

        return patterns

    def generate_from_analysis(self, analysis: Dict, output_dir: Path) -> GeneratedDrumTrack:
        """
        根据音乐分析生成鼓演奏（支持多种拍号和downbeat）

        Args:
            analysis: 音乐分析结果 (来自 MusicAnalyzer)
            output_dir: 输出目录

        Returns:
            生成的鼓轨道
        """
        print("🥁 开始生成鼓演奏...")

        # 1. 选择合适的模式
        pattern = self._select_pattern(analysis)

        print(f"   选择模式: {pattern.name} (复杂度: {pattern.complexity})")

        # 2. 获取节奏信息
        bpm = analysis["bpm"]
        structure = analysis.get("structure", [])

        if not structure:
            # 没有结构信息，生成一个4小节的简单模式
            duration = 4 * 60.0 / bpm * 4  # 4小节
            sections = [{"type": "main", "start": 0, "end": duration, "duration": duration}]
        else:
            sections = structure

        # 3. 获取拍号和downbeat信息（如果有）
        time_signature = analysis.get("time_signature", {"numerator": 4, "denominator": 4})
        downbeats = analysis.get("downbeats", None)
        beats = analysis.get("beats", None)
        beat_positions = analysis.get("beat_positions", None)

        # 4. 合成音频（新版本，支持多种拍号）
        audio = self._synthesize_drums_advanced(
            pattern, bpm, sections,
            time_signature=time_signature,
            downbeats=downbeats,
            beats=beats,
            beat_positions=beat_positions
        )

        result = GeneratedDrumTrack(
            audio=audio,
            bpm=bpm,
            pattern=pattern.name,
            sections=sections
        )

        # 5. 保存文件
        self._save_drums(result, output_dir)

        return result

    def _select_pattern(self, analysis: Dict) -> DrumPattern:
        """
        基于分析选择最合适的节奏模式
        """
        style = analysis["style"]
        bpm = analysis["bpm"]
        energy = analysis.get("energy", 0.2)
        complexity_pref = analysis.get("rhythm_profile", {}).get("complexity", 0.5)

        # 过滤匹配风格和BPM的模式
        candidates = [
            p for p in self.pattern_library.values()
            if p.style == style and p.bpm_range[0] <= bpm <= p.bpm_range[1]
        ]

        if not candidates:
            # 如果没有完美匹配，放宽条件
            candidates = [
                p for p in self.pattern_library.values()
                if p.style == style or (p.bpm_range[0] <= bpm <= p.bpm_range[1])
            ]

        if not candidates:
            # 最后的选择：任何模式
            candidates = list(self.pattern_library.values())

        # 根据能量和复杂度偏好选择
        best_score = -1
        best_pattern = candidates[0]

        for pattern in candidates:
            # 复杂度匹配分数
            complexity_diff = abs(pattern.complexity - complexity_pref)

            # 能量匹配（低能量 → 低复杂度）
            energy_score = 1.0 - abs(pattern.complexity - energy)

            # BPM匹配度
            bpm_mid = (pattern.bpm_range[0] + pattern.bpm_range[1]) / 2
            bpm_score = 1.0 - abs(bpm - bpm_mid) / 50.0

            # 总分
            score = (bpm_score * 0.4) + (energy_score * 0.3) + ((1 - complexity_diff) * 0.3)

            if score > best_score:
                best_score = score
                best_pattern = pattern

        return best_pattern

    def _synthesize_drums(self, pattern: DrumPattern, bpm: int, sections: List[Dict]) -> np.ndarray:
        """
        根据模式合成鼓音频

        Args:
            pattern: 鼓模式
            bpm: 速度
            sections: 段落信息

        Returns:
            合成的音频数据
        """
        # 计算总时长
        total_duration = sum(s.get("duration", s.get("end", 0) - s.get("start", 0)) for s in sections)

        # 计算采样点数
        total_samples = int(total_duration * self.sample_rate)

        # 初始化音频
        audio = np.zeros(total_samples, dtype=np.float32)

        # 每个节拍的采样数
        beat_samples = int(60.0 / bpm * self.sample_rate)

        # 16分音符采样数
        sixteenth_samples = beat_samples // 4

        # 基准音量
        kick_volume = 0.8
        snare_volume = 0.6
        hihat_volume = 0.3

        current_sample = 0

        for section in sections:
            section_duration = section.get("duration", section.get("end", 0) - section.get("start", 0))
            section_beats = int(section_duration * bpm / 60.0)

            # 根据段落类型调整
            if section.get("type") == "chorus":
                kick_volume_adj = 1.0
                snare_volume_adj = 1.0
                hihat_volume_adj = 0.5
            elif section.get("type") == "verse":
                kick_volume_adj = 0.8
                snare_volume_adj = 0.8
                hihat_volume_adj = 0.3
            elif section.get("type") == "intro":
                kick_volume_adj = 0.5
                snare_volume_adj = 0.3
                hihat_volume_adj = 0.4
            else:
                kick_volume_adj = 0.8
                snare_volume_adj = 0.8
                hihat_volume_adj = 0.3

            # 生成每个节拍
            for beat in range(section_beats):
                base_beat_sample = current_sample + beat * beat_samples

                # Kick
                for kick_pos in pattern.kick_pattern:
                    hit_sample = base_beat_sample + kick_pos * sixteenth_samples
                    if hit_sample < total_samples:
                        self._add_kick(audio, hit_sample, kick_volume * kick_volume_adj)

                # Snare
                for snare_pos in pattern.snare_pattern:
                    hit_sample = base_beat_sample + snare_pos * sixteenth_samples
                    if hit_sample < total_samples:
                        self._add_snare(audio, hit_sample, snare_volume * snare_volume_adj)

                # Hi-hat
                for hihat_pos in pattern.hihat_pattern:
                    hit_sample = base_beat_sample + hihat_pos * sixteenth_samples
                    if hit_sample < total_samples:
                        self._add_hihat(audio, hit_sample, hihat_volume * hihat_volume_adj)

                # 偶尔的fills（在段落结束前2拍）
                if beat >= section_beats - 2 and pattern.complexity > 0.5:
                    if np.random.random() > 0.6:  # 40%概率
                        self._add_fill(audio, base_beat_sample + beat_samples - sixteenth_samples, snare_volume_adj)

            current_sample += int(section_duration * self.sample_rate)

        # 归一化
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio * 0.9 / max_val

        return audio

    def _synthesize_drums_advanced(self, pattern: DrumPattern, bpm: int, sections: List[Dict],
                                   time_signature: Dict = None,
                                   downbeats: List[float] = None,
                                   beats: List[float] = None,
                                   beat_positions: List[int] = None) -> np.ndarray:
        """
        高级鼓合成 - 支持多种拍号和downbeat对齐

        Args:
            pattern: 鼓模式
            bpm: 速度
            sections: 段落信息
            time_signature: 拍号 {"numerator": 4, "denominator": 4}
            downbeats: downbeat时间列表
            beats: 完整节拍时间列表
            beat_positions: 每个节拍在小节内的位置

        Returns:
            合成的音频数据
        """
        # 默认拍号
        if time_signature is None:
            time_signature = {"numerator": 4, "denominator": 4}

        numerator = time_signature.get("numerator", 4)
        denominator = time_signature.get("denominator", 4)

        # 计算总时长
        total_duration = sum(s.get("duration", s.get("end", 0) - s.get("start", 0)) for s in sections)

        # 计算采样点数
        total_samples = int(total_duration * self.sample_rate)

        # 初始化音频
        audio = np.zeros(total_samples, dtype=np.float32)

        # 每个节拍的采样数
        beat_samples = int(60.0 / bpm * self.sample_rate)

        # 根据分母计算音符网格
        # 4 = 四分音符, 8 = 八分音符, 16 = 十六分音符
        subdivision_unit = denominator // 4 if denominator >= 4 else 4
        sixteenth_samples = beat_samples // 4  # 始终基于16分音符网格

        # 基准音量
        kick_volume = 0.8
        snare_volume = 0.6
        hihat_volume = 0.3

        current_sample = 0

        for section in sections:
            section_duration = section.get("duration", section.get("end", 0) - section.get("start", 0))
            section_beats = int(section_duration * bpm / 60.0)

            # 根据段落类型调整
            if section.get("type") == "chorus":
                kick_volume_adj = 1.0
                snare_volume_adj = 1.0
                hihat_volume_adj = 0.5
            elif section.get("type") == "verse":
                kick_volume_adj = 0.8
                snare_volume_adj = 0.8
                hihat_volume_adj = 0.3
            elif section.get("type") == "intro":
                kick_volume_adj = 0.5
                snare_volume_adj = 0.3
                hihat_volume_adj = 0.4
            else:
                kick_volume_adj = 0.8
                snare_volume_adj = 0.8
                hihat_volume_adj = 0.3

            # 生成每个节拍
            for beat in range(section_beats):
                base_beat_sample = current_sample + beat * beat_samples

                # 如果有downbeat信息，使用真实的节拍网格
                if downbeats and beats:
                    # 找到这个节拍对应的真实时间
                    section_start = section.get("start", 0)
                    beat_time = section_start + (beat * 60.0 / bpm)

                    # 查找最接近的真实节拍位置
                    if beat_time <= max(beats):
                        closest_beat_idx = min(range(len(beats)), key=lambda i: abs(beats[i] - beat_time))
                        beat_position = beat_positions[closest_beat_idx] if beat_positions else (beat % numerator)
                    else:
                        beat_position = beat % numerator
                else:
                    # 没有downbeat信息，使用传统的4/4假设
                    beat_position = beat % 4

                # 根据拍号调整模式映射
                # 核心：将模式的16分音符位置映射到当前拍号
                pattern_multiplier = numerator / 4.0  # 用于不同拍号的缩放

                # Kick
                for kick_pos in pattern.kick_pattern:
                    adjusted_pos = int(kick_pos * pattern_multiplier)
                    hit_sample = base_beat_sample + adjusted_pos * sixteenth_samples
                    if hit_sample < total_samples:
                        self._add_kick(audio, hit_sample, kick_volume * kick_volume_adj)

                # Snare
                for snare_pos in pattern.snare_pattern:
                    adjusted_pos = int(snare_pos * pattern_multiplier)
                    hit_sample = base_beat_sample + adjusted_pos * sixteenth_samples
                    if hit_sample < total_samples:
                        self._add_snare(audio, hit_sample, snare_volume * snare_volume_adj)

                # Hi-hat
                for hihat_pos in pattern.hihat_pattern:
                    adjusted_pos = int(hihat_pos * pattern_multiplier)
                    hit_sample = base_beat_sample + adjusted_pos * sixteenth_samples
                    if hit_sample < total_samples:
                        self._add_hihat(audio, hit_sample, hihat_volume * hihat_volume_adj)

                # 偶尔的fills（在段落结束前2拍）
                if beat >= section_beats - 2 and pattern.complexity > 0.5:
                    if np.random.random() > 0.6:  # 40%概率
                        self._add_fill(audio, base_beat_sample + beat_samples - sixteenth_samples, snare_volume_adj)

            current_sample += int(section_duration * self.sample_rate)

        # 归一化
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio * 0.9 / max_val

        return audio

    def _add_kick(self, audio: np.ndarray, start: int, volume: float):
        """添加底鼓 - 增强低频，瞬态更短促有力"""
        duration = int(0.12 * self.sample_rate)  # 120ms
        end = min(start + duration, len(audio))

        t = np.arange(0, end - start) / self.sample_rate

        # 低频正弦波包络（更有冲击力）
        freq = 60  # 60Hz基础
        freq2 = 40  # 40Hz超低频
        sine1 = np.sin(2 * np.pi * freq * t) * np.exp(-8 * t)
        sine2 = np.sin(2 * np.pi * freq2 * t) * np.exp(-12 * t)

        # 短促的瞬态噪声（增加敲击感）
        transient = np.random.normal(0, 0.2, len(t)) * np.exp(-30 * t)

        # 混合 - 重点强化低频
        signal = (sine1 * 0.8 + sine2 * 0.6 + transient * 0.2) * volume

        audio[start:end] += signal

    def _add_snare(self, audio: np.ndarray, start: int, volume: float):
        """添加军鼓 - 增强中高频，更响亮明亮"""
        duration = int(0.10 * self.sample_rate)  # 100ms - 比kick短
        end = min(start + duration, len(audio))

        t = np.arange(0, end - start) / self.sample_rate

        # 多频段正弦波（军鼓的音高特征）
        sine1 = np.sin(2 * np.pi * 180 * t) * np.exp(-6 * t)   # 180Hz主体
        sine2 = np.sin(2 * np.pi * 330 * t) * np.exp(-10 * t)  # 330Hz泛音

        # 宽带噪声（军鼓的"沙沙"声）
        noise_mid = np.random.normal(0, 0.25, len(t)) * np.exp(-12 * t)  # 中频噪声
        noise_high = np.random.normal(0, 0.15, len(t)) * np.exp(-20 * t) * (t < 0.03)  # 高频瞬态

        # 军鼓应该听起来更明亮、更开阔
        signal = (sine1 * 0.4 + sine2 * 0.3 + noise_mid * 0.9 + noise_high * 0.5) * volume

        audio[start:end] += signal

    def _add_hihat(self, audio: np.ndarray, start: int, volume: float):
        """添加踩镲 - 尖锐、短促的高频"""
        duration = int(0.05 * self.sample_rate)  # 50ms - 非常短
        end = min(start + duration, len(audio))

        t = np.arange(0, end - start) / self.sample_rate

        # 高频噪声（8kHz+）
        noise_high = np.random.normal(0, 0.2, len(t)) * np.exp(-40 * t)

        # 超高频瞬态（增加"叮"的质感）
        noise_ultra = np.random.normal(0, 0.05, len(t)) * (t < 0.01)

        # 快速衰减，非常明亮
        signal = (noise_high * 0.8 + noise_ultra * 0.4) * volume * 0.25

        audio[start:end] += signal

    def _add_fill(self, audio: np.ndarray, start: int, volume: float):
        """添加填充（滚奏或快速音符）"""
        # 简单的滚奏：3个快速军鼓
        for i in range(3):
            pos = start + i * 40  # 40个采样间隔
            if pos < len(audio):
                self._add_snare(audio, pos, volume * 0.7)

    def _save_drums(self, track: GeneratedDrumTrack, output_dir: Path):
        """保存生成的鼓音频"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存纯鼓轨
        drums_path = output_dir / "generated_drums.wav"
        import soundfile as sf
        sf.write(drums_path, track.audio, self.sample_rate)

        # 保存节奏描述
        info_path = output_dir / "rhythm_info.json"
        import json
        with open(info_path, 'w') as f:
            json.dump({
                "bpm": track.bpm,
                "pattern": track.pattern,
                "sections": track.sections
            }, f, indent=2)

        print(f"✅ 鼓轨已保存: {drums_path}")

    def generate_variant(self, base_pattern: DrumPattern, style: str = "light") -> DrumPattern:
        """
        生成现有模式的变体
        """
        new_pattern = DrumPattern(
            name=f"{base_pattern.name}_{style}",
            style=base_pattern.style,
            bpm_range=base_pattern.bpm_range,
            kick_pattern=list(base_pattern.kick_pattern),
            snare_pattern=list(base_pattern.snare_pattern),
            hihat_pattern=list(base_pattern.hihat_pattern),
            complexity=base_pattern.complexity
        )

        if style == "light":
            # 简化
            new_pattern.kick_pattern = new_pattern.kick_pattern[:2]
            new_pattern.hihat_pattern = [p for p in new_pattern.hihat_pattern if p % 2 == 0]
            new_pattern.complexity *= 0.7

        elif style == "heavy":
            # 复杂化
            if len(new_pattern.kick_pattern) < 6:
                new_pattern.kick_pattern.extend([2, 6, 10])
            new_pattern.complexity = min(1.0, new_pattern.complexity * 1.3)

        return new_pattern
