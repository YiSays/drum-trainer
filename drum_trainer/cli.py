"""
命令行界面 - Drum Trainer

快速使用分离、分析、生成功能
"""

import click
import sys
from pathlib import Path
import json
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.separator import DrumSeparator
from core.music_analyzer import MusicAnalyzer
from core.drum_generator import DrumGenerator
from core.audio_io import AudioIO


@click.group()
def main():
    """🥁 智能鼓声分离与音乐理解工具"""
    pass


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", default="output", help="输出目录")
@click.option("--chunk-size", default=30.0, help="分段处理时长（秒）")
@click.option("--model", default="htdemucs", type=click.Choice(["htdemucs", "htdemucs_ft", "htdemucs_6s"]), help="分离模型")
@click.option("--shifts", default=1, type=int, help="时间偏移增强次数")
def separate(input_file, output, chunk_size, model, shifts):
    """分离鼓声"""
    click.echo(f"🎵 分离鼓声: {input_file}")
    click.echo(f"输出目录: {output}")
    click.echo(f"模型: {model}")
    click.echo(f"时间偏移: {shifts}")

    try:
        separator = DrumSeparator(model_name=model)
        results = separator.separate(input_file, output, chunk_size, shifts=shifts)

        click.echo("\n✅ 分离完成！")
        click.echo("\n生成的文件:")
        for name, path in results.items():
            click.echo(f"  - {name}: {path}")

    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", help="保存JSON报告路径")
def analyze(input_file, output):
    """音乐分析"""
    click.echo(f"📊 分析音乐: {input_file}")

    try:
        analyzer = MusicAnalyzer()
        result = analyzer.analyze(input_file)

        click.echo("\n✅ 分析完成！")
        click.echo("\n结果:")
        click.echo(f"  风格: {result['style']}")
        click.echo(f"  BPM: {result['bpm']}")
        click.echo(f"  键: {result['key']}")
        click.echo(f"  情绪: {result['mood']}")
        click.echo(f"  能量: {result['energy']:.3f}")

        if result["structure"]:
            click.echo("\n  段落结构:")
            for section in result["structure"]["sections"]:
                click.echo(f"    - {section['type']:8s} {section['start']:5.1f}s - {section['end']:5.1f}s")

        # 保存报告
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            click.echo(f"\n📄 报告已保存: {output}")

    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", default="output", help="输出目录")
@click.option("--style", help="风格提示")
@click.option("--complexity", default=0.5, type=float, help="复杂度 (0.0-1.0)")
def generate(input_file, output, style, complexity):
    """生成鼓演奏"""
    click.echo(f"🥁 生成鼓演奏: {input_file}")

    try:
        # 分析
        click.echo("📊 步骤1: 分析音乐...")
        analyzer = MusicAnalyzer()
        analysis = analyzer.analyze(input_file)

        if style:
            analysis["style"] = style

        # 生成
        click.echo("🥁 步骤2: 生成演奏...")
        generator = DrumGenerator()
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)

        drum_track = generator.generate_from_analysis(analysis, output_dir)

        # 混合
        click.echo("🎵 步骤3: 创建混合音频...")
        audio_io = AudioIO()
        original_audio, sr = audio_io.load_audio(input_file)

        min_length = min(original_audio.shape[-1], len(drum_track.audio))
        original_audio = original_audio[:, :min_length]
        drum_audio = drum_track.audio[:min_length]

        if original_audio.shape[0] == 2:
            drum_stereo = audio_io.to_stereo(drum_audio[np.newaxis, :])[:, :min_length]
            mixed = original_audio + drum_stereo * 0.5
        else:
            mixed = original_audio + drum_audio * 0.5

        mixed_path = output_dir / "original_with_drums.wav"
        audio_io.save_audio(mixed, mixed_path, sr)

        click.echo("\n✅ 生成完成！")
        click.echo(f"\n结果:")
        click.echo(f"  模式: {drum_track.pattern}")
        click.echo(f"  BPM: {drum_track.bpm}")
        click.echo(f"\n文件:")
        click.echo(f"  - 鼓轨: {output_dir / 'generated_drums.wav'}")
        click.echo(f"  - 混合: {mixed_path}")
        click.echo(f"  - 节奏信息: {output_dir / 'rhythm_info.json'}")

    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)


@main.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", default="output", help="输出目录")
@click.option("--model", default="htdemucs", type=click.Choice(["htdemucs", "htdemucs_ft", "htdemucs_6s"]), help="分离模型")
@click.option("--shifts", default=1, type=int, help="时间偏移增强次数")
def complete(input_file, output, model, shifts):
    """完整处理：分离 + 分析 + 生成"""
    click.echo(f"🚀 完整处理: {input_file}")
    click.echo(f"输出目录: {output}")
    click.echo(f"模型: {model}")
    click.echo(f"时间偏移: {shifts}")

    try:
        # 1. 分离
        click.echo("\n[1/3] 分离鼓声...")
        separator = DrumSeparator(model_name=model)
        separated = separator.separate(input_file, f"{output}/separated", shifts=shifts)

        # 2. 分析
        click.echo("\n[2/3] 音乐分析...")
        analyzer = MusicAnalyzer()
        analysis = analyzer.analyze(input_file)

        # 3. 生成
        click.echo("\n[3/3] 生成鼓演奏...")
        generator = DrumGenerator()
        output_dir = Path(output) / "generated"
        output_dir.mkdir(parents=True, exist_ok=True)

        drum_track = generator.generate_from_analysis(analysis, output_dir)

        click.echo("\n✅ 完成！")
        click.echo("\n所有文件都在输出目录中:")
        click.echo(f"  - 分离的鼓声: {output}/separated/drum.wav")
        click.echo(f"  - 生成的鼓声: {output}/generated/generated_drums.wav")
        click.echo(f"  - 分析报告: {output}/generated/rhythm_info.json")

    except Exception as e:
        click.echo(f"❌ 错误: {e}", err=True)


@main.command()
def info():
    """显示系统信息"""
    import torch

    click.echo("📋 系统信息")
    click.echo("=" * 50)
    click.echo(f"Python: {sys.version.split()[0]}")
    click.echo(f"PyTorch: {torch.__version__}")

    if torch.backends.mps.is_available():
        click.echo("设备: Apple Silicon (Metal加速) ✅")
    elif torch.cuda.is_available():
        click.echo("设备: CUDA GPU ✅")
    else:
        click.echo("设备: CPU ⚠️")

    click.echo(f"工作目录: {Path.cwd()}")
    click.echo("=" * 50)


if __name__ == "__main__":
    main()
