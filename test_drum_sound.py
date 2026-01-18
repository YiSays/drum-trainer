"""
快速测试鼓音色 - 听生成的Kick/Snare是否有明显区别
"""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))

from core.drum_generator import DrumGenerator

def create_test_beats():
    """创建测试：连续4个节拍，检查音色"""
    sr = 44100
    generator = DrumGenerator(sr)

    # 创建一个空的音频
    audio = np.zeros(int(2 * sr), dtype=np.float32)  # 2秒

    # 手动添加几个节拍，便于测试
    beat_samples = int(60.0 / 75 * sr)  # 75 BPM

    # 节拍1: Kick on beat 1
    generator._add_kick(audio, 0, 0.8)

    # 节拍2: Snare on beat 2 (延迟1拍)
    generator._add_snare(audio, beat_samples, 0.6)

    # 节拍3: Kick on beat 3
    generator._add_kick(audio, beat_samples * 2, 0.8)

    # 节拍4: Snare on beat 4
    generator._add_snare(audio, beat_samples * 3, 0.6)

    # 节拍5: Kick
    generator._add_kick(audio, beat_samples * 4, 0.8)

    # 节拍6: Snare
    generator._add_snare(audio, beat_samples * 5, 0.6)

    # 保存
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    # 保存单独的
    kick_only = np.zeros(int(0.5 * sr), dtype=np.float32)
    generator._add_kick(kick_only, 0, 0.9)
    sf.write(output_dir / "kick_single.wav", kick_only, sr)

    snare_only = np.zeros(int(0.5 * sr), dtype=np.float32)
    generator._add_snare(snare_only, 0, 0.9)
    sf.write(output_dir / "snare_single.wav", snare_only, sr)

    hihat_only = np.zeros(int(0.3 * sr), dtype=np.float32)
    generator._add_hihat(hihat_only, 0, 0.9)
    sf.write(output_dir / "hihat_single.wav", hihat_only, sr)

    # 保存交替序列
    sf.write(output_dir / "test_sequence.wav", audio, sr)

    print("✅ 音色测试文件已生成:")
    print(f"  - {output_dir / 'kick_single.wav'} (Kick 单独)")
    print(f"  - {output_dir / 'snare_single.wav'} (Snare 单独)")
    print(f"  - {output_dir / 'hihat_single.wav'} (Hi-hat 单独)")
    print(f"  - {output_dir / 'test_sequence.wav'} (Kick/Snare交替)")
    print("\n🎵 请听这些文件，检查:")
    print("  1. Kick是否低沉有力 (低音)")
    print("  2. Snare是否明亮有中频")
    print("  3. Hi-hat是否尖锐")
    print("  4. 交替序列是否能听出差异")

    # 频谱分析
    print("\n📊 频谱分析:")
    for name, file in [
        ("Kick", "kick_single.wav"),
        ("Snare", "snare_single.wav"),
        ("Hi-hat", "hihat_single.wav")
    ]:
        filepath = output_dir / file
        data, _ = sf.read(filepath)
        spectrum = np.abs(np.fft.rfft(data))
        freqs = np.fft.rfftfreq(len(data), 1/sr)

        def band(low, high):
            mask = (freqs >= low) & (freqs <= high)
            return np.sum(spectrum[mask]**2)

        total = band(20, 20000)
        low = band(20, 150) / total * 100
        mid = band(150, 800) / total * 100
        high = band(800, 20000) / total * 100

        print(f"  {name}: 低={low:.1f}% 中={mid:.1f}% 高={high:.1f}%")

if __name__ == "__main__":
    create_test_beats()
