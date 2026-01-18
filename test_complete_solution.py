"""
完整解决方案测试 - 验证鼓声问题修复

这个脚本验证：
1. Issue 1: 鼓音色区分 (Kick/Snare/Hi-hat) ✅
2. Issue 2: 无鼓轨低频残留处理 ✅
"""

import sys
from pathlib import Path
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))

from core.drum_generator import DrumGenerator
from core.separator import DrumSeparator

def analyze_frequency_bands(audio, sr, label):
    """分析音频的低/中/高频能量分布"""
    # 计算频谱
    spectrum = np.abs(np.fft.rfft(audio))
    freqs = np.fft.rfftfreq(len(audio), 1/sr)

    # 分频段
    def band_energy(low, high):
        mask = (freqs >= low) & (freqs <= high)
        return np.sum(spectrum[mask]**2)

    low = band_energy(20, 150)
    mid = band_energy(150, 800)
    high = band_energy(800, 8000)
    total = low + mid + high

    low_pct = low / total * 100
    mid_pct = mid / total * 100
    high_pct = high / total * 100

    print(f"  {label}: 低频={low_pct:.1f}% 中频={mid_pct:.1f}% 高频={high_pct:.1f}%")

    return low_pct, mid_pct, high_pct

def test_issue1_drum_sounds():
    """Issue 1: 测试鼓音色区分度"""
    print("\n" + "="*70)
    print("ISSUE 1: 鼓音色区分测试")
    print("="*70)

    sr = 44100
    generator = DrumGenerator(sr)

    # 生成单个乐器
    kick = np.zeros(int(0.5 * sr), dtype=np.float32)
    snare = np.zeros(int(0.5 * sr), dtype=np.float32)
    hihat = np.zeros(int(0.3 * sr), dtype=np.float32)

    generator._add_kick(kick, 0, 0.9)
    generator._add_snare(snare, 0, 0.9)
    generator._add_hihat(hihat, 0, 0.9)

    # 分析频谱
    print("\n📊 单个乐器频谱分析:")
    kick_freqs = analyze_frequency_bands(kick, sr, "Kick")
    snare_freqs = analyze_frequency_bands(snare, sr, "Snare")
    hihat_freqs = analyze_frequency_bands(hihat, sr, "Hi-hat")

    # 验证标准
    print("\n✅ 验证结果:")
    issues = []

    # Kick: 应该主要是低频 (>80%)
    if kick_freqs[0] > 80:
        print("  ✅ Kick: 主要是低频 ({:.1f}%)".format(kick_freqs[0]))
    else:
        print(f"  ❌ Kick: 低频不足 ({kick_freqs[0]:.1f}%)")
        issues.append("kick_low")

    # Snare: 应该主要是中高频 (>60% 中+高)
    mid_high = snare_freqs[1] + snare_freqs[2]
    if mid_high > 60:
        print("  ✅ Snare: 主要是中高频 ({:.1f}%)".format(mid_high))
    else:
        print(f"  ❌ Snare: 中高频不足 ({mid_high:.1f}%)")
        issues.append("snare_midhigh")

    # Hi-hat: 应该主要是高频 (>80%)
    if hihat_freqs[2] > 80:
        print("  ✅ Hi-hat: 主要是高频 ({:.1f}%)".format(hihat_freqs[2]))
    else:
        print(f"  ❌ Hi-hat: 高频不足 ({hihat_freqs[2]:.1f}%)")
        issues.append("hihat_high")

    # 测试交替序列
    print("\n🎵 交替序列测试:")
    audio = np.zeros(int(2 * sr), dtype=np.float32)
    beat_len = int(60.0 / 75 * sr)

    for i in range(6):
        pos = i * beat_len
        if i % 2 == 0:
            generator._add_kick(audio, pos, 0.8)
        else:
            generator._add_snare(audio, pos, 0.6)
        # 每个节拍加个hihat
        generator._add_hihat(audio, pos, 0.3)

    # 提取单个节拍分析
    print("  节拍频谱对比:")
    for i in range(3):
        beat_start = i * beat_len
        beat = audio[beat_start:beat_start + beat_len]
        low, mid, high = analyze_frequency_bands(beat, sr, f"Beat {i+1}")
        if i % 2 == 0:
            print(f"    → Beat {i+1} (Kick) - 应低频高: {low:.1f}%")
        else:
            print(f"    → Beat {i+1} (Snare) - 应中高频高: {mid+high:.1f}%")

    # 保存测试文件
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    sf.write(output_dir / "test_kick.wav", kick, sr)
    sf.write(output_dir / "test_snare.wav", snare, sr)
    sf.write(output_dir / "test_hihat.wav", hihat, sr)
    sf.write(output_dir / "test_sequence_v2.wav", audio, sr)

    print(f"\n💾 测试文件已保存至: {output_dir}")

    if not issues:
        print("\n🎉 Issue 1: ✅ 已修复 - 鼓音色区分良好！")
        return True
    else:
        print(f"\n⚠️  Issue 1: 存在问题: {issues}")
        return False

