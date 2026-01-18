"""
简单分离测试 - 检查Demucs分离效果
"""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))

from core.separator import DrumSeparator

def main():
    audio_file = Path("unhidden_light.mp3")
    output_dir = Path("separation_test")
    output_dir.mkdir(exist_ok=True)

    if not audio_file.exists():
        print(f"❌ 找不到音频文件: {audio_file}")
        return

    print("=" * 70)
    print("分离效果测试")
    print("=" * 70)
    print(f"输入: {audio_file}")
    print(f"输出: {output_dir}")
    print()

    try:
        separator = DrumSeparator()

        print("⏳ 开始分离（这可能需要几分钟）...")
        result = separator.separate(audio_file, output_dir)

        print("\n✅ 分离完成！")
        print("\n生成的文件:")
        for name, path in result.items():
            size = Path(path).stat().st_size / 1024 / 1024
            print(f"  {name}: {path} ({size:.1f} MB)")

        # 分析分离质量
        print("\n📊 分离质量分析:")

        # 读取文件
        drums, sr = sf.read(result["drum"])
        no_drums, _ = sf.read(result["no_drums"])

        # 转换为mono
        if drums.ndim == 2:
            drums = np.mean(drums, axis=1)
        if no_drums.ndim == 2:
            no_drums = np.mean(no_drums, axis=1)

        # 计算RMS
        drums_rms = np.sqrt(np.mean(drums**2))
        no_drums_rms = np.sqrt(np.mean(no_drums**2))

        print(f"  鼓轨RMS: {drums_rms:.4f}")
        print(f"  无鼓轨RMS: {no_drums_rms:.4f}")

        # 频谱分析 - 重点看低频残留
        def freq_band(audio, sr, low, high):
            spec = np.abs(np.fft.rfft(audio))
            freqs = np.fft.rfftfreq(len(audio), 1/sr)
            mask = (freqs >= low) & (freqs <= high)
            return np.sum(spec[mask]**2)

        # 无鼓轨的低频能量占比
        no_drums_low = freq_band(no_drums, sr, 20, 150)
        no_drums_total = freq_band(no_drums, sr, 20, 20000)
        low_ratio = no_drums_low / no_drums_total

        print(f"\n  无鼓轨低频(20-150Hz)占比: {low_ratio*100:.2f}%")

        if low_ratio < 0.05:
            print("  ✅ 分离质量优秀！低频残留很少")
        elif low_ratio < 0.1:
            print("  ⚠️ 分离质量一般，有少量低频残留")
        else:
            print("  ❌ 分离效果差，低频残留过多")

        # 鼓轨的频率分布
        drums_low = freq_band(drums, sr, 20, 150)
        drums_mid = freq_band(drums, sr, 150, 800)
        drums_high = freq_band(drums, sr, 800, 20000)
        drums_total = drums_low + drums_mid + drums_high

        print(f"\n  鼓轨频率分布:")
        print(f"    低频(20-150Hz): {drums_low/drums_total*100:.1f}%")
        print(f"    中频(150-800Hz): {drums_mid/drums_total*100:.1f}%")
        print(f"    高频(800Hz+): {drums_high/drums_total*100:.1f}%")

        if drums_low / drums_total > 0.6:
            print("  ✅ 鼓轨以低频为主，符合预期")
        else:
            print("  ⚠️ 鼓轨频率分布异常")

        print("\n" + "=" * 70)
        print("💡 听一下生成的文件:")
        print(f"   - {result['drum']} (应该是纯鼓声)")
        print(f"   - {result['no_drums']} (应该没有鼓声)")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ 出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
