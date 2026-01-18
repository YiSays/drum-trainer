"""
音乐结构分析器 V2 - 包含完整的节拍检测（拍号、downbeat）

基于 librosa + rhythm_detector
"""

import numpy as np
import librosa
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import warnings

from .rhythm_detector import RhythmDetector, BeatInfo, TimeSignature

warnings.filterwarnings("ignore")


class MusicAnalyzerV2:
    """增强的音乐分析器 - 包含节拍检测"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.audio_io = None
        self.rhythm_detector = RhythmDetector(sample_rate)

    def _ensure_audio_io(self):
        """延迟导入 AudioIO"""
        if self.audio_io is None:
            from .audio_io import AudioIO
            self.audio_io = AudioIO(self.sample_rate)

    def analyze(self, audio_path: str | Path) -> Dict:
        """
        完整的音乐分析（V2 - 包含节拍检测）

        Returns:
            {
                "style": "rock",
                "bpm": 128,
                "energy": 0.8,
                "structure": [...],
                "rhythm_profile": {...},
                "key": "C",
                "mood": "energetic",
                "time_signature": {"numerator": 4, "denominator": 4, "confidence": 0.8},
                "downbeats": [0.0, 2.1, 4.2, ...],
                "beats": [0.0, 0.525, 1.05, ...],
                "beat_positions": [0, 1, 2, 3, 0, 1, ...]
            }
        """
        self._ensure_audio_io()

        print("📊 开始音乐分析 V2...")

        # 加载音频
        audio, sr = self.audio_io.load_audio(audio_path)
        mono = self.audio_io.to_mono(audio)

        results = {}

        # 1. BPM 检测 (最高优先级)
        results["bpm"] = self.detect_bpm(mono, sr)

        # 2. 节拍检测（拍号、downbeat、节拍位置）
        beat_info = self.rhythm_detector.detect_rhythm_info(mono, sr)

        results["time_signature"] = {
            "numerator": beat_info.time_signature.numerator,
            "denominator": beat_info.time_signature.denominator,
            "confidence": beat_info.time_signature.confidence
        }
        results["downbeats"] = beat_info.downbeats
        results["beats"] = beat_info.beats
        results["beat_positions"] = beat_info.beat_positions

        # 3. 风格识别
        results["style"] = self.detect_style(mono, sr, results["bpm"])

        # 4. 段落结构检测（使用新的智能分类）
        results["structure"] = self.detect_structure(mono, sr)

        # 5. 节奏特征
        results["rhythm_profile"] = self.analyze_rhythm(mono, sr, results["bpm"])

        # 6. 能量分析
        results["energy"] = self.analyze_energy(mono, sr)

        # 7. 键/调性检测
        results["key"] = self.detect_key(mono, sr)

        # 8. 情绪分析
        results["mood"] = self.analyze_mood(
            results["style"],
            results["energy"],
            results["bpm"]
        )

        return results

    def detect_bpm(self, audio: np.ndarray, sr: int) -> int:
        """检测 BPM - 多算法融合"""
        # 方法1: Librosa
        tempo1, _ = librosa.beat.beat_track(y=audio, sr=sr, start_bpm=120)

        # 方法2: 基于起音
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        tempo2, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)

        # 取中位数
        bpms = [tempo1, tempo2]
        bpm = int(np.median(bpms))

        # 修正双倍/一半
        if bpm > 140:
            bpm = bpm // 2
        elif bpm < 60:
            bpm = bpm * 2

        return max(60, min(200, bpm))

    def detect_style(self, audio: np.ndarray, sr: int, bpm: int) -> str:
        """风格识别"""
        # 提取特征
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)

        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_var = np.std(onset_env)
        onset_mean = np.mean(onset_env)

        contrast = librosa.feature.spectral_contrast(y=audio, sr=sr)
        contrast_mean = np.mean(contrast, axis=1)

        # 基于 BPM 和特征的分类
        if 60 <= bpm <= 90:
            return "jazz" if onset_mean < 0.3 else "ballad"

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
        """段落结构检测 - 使用智能分类"""
        # 计算特征
        hop_length = 512
        frame_length = 2048

        rms = librosa.feature.rms(y=audio, hop_length=hop_length, frame_length=frame_length)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

        spec_cent = librosa.feature.spectral_centroid(y=audio, sr=sr, hop_length=hop_length)[0]

        onset_env = librosa.onset.onset_strength(y=audio, sr=sr, hop_length=hop_length)

        contrast = librosa.feature.spectral_contrast(y=audio, sr=sr, hop_length=hop_length)
        contrast_change = np.abs(np.diff(np.mean(contrast, axis=0)))

        # 融合变化分数
        energy_change = np.abs(np.diff(rms_db))
        centroid_change = np.abs(np.diff(spec_cent))
        onset_change = np.abs(np.diff(onset_env))

        total_change = (
            energy_change * 0.25 +
            centroid_change * 0.3 +
            onset_change * 0.35 +
            contrast_change * 0.1
        )

        # 检测边界
        threshold = np.percentile(total_change, 92)
        boundary_frames = np.where(total_change > threshold)[0]
        boundary_times = librosa.frames_to_time(boundary_frames, sr=sr, hop_length=hop_length)

        # 合并邻近边界
        merged_boundaries = []
        min_gap = 4.0

        if len(boundary_times) > 0:
            merged_boundaries.append(boundary_times[0])
            for t in boundary_times[1:]:
                if t - merged_boundaries[-1] > min_gap:
                    merged_boundaries.append(t)

        # 添加起点和终点
        total_duration = len(audio) / sr
        all_boundaries = [0.0] + merged_boundaries + [total_duration]

        # 段落过多时合并
        if len(all_boundaries) - 1 > 10:
            while len(all_boundaries) - 1 > 8:
                min_idx = -1
                min_duration = float('inf')
                for i in range(1, len(all_boundaries) - 1):
                    duration = all_boundaries[i] - all_boundaries[i-1]
                    if duration < min_duration:
                        min_duration = duration
                        min_idx = i
                if min_idx > 0:
                    all_boundaries.pop(min_idx)

        # 分类每个段落
        structure = []
        total_sections = len(all_boundaries) - 1

        for i in range(total_sections):
            start = all_boundaries[i]
            end = all_boundaries[i + 1]
            duration = end - start

            section_audio = audio[int(start*sr):int(end*sr)]
            if len(section_audio) == 0:
                continue

            # 特征提取
            section_rms = librosa.feature.rms(y=section_audio)[0]
            section_energy = np.mean(section_rms)
            section_energy_std = np.std(section_rms)

            section_onset = librosa.onset.onset_strength(y=section_audio, sr=sr)
            section_onset_density = len(section_onset[section_onset > np.mean(section_onset)]) / len(section_audio) * sr

            section_cent = librosa.feature.spectral_centroid(y=section_audio, sr=sr)[0]
            section_brightness = np.mean(section_cent)

            # 智能分类
            section_type = self._classify_section_smart(
                i, total_sections, duration, section_energy,
                section_onset_density, section_brightness, section_energy_std
            )

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
        """智能段落分类"""
        # 基于位置的规则
        if index == 0:
            if duration < 20 and energy < 0.05:
                return "intro"
            elif duration < 15:
                return "intro"

        if index == total - 1:
            if duration < 20 and (energy < 0.05 or onset_density < 0.15):
                return "outro"
            elif duration < 15:
                return "outro"

        # 基于能量和密度的规则
        if energy > 0.08 and onset_density > 0.25:
            return "chorus"

        if energy > 0.1 and energy_std > 0.02:
            return "chorus"

        if 0.04 <= energy <= 0.08 and onset_density < 0.25:
            return "verse"

        if energy < 0.08 and duration > 25:
            return "verse"

        if brightness > 3500 and duration < 25:
            return "bridge"

        if energy < 0.04:
            return "intro" if index < total / 2 else "outro"

        # 位置和能量的综合
        if index < total / 2:
            return "chorus" if energy > 0.06 else "verse"
        else:
            if energy > 0.07:
                return "chorus"
            elif brightness > 3000:
                return "bridge"
            else:
                return "verse"

        return "verse"

    def analyze_rhythm(self, audio: np.ndarray, sr: int, bpm: int) -> Dict:
        """节奏特征分析"""
        tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)

        if len(beat_frames) < 4:
            return {"pattern": "unknown", "complexity": 0.0}

        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        intervals = np.diff(beat_times)

        stability = 1.0 / (np.std(intervals) + 1e-6)

        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_peaks = librosa.util.peak_pick(
            onset_env,
            pre_max=20, post_max=20,
            pre_avg=20, post_avg=20,
            delta=0.1, wait=10
        )

        if stability > 0.8:
            pattern = "straight"
        elif stability > 0.6:
            pattern = "swing"
        else:
            pattern = "irregular"

        complexity = min(1.0, len(onset_peaks) / (len(beat_frames) * 2))

        return {
            "pattern": pattern,
            "stability": round(stability, 3),
            "complexity": round(complexity, 3),
            "beat_count": len(beat_frames),
            "onset_density": len(onset_peaks) / (len(audio) / sr)
        }

    def analyze_energy(self, audio: np.ndarray, sr: int) -> float:
        """整体能量水平"""
        rms = librosa.feature.rms(y=audio)[0]
        return float(np.mean(rms))

    def detect_key(self, audio: np.ndarray, sr: int) -> str:
        """调性检测"""
        try:
            chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
            chroma_vals = np.sum(chroma, axis=1)
            pitch_class = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key_index = np.argmax(chroma_vals)
            return pitch_class[key_index]
        except:
            return "C"

    def analyze_mood(self, style: str, energy: float, bpm: int) -> str:
        """情绪分析"""
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
