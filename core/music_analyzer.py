"""
音乐结构分析模块 - 风格/BPM/段落/节奏分析

使用 Essentia 和 Librosa 进行专业音乐分析。
"""

import numpy as np
import librosa
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

try:
    import essentia.standard as es
    ESSENTIA_AVAILABLE = True
except ImportError:
    ESSENTIA_AVAILABLE = False
    print("⚠️  Essentia 未安装，部分功能受限")

try:
    import madmom
    MADMOM_AVAILABLE = True
except ImportError:
    MADMOM_AVAILABLE = False
    print("⚠️  Madmom 未安装，部分节奏分析受限")


class MusicAnalyzer:
    """音乐结构与风格分析器"""

    def __init__(self, sample_rate: int = 44100):
        """
        初始化分析器

        Args:
            sample_rate: 采样率
        """
        self.sample_rate = sample_rate
        self.audio_io = None  # 延迟导入避免循环依赖

    def _ensure_audio_io(self):
        """延迟导入 AudioIO"""
        if self.audio_io is None:
            from .audio_io import AudioIO
            self.audio_io = AudioIO(self.sample_rate)

    def analyze(self, audio_path: str | Path) -> Dict:
        """
        完整的音乐分析

        Returns:
            {
                "style": "rock",           # 风格
                "bpm": 128,                # 节奏
                "energy": 0.8,             # 能量水平
                "structure": [...],        # 段落结构
                "rhythm_profile": {...},   # 节奏特征
                "key": "C",                # 调性
                "mood": "energetic"        # 情绪
            }
        """
        self._ensure_audio_io()

        print("📊 开始音乐分析...")

        # 加载音频
        audio, sr = self.audio_io.load_audio(audio_path)
        mono = self.audio_io.to_mono(audio)

        results = {}

        # 1. BPM 检测 (最高优先级)
        results["bpm"] = self.detect_bpm(mono, sr)

        # 2. 风格识别
        results["style"] = self.detect_style(mono, sr, results["bpm"])

        # 3. 段落结构检测
        results["structure"] = self.detect_structure(mono, sr)

        # 4. 节奏特征
        results["rhythm_profile"] = self.analyze_rhythm(mono, sr, results["bpm"])

        # 5. 能量分析
        results["energy"] = self.analyze_energy(mono, sr)

        # 6. 键/调性检测
        results["key"] = self.detect_key(mono, sr)

        # 7. 情绪分析
        results["mood"] = self.analyze_mood(
            results["style"],
            results["energy"],
            results["bpm"]
        )

        return results

    def detect_bpm(self, audio: np.ndarray, sr: int) -> int:
        """
        检测 BPM - 多算法融合提高准确性

        优先级：
        1. Madmom (如果有) - 最准确
        2. Librosa 多算法投票
        3. Essentia
        """
        if MADMOM_AVAILABLE:
            try:
                # 使用 madmom 的高级 BPM 检测
                from madmom.features.beats import RNNBeatProcessor, DBNBeatTracker

                proc = RNNBeatProcessor()
                activations = proc(audio)
                tracker = DBNBeatTracker()
                beats = tracker(activations)

                if len(beats) > 1:
                    intervals = np.diff(beats)
                    bpm = int(60.0 / np.median(intervals))
                    return max(60, min(200, bpm))
            except:
                pass

        # Librosa 多算法投票
        try:
            # 方法1: 恒定Q变换
            tempo1, _ = librosa.beat.beat_track(
                y=audio, sr=sr, start_bpm=120
            )

            # 方法2: 强制节奏
            tempo2, _ = librosa.beat.beat_track(
                y=audio, sr=sr, units='time',
                start_bpm=120
            )

            # 方法3: 谐波节奏
            onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
            tempo3, _ = librosa.beat.beat_track(
                onset_envelope=onset_env, sr=sr
            )

            # 取中位数，并四舍五入到最接近的整数
            bpms = [tempo1, tempo2, tempo3]
            bpm = int(np.median(bpms))

            # 修正双倍/一半
            if bpm > 140:
                bpm = bpm // 2
            elif bpm < 70:
                bpm = bpm * 2

            return max(60, min(200, bpm))

        except Exception as e:
            print(f"BPM 检测警告: {e}")
            return 120  # 默认值

    def detect_style(self, audio: np.ndarray, sr: int, bpm: int) -> str:
        """
        风格识别 - 基于节奏模式和频谱特征

        Returns:
            风格字符串: rock, jazz, pop, electronic, hip_hop, funk, country
        """
        # 提取 MFCC 特征
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)

        # 提取节拍强度特征
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_var = np.std(onset_env)
        onset_mean = np.mean(onset_env)

        # 频谱对比度
        contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
        contrast_mean = np.mean(contrast, axis=1)

        # 节奏密度分析
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
        if len(beat_frames) > 1:
            beat_intervals = np.diff(beat_frames)
            beat_regularity = 1.0 / (np.std(beat_intervals) + 1e-6)
        else:
            beat_regularity = 0.5

        # 基于 BPM 和特征的规则分类
        if 60 <= bpm <= 90:
            if beat_regularity > 0.8 and onset_mean < 0.3:
                return "jazz"
            return "ballad"

        elif 90 <= bpm <= 120:
            if onset_var > 0.4:
                return "funk"
            if contrast_mean[0] > 30:
                return "pop"
            return "country"

        elif 120 <= bpm <= 140:
            if onset_mean > 0.5 and onset_var > 0.5:
                return "rock"
            if onset_var < 0.2:
                return "pop"
            return "reggae"

        elif 140 <= bpm <= 180:
            if contrast_mean[1] > 40:
                return "electronic"
            if onset_mean > 0.6:
                return "hip_hop"
            return "punk"

        else:
            return "electronic"

    def detect_structure(self, audio: np.ndarray, sr: int) -> List[Dict]:
        """
        段落结构检测 - 识别 Intro/Verse/Chorus/Bridge/Outro

        使用能量变化、频谱变化和节拍强度检测边界，结合智能分类
        """
        # 计算能量包络
        hop_length = 512
        frame_length = 2048

        # 1. 能量变化（RMS）
        rms = librosa.feature.rms(
            y=audio, hop_length=hop_length, frame_length=frame_length
        )[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

        # 2. 频谱中心变化
        spec_cent = librosa.feature.spectral_centroid(
            y=audio, sr=sr, hop_length=hop_length
        )[0]

        # 3. 节奏强度变化（起音）
        onset_env = librosa.onset.onset_strength(
            y=audio, sr=sr, hop_length=hop_length
        )

        # 4. 频谱对比度（区分度）
        contrast = librosa.feature.spectral_contrast(
            y=audio, sr=sr, hop_length=hop_length
        )
        contrast_change = np.abs(np.diff(np.mean(contrast, axis=0)))

        # 融合特征用于边界检测
        energy_change = np.abs(np.diff(rms_db))
        centroid_change = np.abs(np.diff(spec_cent))
        onset_change = np.abs(np.diff(onset_env))

        # 综合变化分数 - 降低能量变化的权重，避免过度分割
        total_change = (
            energy_change * 0.25 +      # 降低能量权重
            centroid_change * 0.3 +
            onset_change * 0.35 +       # 增加起音权重
            contrast_change * 0.1
        )

        # 寻找显著边界 - 使用更严格的阈值
        threshold = np.percentile(total_change, 92)  # 从85提高到92
        boundary_frames = np.where(total_change > threshold)[0]

        # 转换为时间
        boundary_times = librosa.frames_to_time(boundary_frames, sr=sr, hop_length=hop_length)

        # 合并邻近边界
        merged_boundaries = []
        min_gap = 4.0  # 增加最小间隔到4秒，减少过度分割

        if len(boundary_times) > 0:
            merged_boundaries.append(boundary_times[0])
            for t in boundary_times[1:]:
                if t - merged_boundaries[-1] > min_gap:
                    merged_boundaries.append(t)

        # 添加起点和终点
        total_duration = len(audio) / sr
        all_boundaries = [0.0] + merged_boundaries + [total_duration]

        # 如果段落过多（>10个），说明检测过于敏感，合并相邻短段落
        if len(all_boundaries) - 1 > 10:
            # 重新合并，目标是5-8个段落
            while len(all_boundaries) - 1 > 8:
                # 找到最短的相邻段落对
                min_idx = -1
                min_duration = float('inf')

                for i in range(1, len(all_boundaries) - 1):
                    duration = all_boundaries[i] - all_boundaries[i-1]
                    if duration < min_duration:
                        min_duration = duration
                        min_idx = i

                if min_idx > 0:
                    # 合并这个段落
                    all_boundaries.pop(min_idx)

        # 为每个段落分配类型
        structure = []
        total_sections = len(all_boundaries) - 1

        for i in range(total_sections):
            start = all_boundaries[i]
            end = all_boundaries[i + 1]
            duration = end - start

            # 计算该段落的音频特征
            section_audio = audio[int(start*sr):int(end*sr)]
            if len(section_audio) == 0:
                continue

            # 提取特征
            section_rms = librosa.feature.rms(y=section_audio)[0]
            section_energy = np.mean(section_rms)
            section_energy_std = np.std(section_rms)

            section_onset = librosa.onset.onset_strength(y=section_audio, sr=sr)
            section_onset_density = len(section_onset[section_onset > np.mean(section_onset)]) / len(section_audio) * sr

            section_cent = librosa.feature.spectral_centroid(y=section_audio, sr=sr)[0]
            section_brightness = np.mean(section_cent)

            # 智能分类逻辑
            section_type = self._classify_section_smart(
                i, total_sections, duration, section_energy,
                section_onset_density, section_brightness, section_energy_std
            )

            # 节奏复杂度
            section_rhythm = "complex" if (section_onset_density > 0.25 or section_energy > 0.08) else "simple"

            structure.append({
                "type": section_type,
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
                "rhythm": section_rhythm
            })

        return structure

    def _classify_section_smart(self, index: int, total: int, duration: float,
                                energy: float, onset_density: float,
                                brightness: float, energy_std: float) -> str:
        """
        智能段落分类 - 避免循环分配，使用特征决策树

        决策规则：
        1. 基于位置（开始/结束）
        2. 基于能量（高=chorus/verse，低=intro/outro）
        3. 基于密度（高=chorus，低=verse/intro）
        4. 基于持续时间
        """
        # 1. 基于位置的规则
        if index == 0:
            # 第一个段落
            if duration < 20 and energy < 0.05:
                return "intro"
            elif duration < 15:
                return "intro"

        if index == total - 1:
            # 最后一个段落
            if duration < 20 and (energy < 0.05 or onset_density < 0.15):
                return "outro"
            elif duration < 15:
                return "outro"

        # 2. 基于能量和密度的规则
        # Chorus: 高能量 + 高密度
        if energy > 0.08 and onset_density > 0.25:
            return "chorus"

        if energy > 0.1 and energy_std > 0.02:
            return "chorus"

        # Verse: 中等能量 + 较低密度
        if 0.04 <= energy <= 0.08 and onset_density < 0.25:
            return "verse"

        if energy < 0.08 and duration > 25:
            return "verse"

        # Bridge: 高亮度 + 短时长
        if brightness > 3500 and duration < 25:
            return "bridge"

        # 再次检查 Intro/Outro 基于低能量
        if energy < 0.04:
            if index < total / 2:
                return "intro"
            else:
                return "outro"

        # 3. 位置和能量的综合规则
        if index < total / 2:
            # 前半段
            if energy > 0.06:
                return "chorus"
            else:
                return "verse"
        else:
            # 后半段
            if energy > 0.07:
                return "chorus"
            elif brightness > 3000:
                return "bridge"
            else:
                return "verse"

        # 默认（不应该到达这里，但保持安全）
        return "verse"

    def analyze_rhythm(self, audio: np.ndarray, sr: int, bpm: int) -> Dict:
        """
        节奏特征分析 - 识别主节奏型

        Returns:
            节奏特征字典
        """
        # 计算节拍位置
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)

        if len(beat_frames) < 4:
            return {"pattern": "unknown", "complexity": 0.0}

        # 节奏间隔分析
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        intervals = np.diff(beat_times)

        # 节奏稳定性
        stability = 1.0 / (np.std(intervals) + 1e-6)

        # 强拍模式（基于能量）
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_peaks = librosa.util.peak_pick(
            onset_env,
            pre_max=20, post_max=20,
            pre_avg=20, post_avg=20,
            delta=0.1, wait=10
        )

        # 确定主要节奏型
        if stability > 0.8:
            pattern = "straight"  # 直拍
        elif stability > 0.6:
            pattern = "swing"     # 摇摆
        else:
            pattern = "irregular" # 不规则

        # 复杂度评估
        complexity = min(1.0, len(onset_peaks) / (len(beat_frames) * 2))

        return {
            "pattern": pattern,
            "stability": round(stability, 3),
            "complexity": round(complexity, 3),
            "beat_count": len(beat_frames),
            "onset_density": len(onset_peaks) / (len(audio) / sr)  # 每秒音符数
        }

    def analyze_energy(self, audio: np.ndarray, sr: int) -> float:
        """整体能量水平分析"""
        rms = librosa.feature.rms(y=audio)[0]
        return float(np.mean(rms))

    def detect_key(self, audio: np.ndarray, sr: int) -> str:
        """
        调性检测

        Returns:
            键字符串: C, G, D, A, E, B, F#, F, Bb, Eb, Ab, Db, Gb
        """
        try:
            if ESSENTIA_AVAILABLE:
                # Essentia 提供更准确的调性检测
                loader = es.MonoLoader(sampleRate=sr)
                loader(audio.tobytes())  # 需要转换
                key_extractor = es.KeyExtractor()
                key, _, _ = key_extractor(audio)
                return str(key)

            # Librosa 备选
            chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
            chroma_vals = np.sum(chroma, axis=1)
            pitch_class = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key_index = np.argmax(chroma_vals)
            return pitch_class[key_index]

        except:
            return "C"  # 默认

    def analyze_mood(self, style: str, energy: float, bpm: int) -> str:
        """
        情绪分析 - 基于风格、能量和节奏

        Returns:
            情绪描述
        """
        mood_map = {
            "rock": ["energetic", "aggressive", "powerful"],
            "jazz": ["relaxed", "sophisticated", "smooth"],
            "pop": ["upbeat", "catchy", "happy"],
            "electronic": ["dance", "energetic", "futuristic"],
            "hip_hop": ["groovy", "confident", "cool"],
            "funk": ["funky", "danceable", "fun"],
            "ballad": ["emotional", "slow", "romantic"],
            "country": ["warm", "storytelling", "nostalgic"],
            "punk": ["aggressive", "energetic", "raw"],
            "reggae": ["chill", "positive", "laid-back"]
        }

        if style in mood_map:
            moods = mood_map[style]

            # 根据能量和BPM调整
            if energy < 0.15:
                return moods[0] if style != "jazz" else "relaxed"
            elif energy > 0.35:
                if bpm > 140:
                    return "intense"
                else:
                    return moods[1] if len(moods) > 1 else moods[0]
            else:
                return moods[0]
        else:
            return "neutral"
