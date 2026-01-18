"""
段落检测器 - 高级结构边界识别

使用多特征融合方法精确检测歌曲段落变化。
"""

import numpy as np
import librosa
from typing import List, Dict, Tuple
from dataclasses import dataclass
import warnings

warnings.filterwarnings("ignore")


@dataclass
class Section:
    """段落数据类"""
    type: str
    start: float
    end: float
    confidence: float
    features: Dict


class StructureDetector:
    """结构检测器"""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.section_types = ["intro", "verse", "chorus", "bridge", "solo", "outro"]

    def detect(self, audio: np.ndarray, sr: int, bpm: int = None) -> List[Section]:
        """
        检测歌曲结构段落

        Args:
            audio: 音频数据 (单声道)
            sr: 采样率
            bpm: 可选的已知BPM

        Returns:
            段落列表
        """
        # 1. 提取多维度特征
        features = self._extract_features(audio, sr)

        # 2. 检测边界
        boundaries = self._detect_boundaries(features, audio, sr)

        # 3. 聚合小段落
        boundaries = self._merge_short_sections(boundaries, min_duration=8.0)

        # 4. 分类段落类型
        sections = self._classify_sections(boundaries, features, audio, sr, bpm)

        # 5. 计算置信度
        sections = self._calculate_confidence(sections, features)

        return sections

    def _extract_features(self, audio: np.ndarray, sr: int) -> Dict:
        """
        提取多维度特征用于边界检测
        """
        hop_length = 512
        frame_length = 2048

        # 1. 能量特征
        rms = librosa.feature.rms(
            y=audio, hop_length=hop_length, frame_length=frame_length
        )[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

        # 2. 频谱特征
        spec_cent = librosa.feature.spectral_centroid(
            y=audio, sr=sr, hop_length=hop_length
        )[0]
        spec_bw = librosa.feature.spectral_bandwidth(
            y=audio, sr=sr, hop_length=hop_length
        )[0]
        spec_roll = librosa.feature.spectral_rolloff(
            y=audio, sr=sr, hop_length=hop_length
        )[0]

        # 3. 色彩特征
        chroma = librosa.feature.chroma_cens(
            y=audio, sr=sr, hop_length=hop_length
        )

        # 4. 节奏特征
        onset_env = librosa.onset.onset_strength(
            y=audio, sr=sr, hop_length=hop_length
        )

        # 5. MFCC
        mfcc = librosa.feature.mfcc(
            y=audio, sr=sr, hop_length=hop_length, n_mfcc=13
        )

        return {
            "rms_db": rms_db,
            "spec_cent": spec_cent,
            "spec_bw": spec_bw,
            "spec_roll": spec_roll,
            "chroma": chroma,
            "onset": onset_env,
            "mfcc": mfcc,
            "hop_length": hop_length,
        }

    def _detect_boundaries(self, features: Dict, audio: np.ndarray, sr: int) -> List[Tuple[float, float]]:
        """
        使用多特征融合检测边界
        """
        rms_db = features["rms_db"]
        spec_cent = features["spec_cent"]
        onset = features["onset"]
        chroma = features["chroma"]
        hop_length = features["hop_length"]

        # 1. 能量变化
        energy_change = np.abs(np.diff(rms_db))
        energy_peaks = self._find_peaks(energy_change, sensitivity=0.3)

        # 2. 频谱中心变化
        centroid_change = np.abs(np.diff(spec_cent))
        centroid_peaks = self._find_peaks(centroid_change, sensitivity=0.2)

        # 3. 起音强度变化
        onset_change = np.abs(np.diff(onset))
        onset_peaks = self._find_peaks(onset_change, sensitivity=0.4)

        # 4. 和声变化（色度）
        chroma_change = []
        for i in range(1, chroma.shape[1]):
            diff = np.sum(np.abs(chroma[:, i] - chroma[:, i-1]))
            chroma_change.append(diff)
        chroma_change = np.array(chroma_change)
        chroma_peaks = self._find_peaks(chroma_change, sensitivity=0.3)

        # 融合所有边界
        all_peaks = {}
        for peaks in [energy_peaks, centroid_peaks, onset_peaks, chroma_peaks]:
            for p in peaks:
                all_peaks[p] = all_peaks.get(p, 0) + 1

        # 选择至少2个特征一致的边界
        threshold = 2
        selected_peaks = [p for p, count in all_peaks.items() if count >= threshold]

        # 转换为时间
        boundary_times = librosa.frames_to_time(selected_peaks, sr=sr, hop_length=hop_length)

        # 添加起点和终点
        total_duration = len(audio) / sr
        all_boundaries = sorted([0.0] + list(boundary_times) + [total_duration])

        # 合并邻近边界（< 2秒）
        merged = []
        current_start = all_boundaries[0]

        for i in range(1, len(all_boundaries)):
            if all_boundaries[i] - current_start >= 2.0:
                merged.append((current_start, all_boundaries[i]))
                current_start = all_boundaries[i]

        return merged

    def _find_peaks(self, signal: np.ndarray, sensitivity: float = 0.3) -> List[int]:
        """
        寻找信号峰值
        """
        if len(signal) == 0:
            return []

        threshold = np.percentile(signal, 100 * (1 - sensitivity))
        peaks = np.where(signal > threshold)[0]

        # 过滤密集峰值
        filtered_peaks = []
        min_distance = 5  # 帧数
        last_peak = -min_distance

        for peak in peaks:
            if peak - last_peak >= min_distance:
                filtered_peaks.append(peak)
                last_peak = peak

        return filtered_peaks

    def _merge_short_sections(self, boundaries: List[Tuple[float, float]], min_duration: float = 8.0) -> List[Tuple[float, float]]:
        """合并过短的段落"""
        if len(boundaries) <= 1:
            return boundaries

        merged = []
        current = boundaries[0]

        for i in range(1, len(boundaries)):
            start, end = current
            next_start, next_end = boundaries[i]

            if end - start < min_duration:
                # 合并
                current = (start, next_end)
            else:
                merged.append(current)
                current = boundaries[i]

        merged.append(current)
        return merged

    def _classify_sections(self, boundaries: List[Tuple[float, float]], features: Dict,
                          audio: np.ndarray, sr: int, bpm: int = None) -> List[Section]:
        """
        为每个段落分类类型
        """
        sections = []

        for i, (start, end) in enumerate(boundaries):
            duration = end - start

            # 提取段落音频
            start_sample = int(start * sr)
            end_sample = int(end * sr)
            section_audio = audio[start_sample:end_sample]

            # 提取段落特征
            section_features = self._extract_section_features(section_audio, sr, features, start, end)

            # 分类逻辑
            section_type = self._classify_single_section(section_features, duration, i, len(boundaries))

            sections.append(Section(
                type=section_type,
                start=start,
                end=end,
                confidence=0.0,  # 后续计算
                features=section_features
            ))

        return sections

    def _extract_section_features(self, section_audio: np.ndarray, sr: int,
                                 all_features: Dict, start: float, end: float) -> Dict:
        """提取单个段落的特征"""
        # 能量
        rms_db = np.mean(all_features["rms_db"])

        # 频谱中心
        spec_cent = np.mean(all_features["spec_cent"])

        # 和声复杂度
        chroma = all_features["chroma"]
        chroma_entropy = -np.sum(chroma * np.log(chroma + 1e-8))

        # 起音密度
        onset = all_features["onset"]
        onset_density = np.sum(onset) / (end - start + 1e-6)

        # MFCC
        mfcc = all_features["mfcc"]
        mfcc_var = np.mean(np.std(mfcc, axis=1))

        return {
            "energy": rms_db,
            "brightness": spec_cent,
            "harmonic_complexity": chroma_entropy,
            "onset_density": onset_density,
            "timbre_variability": mfcc_var,
            "duration": end - start,
        }

    def _classify_single_section(self, features: Dict, duration: float,
                                index: int, total: int) -> str:
        """
        基于特征对单个段落进行分类
        """
        # 基于位置
        if index == 0:
            if duration < 15:
                return "intro"
            elif duration < 30:
                return "intro"

        if index == total - 1:
            if duration < 15:
                return "outro"

        # 基于能量和特征
        energy = features["energy"]
        onset_density = features["onset_density"]
        brightness = features["brightness"]
        duration_norm = features["duration"]

        # 详细规则
        if energy < -30 and onset_density < 0.1:
            return "intro"

        elif onset_density > 0.35 and energy > -18:
            return "chorus"

        elif onset_density < 0.2 and duration_norm > 20:
            return "verse"

        elif brightness > 4000 and duration_norm < 20:
            return "bridge"

        elif features["timbre_variability"] > 15:
            return "solo"

        # 默认
        return "verse"

    def _calculate_confidence(self, sections: List[Section], features: Dict) -> List[Section]:
        """
        计算每个段落的置信度
        """
        for section in sections:
            score = 0.5  # 基础值

            # 边界清晰度
            boundary_strength = self._get_boundary_strength(section, features)
            score += boundary_strength * 0.2

            # 持续时间合理性
            if 8 <= section.features["duration"] <= 60:
                score += 0.15

            # 特征一致性
            if section.type in ["chorus", "verse"]:
                if section.features["onset_density"] > 0.25:
                    score += 0.1

            section.confidence = min(0.95, score)

        return sections

    def _get_boundary_strength(self, section: Section, features: Dict) -> float:
        """计算边界强度"""
        # 这里简化实现，实际应该检查前后特征变化
        return 0.3

    def get_section_summary(self, sections: List[Section]) -> Dict:
        """生成段落总结"""
        summary = {
            "total_sections": len(sections),
            "types": {},
            "duration": sum(s.features["duration"] for s in sections),
            "sections": []
        }

        for section in sections:
            summary["types"][section.type] = summary["types"].get(section.type, 0) + 1
            summary["sections"].append({
                "type": section.type,
                "start": round(section.start, 2),
                "end": round(section.end, 2),
                "duration": round(section.features["duration"], 2),
                "confidence": round(section.confidence, 2),
                "energy": round(section.features["energy"], 1),
            })

        return summary
