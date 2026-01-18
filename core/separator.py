"""
鼓声分离模块 - 使用 Demucs 模型

针对 Apple Silicon 优化，自动检测并使用 Metal 加速。
模型默认存储在 storage/models/ 目录下。
"""

import os
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List
import warnings
from tqdm import tqdm

from .audio_io import AudioIO
from scipy.signal import butter, filtfilt

warnings.filterwarnings("ignore")

# MPS兼容性处理 - 某些操作不支持MPS，需要fallback到CPU
if torch.backends.mps.is_available():
    os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'


class DrumSeparator:
    """使用 Demucs 的鼓声分离器"""

    def __init__(self, model_name: str = "htdemucs", device: Optional[str] = None,
                 model_cache_dir: str | Path = "storage/models"):
        """
        初始化分离器

        Args:
            model_name: Demucs 模型名称
                - "htdemucs": Hybrid Transformer，最新最强，4声部分离 (drums, bass, other, vocals)
                - "htdemucs_ft": 微调版本，4声部分离
                - "htdemucs_6s": 6声部分离 (drums, bass, other, vocals, piano, guitar)
            device: 指定设备 (auto/metal/cpu/cuda)
            model_cache_dir: 模型缓存目录，默认为 storage/models
        """
        self.model_name = model_name
        self.device = self._detect_device(device)
        self.audio_io = AudioIO()
        self.model = None

        # 设置模型缓存路径到 storage/models
        cache_path = Path(model_cache_dir).resolve()
        cache_path.mkdir(parents=True, exist_ok=True)
        os.environ['TORCH_HOME'] = str(cache_path)

        print(f"🔧 初始化 Demucs 分离器 - 设备: {self.device}")
        print(f"📁 模型缓存路径: {cache_path}")

        # Apple Silicon 检测信息
        if self.device == "mps":
            print("✅ 检测到 Apple Silicon，使用 Metal 加速")
        elif self.device == "cpu":
            print("⚠️  使用 CPU 模式（更稳定）")

    def _detect_device(self, device: Optional[str]) -> str:
        """
        检测并设置最佳计算设备

        Args:
            device: 用户指定的设备

        Returns:
            设备字符串 (cpu/cuda/mps)
        """
        if device:
            # 用户手动指定
            if device == "metal":
                return "mps"
            return device

        # 自动检测 - 对于Demucs，建议优先使用CPU以避免MPS兼容性问题
        # 如果用户明确需要速度，可以手动指定metal
        if torch.cuda.is_available():
            return "cuda"
        else:
            # 即使MPS可用，Demucs在MPS上可能有问题，使用更稳定的CPU
            # 用户可以通过 device="metal" 强制使用MPS
            return "cpu"

    def _load_model(self):
        """延迟加载模型，节省内存"""
        if self.model is not None:
            return

        try:
            from demucs.pretrained import get_model
            from demucs.apply import apply_model

            # 加载模型
            print(f"📥 下载/加载模型: {self.model_name}")
            self.model = get_model(self.model_name)
            self.model.to(self.device)
            self.model.eval()

            # 保存apply_model函数引用
            self.apply_model_fn = apply_model

            print(f"✅ 模型加载完成")

        except ImportError:
            raise ImportError(
                "Demucs 未安装，请运行: uv add demucs @ git+https://github.com/facebookresearch/demucs.git@main"
            )
        except Exception as e:
            raise RuntimeError(f"模型加载失败: {e}")

    def separate(self, audio_path: str | Path, output_dir: str | Path,
                 chunk_duration: float = 30.0, clean_no_drums: bool = False,
                 cutoff_freq: float = 180.0, progress_callback=None) -> dict:
        """
        分离鼓声并保存结果

        Args:
            audio_path: 输入音频文件
            output_dir: 输出目录
            chunk_duration: 分段处理时长（秒），避免内存溢出
            clean_no_drums: 是否对no_drums应用高通滤波去除低频残留
            cutoff_freq: 高通滤波截止频率(Hz)，当clean_no_drums=True时使用
            progress_callback: 可选的进度回调函数，接收 (stage, current, total, message) 参数

        Returns:
            包含输出文件路径的字典
        """
        self._load_model()
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 加载音频
        if progress_callback:
            progress_callback("loading", 0, 1, "加载音频文件...")
        print("📂 加载音频文件...")
        audio, sr = self.audio_io.load_audio(audio_path)
        duration = self.audio_io.get_duration(audio, sr)

        print(f"📊 音频信息: {duration:.2f}秒, {sr}Hz, {audio.shape[0]}声道")

        # 分段处理长音频
        slices = self.audio_io.split_long_audio(audio, sr, chunk_duration)
        all_results = []

        num_chunks = len(slices)
        print(f"🔪 分离处理: {num_chunks}个片段")

        for i, (start, end) in enumerate(tqdm(slices, desc="分离进度")):
            chunk = audio[:, start:end]
            chunk_results = self._separate_chunk(chunk, sr)
            all_results.append(chunk_results)

            # Report chunk progress
            if progress_callback:
                progress_callback("chunk", i + 1, num_chunks, f"处理片段 {i + 1}/{num_chunks}")

        # 合并结果
        if progress_callback:
            progress_callback("merging", 0, 7, "合并片段...")
        print("🔄 合并片段...")
        final_results = self._merge_results(
            all_results, output_dir, sr,
            clean_no_drums=clean_no_drums,
            cutoff_freq=cutoff_freq,
            progress_callback=progress_callback
        )

        return final_results

    def _separate_chunk(self, audio_chunk: np.ndarray, sr: int) -> dict:
        """
        处理单个音频片段

        Returns:
            分离结果字典，包含各声部的numpy数组
        """
        # 转换为tensor
        audio_tensor = torch.from_numpy(audio_chunk).float()

        # 应用模型 - 使用apply_model函数
        with torch.no_grad():
            # demucs.apply_model 返回 [batch, sources, channels, time]
            sources = self.apply_model_fn(
                self.model,
                audio_tensor.unsqueeze(0).to(self.device),
                device=self.device
            )

        # 转换回numpy
        sources = sources.cpu().numpy()[0]  # 移除batch维度

        # Demucs 声部顺序取决于模型:
        # 4-source: drums, bass, other, vocals
        # 6-source: drums, bass, other, vocals, piano, guitar
        num_sources = sources.shape[0]

        result = {
            "drums": sources[0],
            "bass": sources[1],
            "other": sources[2],
            "vocals": sources[3],
        }

        # 6-source models have piano and guitar
        if num_sources >= 6:
            result["piano"] = sources[4]
            result["guitar"] = sources[5]

        return result

    def _merge_results(self, results: list, output_dir: Path, sr: int,
                      clean_no_drums: bool = False, cutoff_freq: float = 180.0,
                      progress_callback=None) -> dict:
        """
        合并所有片段并保存

        Args:
            results: 分离结果列表
            output_dir: 输出目录
            sr: 采样率
            clean_no_drums: 是否对no_drums应用高通滤波去除低频残留
            cutoff_freq: 高通滤波截止频率(Hz)，当clean_no_drums=True时使用
            progress_callback: 可选的进度回调函数
        """
        if not results:
            raise ValueError("没有可合并的结果")

        # 检查是否为6-source模型
        is_6_source = "piano" in results[0]

        # 合并每个声部
        if progress_callback:
            progress_callback("merging", 1, 7, "合并 drums...")
        drums = np.concatenate([r["drums"] for r in results], axis=-1)

        if progress_callback:
            progress_callback("merging", 2, 7, "合并 bass...")
        bass = np.concatenate([r["bass"] for r in results], axis=-1)

        if progress_callback:
            progress_callback("merging", 3, 7, "合并 other...")
        other = np.concatenate([r["other"] for r in results], axis=-1)

        if progress_callback:
            progress_callback("merging", 4, 7, "合并 vocals...")
        vocals = np.concatenate([r["vocals"] for r in results], axis=-1)

        # 6-source模型：合并piano和guitar
        if is_6_source:
            if progress_callback:
                progress_callback("merging", 5, 9, "合并 piano...")
            piano = np.concatenate([r["piano"] for r in results], axis=-1)

            if progress_callback:
                progress_callback("merging", 6, 9, "合并 guitar...")
            guitar = np.concatenate([r["guitar"] for r in results], axis=-1)

            original = drums + bass + piano + guitar + other + vocals
            no_drums = bass + piano + guitar + other + vocals
            no_vocals = drums + bass + piano + guitar + other
            total_files = 9
        else:
            # 4-source模型
            original = drums + bass + other + vocals  # 完整原曲
            no_drums = bass + other + vocals           # 无鼓
            no_vocals = drums + bass + other          # 无人声
            total_files = 7

        # 可选：no_drums后处理（高通滤波去除低频残留）
        if clean_no_drums:
            print(f"🔧 应用高通滤波去除低频残留 (cutoff={cutoff_freq}Hz)")
            no_drums = self._highpass_filter(no_drums, sr, cutoff_freq)

        # 归一化并保存
        files = {}

        # 保存各声部（统一使用WAV格式以确保兼容性）
        def save_with_progress(name: str, audio_data: np.ndarray, file_path: Path, current: int):
            if progress_callback:
                progress_callback("saving", current, total_files, f"保存 {name}...")
            self.audio_io.save_audio(audio_data, file_path, sr)
            return file_path

        files["original"] = save_with_progress("original", original, output_dir / "original.wav", 1)

        files["drum"] = save_with_progress("drum", drums, output_dir / "drum.wav", 2)

        files["no_drums"] = save_with_progress("no_drums", no_drums, output_dir / "no_drums.wav", 3)

        files["no_vocals"] = save_with_progress("no_vocals", no_vocals, output_dir / "no_vocals.wav", 4)

        files["bass"] = save_with_progress("bass", bass, output_dir / "bass.wav", 5)

        files["vocals"] = save_with_progress("vocals", vocals, output_dir / "vocals.wav", 6)

        files["other"] = save_with_progress("other", other, output_dir / "other.wav", 7)

        # 保存piano和guitar（如果为6-source模型）
        if is_6_source:
            files["piano"] = save_with_progress("piano", piano, output_dir / "piano.wav", 8)
            files["guitar"] = save_with_progress("guitar", guitar, output_dir / "guitar.wav", 9)

        return {k: str(v) for k, v in files.items()}

    def _highpass_filter(self, audio: np.ndarray, sr: int, cutoff: float = 180.0) -> np.ndarray:
        """
        高通滤波器 - 移除低频残留

        Args:
            audio: 输入音频
            sr: 采样率
            cutoff: 截止频率(Hz)

        Returns:
            滤波后的音频
        """
        nyquist = sr / 2
        normal_cutoff = cutoff / nyquist
        b, a = butter(4, normal_cutoff, btype='high', analog=False)
        return filtfilt(b, a, audio)

    def preview_sources(self, audio_path: str | Path) -> dict:
        """
        快速预览分离结果（不保存文件）

        Returns:
            各声部的音频数据字典
        """
        self._load_model()

        audio, sr = self.audio_io.load_audio(audio_path)

        # 只处理前30秒用于预览
        if audio.shape[-1] > sr * 30:
            audio = audio[:, :sr * 30]

        results = self._separate_chunk(audio, sr)

        # 返回时长信息（不返回完整音频数据）
        durations = {
            "drums": audio.shape[-1] / sr,
            "bass": audio.shape[-1] / sr,
            "other": audio.shape[-1] / sr,
            "vocals": audio.shape[-1] / sr,
        }

        # 6-source模型额外包含piano和guitar
        if "piano" in results:
            durations["piano"] = audio.shape[-1] / sr
            durations["guitar"] = audio.shape[-1] / sr

        return durations
