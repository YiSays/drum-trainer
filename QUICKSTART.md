# 🚀 快速开始指南

针对 **Apple Silicon (M系列芯片)** 优化

---

## ⚡ 3分钟快速安装

### 1. 安装 uv (如果未安装)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.cargo/env"
```

### 2. 下载项目
```bash
git clone <your-repo> drum-trainer
cd drum-trainer
```

### 3. 安装依赖
```bash
uv sync
```

**⚠️ 注意**:
- 这会安装 PyTorch (支持 Metal 加速) 和 Demucs
- 首次运行 Demucs 会下载模型 (~1.5GB)，请保持网络通畅
- Essentia 和 Madmom 是可选的，可稍后安装

### 4. 验证安装
```bash
uv run python test_simple.py
```

应该看到:
```
✅ torch, librosa, numpy 导入成功
✅ Apple Silicon Metal 加速可用 (MPS)
✅ 核心模块导入成功
```

---

## 🎯 开始使用

### 方法 A: CLI 命令行 (最简单)

```bash
# 查看帮助
uv run drum-trainer info

# 完整处理 (推荐)
uv run drum-trainer complete your_song.mp3 -o output/

# 查看结果
ls output/generated/
# 你会看到:
# - generated_drums.wav (生成的鼓演奏)
# - original_with_generated_drums.wav (原曲+鼓)
# - rhythm_info.json (节奏分析)
```

### 方法 B: API 服务

```bash
# 启动服务
uv run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

# 访问文档
open http://localhost:8000/docs

# 测试 API (新终端)
curl -X POST http://localhost:8000/generation/process \
  -F "file=@your_song.mp3" \
  -o result.json
```

---

## 📊 功能演示

### 1. 鼓声分离
```bash
uv run drum-trainer separate song.mp3 -o output/
# 输出: output/drum.wav, output/no_drums.mp3
```

### 2. 音乐分析
```bash
uv run drum-trainer analyze song.mp3
# 输出:
# 风格: rock
# BPM: 128
# 结构: intro, verse, chorus, chorus
```

### 3. 生成鼓演奏
```bash
uv run drum-trainer generate song.mp3 -o output/ --style rock
# 输出: output/generated_drums.wav
```

### 4. 完整流程
```bash
uv run drum-trainer complete song.mp3 -o output/
# 一次完成: 分离 + 分析 + 生成
```

---

## 🔧 高级配置

### 环境变量
创建 `.env` 文件:
```bash
DEVICE=mps              # 使用 Metal 加速
CHUNK_DURATION=30       # 分段处理时长(秒)
MAX_FILE_SIZE=500       # 最大文件大小(MB)
```

### 安装可选依赖
```bash
# 高级音乐分析 (可能需要编译)
uv add --optional analysis essentia madmom

# 开发工具
uv add --optional dev pytest black ruff mypy
```

### 手动安装 Essentia (如果自动失败)
```bash
# 使用 Homebrew
brew install essentia

# 或使用 Conda
conda install -c conda-forge essentia
```

---

## 🎵 示例输出

### 完整处理结果
```json
{
  "status": "success",
  "analysis": {
    "style": "rock",
    "bpm": 128,
    "energy": 0.65,
    "key": "C",
    "mood": "energetic",
    "structure": {
      "sections": [
        {"type": "intro", "start": 0, "end": 16, "duration": 16},
        {"type": "verse", "start": 16, "end": 48, "duration": 32},
        {"type": "chorus", "start": 48, "end": 80, "duration": 32}
      ]
    },
    "rhythm_profile": {
      "main_pattern": "rock_basic",
      "complexity": 0.45
    }
  },
  "files": {
    "generated_drums": "output/generated/generated_drums.wav",
    "original_with_drums": "output/original_with_generated_drums.wav"
  }
}
```

### 生成的文件
```
output/
├── separated/              # Demucs 分离结果
│   ├── drum.wav
│   ├── no_drums.mp3
│   └── mixed.wav
├── generated/              # 生成的鼓
│   ├── generated_drums.wav
│   └── rhythm_info.json
└── original_with_generated_drums.wav  # 混合音频
```

---

## 📱 Web 前端 (Flutter)

**计划中**: 一套代码，支持 Web/iOS/Android

```bash
# 未来命令
flutter create drum_trainer_app
cd drum_trainer_app
flutter run -d chrome
```

---

## 🎯 使用场景

### 鼓手练习
```bash
# 1. 分析歌曲
uv run drum-trainer analyze song.mp3

# 2. 获取仅鼓伴奏
uv run drum-trainer separate song.mp3 -o output/

# 3. 生成练习节奏
uv run drum-trainer generate song.mp3 -o output/ --complexity 0.6
```

### 音乐制作
```bash
# 快速获取鼓样本
uv run drum-trainer complete beat.mp3 -o samples/
```

### 学习分析
```bash
# 理解歌曲结构
uv run drum-trainer analyze jazz_song.mp3
```

---

## ⚠️ 故障排除

### 问题: PyTorch 无法使用 Metal
```bash
# 检查版本
uv run python -c "import torch; print(torch.__version__)"

# 应 >= 2.0.0
# 如果不是，请清理并重装
rm -rf .venv
uv sync
```

### 问题: Demucs 下载失败
```bash
# 手动下载模型
mkdir -p storage/models
# 从 https://github.com/facebookresearch/demucs 下载
# 放入 storage/models/
```

### 问题: 内存不足
```bash
# 减少分段大小
uv run drum-trainer complete song.mp3 --chunk-size 15
```

### 问题: Essentia 安装失败
```bash
# 不影响核心功能
# 可选安装，如果失败可以跳过
# 仍然可以使用分离和生成功能
```

---

## 🎉 验证成功

运行以下命令验证一切正常:

```bash
uv run python test_simple.py && echo "✅ 安装成功！" || echo "❌ 安装失败"
```

**成功标志**:
- ✅ Metal 加速可用
- ✅ 核心模块导入成功
- ✅ 可以生成鼓演奏

---

## 💡 下一步

1. **测试你的第一首歌**:
   ```bash
   uv run drum-trainer complete your_song.mp3 -o test/
   ```

2. **探索 API**:
   - 访问 http://localhost:8000/docs
   - 测试所有端点

3. **准备测试音频**:
   - 推荐: 2-5分钟，有明确段落
   - 格式: mp3, wav, flac
   - 风格: 摇滚/流行/爵士等

---

## 📞 需要帮助？

查看完整文档: [README.md](README.md)

或运行:
```bash
uv run drum-trainer info
```

**祝你使用愉快！** 🥁