def test_issue2_separation_quality():
    """Issue 2: 测试分离质量（低频残留）"""
    print("\n" + "="*70)
    print("ISSUE 2: 分离质量测试（低频残留）")
    print("="*70)

    audio_file = Path("unhidden_light.mp3")
    if not audio_file.exists():
        print(f"⚠️  跳过分离测试 - 找不到测试音频: {audio_file}")
        print("   请确保 unhidden_light.mp3 存在于项目根目录")
        return None

    output_dir = Path("separation_cleaned")
    output_dir.mkdir(exist_ok=True)

    separator = DrumSeparator()

    # 测试1: 原始分离
    print("\n📝 测试1: 原始分离（不滤波）")
    result1 = separator.separate(
        audio_file,
        output_dir / "original",
        clean_no_drums=False
    )

    # 测试2: 带高通滤波的分离
    print("\n📝 测试2: 分离 + 高通滤波 (180Hz)")
    result2 = separator.separate(
        audio_file,
        output_dir / "cleaned",
        clean_no_drums=True,
        cutoff_freq=180.0
    )

    # 分析两个结果的低频残留
    print("\n📊 低频残留对比分析:")

    def analyze_low_freq_ratio(audio_path):
        data, sr = sf.read(audio_path)
        if data.ndim == 2:
            data = np.mean(data, axis=1)

        # 低频能量占比
        spectrum = np.abs(np.fft.rfft(data))
        freqs = np.fft.rfftfreq(len(data), 1/sr)

        low = np.sum(spectrum[(freqs >= 20) & (freqs <= 150)]**2)
        total = np.sum(spectrum**2)
        return low / total * 100

    no_drums_original = Path(result1["no_drums"])
    no_drums_cleaned = Path(result2["no_drums"])

    low_orig = analyze_low_freq_ratio(no_drums_original)
    low_cleaned = analyze_low_freq_ratio(no_drums_cleaned)

    print(f"  无鼓轨 (原始): {low_orig:.1f}% 低频残留")
    print(f"  无鼓轨 (滤波): {low_cleaned:.1f}% 低频残留")
    print(f"  改善: {low_orig - low_cleaned:.1f}% 低频移除")

    # 评估结果
    print("\n✅ 验证结果:")
    success = True

    # 目标: 无鼓轨低频 < 15%
    if low_cleaned < 15:
        print(f"  ✅ 滤波后低频残留 {low_cleaned:.1f}% < 15% (目标达成)")
    else:
        print(f"  ⚠️  滤波后仍有 {low_cleaned:.1f}% 低频残留（建议提高 cutoff）")
        success = False

    # 如果原始就 < 15%，说明分离效果已经很好
    if low_orig < 15:
        print(f"  ✅ 原始分离已很好 ({low_orig:.1f}% 低频)")
        print("   注: 此音频不需要后处理滤波")

    print("\n💾 清理后的音频已保存至:")
    print(f"   - {no_drums_original}")
    print(f"   - {no_drums_cleaned}")

    if success:
        print("\n🎉 Issue 2: ✅ 已解决 - 高通滤波有效去除低频残留！")
    else:
        print("\n⚠️  Issue 2: 部分解决 - 可能需要调整滤波参数")

    return success

def main():
    """主测试流程"""
    print("="*70)
    print("🧪 鼓声问题完整解决方案测试")
    print("="*70)

    # Issue 1 测试
    issue1_ok = test_issue1_drum_sounds()

    # Issue 2 测试
    issue2_ok = test_issue2_separation_quality()

    # 总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70)

    if issue1_ok:
        print("✅ Issue 1 (鼓音色区分): 已修复")
    else:
        print("❌ Issue 1 (鼓音色区分): 未完全修复")

    if issue2_ok is True:
        print("✅ Issue 2 (分离质量): 已修复")
    elif issue2_ok is False:
        print("⚠️  Issue 2 (分离质量): 部分修复")
    else:
        print("⚪ Issue 2 (分离质量): 未测试（缺少音频文件）")

    print("\n" + "="*70)
    print("🔧 使用说明")
    print("="*70)
    print("\n1. 验证 Issue 1:")
    print("   请听 test_output/ 目录下的:")
    print("   - test_kick.wav (应该低沉)")
    print("   - test_snare.wav (应该明亮)")
    print("   - test_sequence_v2.wav (应该能听出 K-S-K-S)")

    print("\n2. 验证 Issue 2:")
    if issue2_ok is not None:
        print("   请对比听 separation_cleaned/ 目录下的:")
        print("   - original/no_drums.wav (可能有隆隆声)")
        print("   - cleaned/no_drums.wav (应该干净很多)")

    print("\n3. 如需进一步调整:")
    print("   - 修改 cutoff_freq 参数 (当前180Hz)")
    print("   - 尝试不同值: 150, 200, 250 Hz")
    print("   - 在 test_separation.py 中可看到详细频谱分析")

if __name__ == "__main__":
    main()
