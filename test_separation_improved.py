"""
分离质量优化测试 - 对比原始分离 vs 高通滤波后

这个脚本展示如何使用 clean_no_drums 参数改善分离质量
"""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))

from core.separator import DrumSeparator

def freq_band_analysis(audio, sr, label):
    """分析音频的频率分布并返回百分比"""
    spec = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1/sr)

    def band(low, high):
        mask = (freqs >= low) & (freqs <= high)
        return np.sum(spec[mask]**2)

    low = band(20, 150)
    mid = band(150, 800)
    high = band(800, 20000)
    total = low + mid + high

    low_pct = low / total * 100
    mid_pct = mid / total * 100
    high_pct = high / total * 100

    print(f"  {label}:")
    print(f"    低频(20-150Hz): {low_pct:.1f}%")
    print(f"    中频(150-800Hz): {mid_pct:.1f}%")
    print(f"    高频(800Hz+): {high_pct:.1f}%")

    return low_pct, mid_pct, high_pct

def main():
    audio_file = Path("unhidden_light.mp3")

    if not audio_file.exists():
        print(f"❌ 找不到音频文件: {audio_file}")
        print("   请确保 unhidden_light.mp3 存在于项目根目录")
        return

    print("="*70)
    print("分离质量优化测试")
    print("="*70)
    print(f"输入: {audio_file}")
    print()

    separator = DrumSeparator()

    # ===== 测试 1: 原始分离 =====
    print("\n" + "="*70)
    print("测试 1: 原始分离 (clean_no_drums=False)")
    print("="*70)

    output1 = Path("separation_original")
    result1 = separator.separate(audio_file, output1, clean_no_drums=False)

    # 读取并分析
    no_drums1, sr1 = sf.read(result1["no_drums"])
    if no_drums1.ndim == 2:
        no_drums1 = np.mean(no_drums1, axis=1)

    print("\n📊 无鼓轨频率分析 (原始):")
    low1, mid1, high1 = freq_band_analysis(no_drums1, sr1, "原始无鼓轨")

    # ===== 测试 2: 高通滤波 180Hz =====
    print("\n" + "="*70)
    print("测试 2: 分离 + 高通滤波 (180Hz)")
    print("="*70)

    output2 = Path("separation_180hz")
    result2 = separator.separate(
        audio_file,
        output2,
        clean_no_drums=True,
        cutoff_freq=180.0
    )

    # 读取并分析
    no_drums2, sr2 = sf.read(result2["no_drums"])
    if no_drums2.ndim == 2:
        no_drums2 = np.mean(no_drums2, axis=1)

    print("\n📊 无鼓轨频率分析 (滤波后):")
    low2, mid2, high2 = freq_band_analysis(no_drums2, sr2, "滤波无鼓轨")

    # ===== 测试 3: 高通滤波 250Hz (可选) =====
    print("\n" + "="*70)
    print("测试 3: 分离 + 高通滤波 (250Hz - 更激进)")
    print("="*70)

    output3 = Path("separation_250hz")
    result3 = separator.separate(
        audio_file,
        output3,
        clean_no_drums=True,
        cutoff_freq=250.0
    )

    # 读取并分析
    no_drums3, sr3 = sf.read(result3["no_drums"])
    if no_drums3.ndim == 2:
        no_drums3 = np.mean(no_drums3, axis=1)

    print("\n📊 无鼓轨频率分析 (激进滤波):")
    low3, mid3, high3 = freq_band_analysis(no_drums3, sr3, "250Hz滤波")

    # ===== 对比总结 =====
    print("\n" + "="*70)
    print("📊 对比总结")
    print("="*70)

    print("\n无鼓轨低频残留对比:")
    print(f"  原始分离:       {low1:.1f}%")
    print(f"  180Hz滤波:      {low2:.1f}%  (-{low1 - low2:.1f}%)")
    print(f"  250Hz滤波:      {low3:.1f}%  (-{low1 - low3:.1f}%)")

    print("\n📁 生成的文件:")
    print(f"  separation_original/")
    print(f"    ├── drum.wav")
    print(f"    ├── no_drums.wav  (原始，{low1:.1f}%低频)")
    print(f"    └── bass.wav")
    print()
    print(f"  separation_180hz/")
    print(f"    ├── drum.wav")
    print(f"    ├── no_drums.wav  (滤波，{low2:.1f}%低频)")
    print(f"    └── bass.wav")
    print()
    print(f"  separation_250hz/")
    print(f"    ├── drum.wav")
    print(f"    ├── no_drums.wav  (激进，{low3:.1f}%低频)")
    print(f"    └── bass.wav")

    # ===== 评估 =====
    print("\n" + "="*70)
    print("✅ 评估建议")
    print("="*70)

    if low1 < 15:
        print(f"\n🎉 原始分离质量已经很好 ({low1:.1f}%低频)")
        print("   建议: 使用原始分离结果即可")

    elif low2 < 15:
        print(f"\n✅ 180Hz滤波有效 ({low2:.1f}%低频)")
        print("   建议: 使用 separation_180hz/no_drums.wav")

    elif low3 < 15:
        print(f"\n⚠️  需要激进滤波 ({low3:.1f}%低频)")
        print("   建议: 使用 separation_250hz/no_drums.wav")
        print("   注意: 可能影响少量贝斯或低音乐器")

    else:
        print(f"\n⚠️  滤波后仍有较多低频")
        print("   可能原因:")
        print("   - 原曲贝斯很重，大量低频在 bass.wav 中")
        print("   - 可以尝试更高 cutoff (300-400Hz)")
        print("   - 或者接受当前水平用于练习")

    print("\n🎧 听音建议:")
    print("  1. 比较 separation_original/no_drums.wav")
    print("  2. 比较 separation_180hz/no_drums.wav")
    print("  3. 选择合适的版本使用")

if __name__ == "__main__":
    main()
