"""
音频处理模块 - 支持 Apple Silicon 优化

处理音频文件的加载、保存和格式转换。
"""

import librosa
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Tuple, Optional
import warnings

# 忽略不必要的警告
warnings.filterwarnings("ignore")


class AudioIO:
    """音频输入/输出处理类"""

    def __init__(self, sample_rate: int = 44100):
        """
        初始化音频处理器

        Args:
            sample_rate: 目标采样率 (Hz)
        """
        self.sample_rate = sample_rate

    def load_audio(self, file_path: str | Path) -> Tuple[np.ndarray, int]:
        """
        加载音频文件

        Args:
            file_path: 音频文件路径

        Returns:
            Tuple[音频数据, 实际采样率]
        """
        file_path = str(file_path)

        try:
            # 使用 librosa 加载，自动重采样到目标采样率
            audio, sr = librosa.load(
                file_path,
                sr=self.sample_rate,  # 自动重采样
                mono=False,           # 保留立体声
                dtype=np.float32      # 优化内存使用
            )

            # 确保是 2D 数组 (channels, samples)
            if audio.ndim == 1:
                audio = audio[np.newaxis, :]

            return audio, sr

        except Exception as e:
            raise RuntimeError(f"加载音频文件失败: {e}")

    def save_audio(self, audio: np.ndarray, file_path: str | Path,
                   sr: Optional[int] = None) -> None:
        """
        保存音频文件

        Args:
            audio: 音频数据 (channels, samples)
            file_path: 保存路径
            sr: 采样率 (默认使用初始化值)
        """
        file_path = str(file_path)
        sr = sr or self.sample_rate

        # 确保目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        # 转换为适合保存的格式
        # 确保音频是 2D: (channels, samples) 或 (samples, channels)
        if audio.ndim == 1:
            # 单声道 -> (samples,)
            sf.write(file_path, audio, sr, subtype='PCM_16')
        elif audio.ndim == 2:
            # 检查形状
            if audio.shape[0] == 2 or audio.shape[1] == 2:
                # 立体声
                if audio.shape[0] == 2:
                    # (2, samples) -> (samples, 2)
                    sf.write(file_path, audio.T, sr, subtype='PCM_16')
                else:
                    # (samples, 2)
                    sf.write(file_path, audio, sr, subtype='PCM_16')
            else:
                # 多声道，转置为 (samples, channels)
                if audio.shape[0] > audio.shape[1]:
                    sf.write(file_path, audio.T, sr, subtype='PCM_16')
                else:
                    sf.write(file_path, audio, sr, subtype='PCM_16')
        else:
            raise ValueError(f"不支持的音频维度: {audio.shape}")

    def to_stereo(self, audio: np.ndarray) -> np.ndarray:
        """转换为立体声（如果单声道则复制）"""
        if audio.ndim == 1:
            return np.stack([audio, audio])
        elif audio.shape[0] == 1:
            return np.repeat(audio, 2, axis=0)
        return audio

    def to_mono(self, audio: np.ndarray) -> np.ndarray:
        """转换为单声道"""
        if audio.ndim == 1:
            return audio
        if audio.shape[0] == 2:
            # 立体声转单声道：取平均值
            return np.mean(audio, axis=0)
        # 多声道转单声道
        return np.mean(audio, axis=0)

    def get_duration(self, audio: np.ndarray, sr: int) -> float:
        """获取音频时长（秒）"""
        return audio.shape[-1] / sr

    def normalize(self, audio: np.ndarray, headroom: float = 0.1) -> np.ndarray:
        """
        归一化音频，防止削波

        Args:
            audio: 音频数据
            headroom: 保留的头部空间 (0.0-1.0)

        Returns:
            归一化后的音频
        """
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            return audio * (0.9 - headroom) / max_val
        return audio

    def split_long_audio(self, audio: np.ndarray, sr: int,
                         chunk_duration: float = 60.0) -> list[tuple[int, int]]:
        """
        将长音频分割为多个片段

        Args:
            audio: 音频数据
            sr: 采样率
            chunk_duration: 每个片段的时长（秒）

        Returns:
            切片索引列表 [(start_sample, end_sample), ...]
        """
        chunk_size = int(chunk_duration * sr)
        total_samples = audio.shape[-1]

        slices = []
        for start in range(0, total_samples, chunk_size):
            end = min(start + chunk_size, total_samples)
            slices.append((start, end))

        return slices

    def get_audio_info(self, file_path: str | Path) -> dict:
        """
        获取音频文件信息

        Args:
            file_path: 音频文件路径

        Returns:
            包含音频信息的字典
        """
        file_path_str = str(file_path)

        try:
            # Try soundfile first (faster, supports WAV, FLAC, etc.)
            info = sf.info(file_path_str)
            return {
                "samplerate": info.samplerate,
                "channels": info.channels,
                "duration": info.duration,
                "format": info.format,
                "subtype": info.subtype
            }
        except Exception:
            # Fallback to librosa for formats not supported by soundfile (e.g., webm, m4a)
            try:
                # Get basic info using librosa
                import librosa
                duration = librosa.get_duration(path=file_path_str)

                # Try to get sample rate without loading full audio
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    # Load just a tiny bit to get sample rate
                    _, sr = librosa.load(file_path_str, sr=None, duration=0.1)

                return {
                    "samplerate": sr,
                    "channels": 2,  # Default assumption for formats librosa handles
                    "duration": duration,
                    "format": "UNKNOWN",
                    "subtype": "UNKNOWN"
                }
            except Exception as e:
                raise RuntimeError(f"无法获取音频信息: {e}")
