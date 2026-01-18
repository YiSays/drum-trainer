# 🥁 智能鼓声分离与音乐理解工具

基于 AI 的一站式音乐分析与鼓演奏生成工具，针对 Apple Silicon (M系列芯片) 优化。

## ✨ 核心特性

### 🎵 鼓声分离 (Demucs AI)
- 使用 Facebook 的 Demucs 模型分离鼓声
- 支持长音频分段处理（避免内存溢出）
- 生成：仅鼓声、无鼓伴奏、完整混合

### 📊 音乐理解 (A+B 优先级)
自动分析并理解音乐的深层结构：
- **风格识别**：rock, jazz, pop, electronic, hip_hop, funk 等
- **BPM 检测**：多算法融合，高准确率
- **段落结构**：intro, verse, chorus, bridge, outro
- **节奏特征**：节奏型、稳定性、复杂度
- **键/调性**：C, G, D, A 等
- **情绪分析**：energetic, relaxed, happy 等

### 🥁 智能生成 (纯自动)
- 基于音乐分析生成适合的鼓演奏
- 20+ 种预定义节奏模式库
- 自动匹配风格、速度、复杂度
- 生成多种音频：鼓轨、混合音频

### ⚡ Apple Silicon 优化
- **Metal 加速**：自动使用 MPS 后端
- **uv 管理**：现代化依赖管理
- **跨平台**：Python + Flutter，支持 Web/iOS/Android

## 📁 项目结构

```
drum-trainer/
├── core/                          # Python 核心模块
│   ├── audio_io.py               # 音频处理
│   ├── separator.py              # Demucs 分离器
│   ├── music_analyzer.py         # 音乐分析 (v1 - 基础)
│   ├── music_analyzer_v2.py      # 音乐分析 (v2 - 带节拍)
│   ├── structure_detector.py     # 段落检测
│   ├── rhythm_detector.py        # 节奏识别
│   └── drum_generator.py         # 鼓生成器
│
├── api/                           # FastAPI 服务
│   ├── server.py                 # 主服务
│   ├── models.py                 # 数据模型
│   └── endpoints/
│       ├── separation.py         # 分离端点
│       ├── analysis.py           # 分析端点
│       ├── generation.py         # 生成端点
│       ├── tracks.py             # 音轨管理端点
│       └── youtube.py            # YouTube 下载端点
│
├── drum_trainer/                  # CLI 工具
│   ├── __init__.py
│   └── cli.py                    # 命令行接口
│
├── scripts/                       # 脚本
│   ├── install.sh               # 安装脚本
│   └── run.sh                   # 启动脚本
│
├── storage/                       # 数据存储
│   ├── uploaded/                 # 已上传文件 (主目录)
│   │   ├── separated/            # 分离结果
│   │   │   ├── drum.wav          # 鼓声分离
│   │   │   ├── no_drums.wav      # 无鼓伴奏
│   │   │   └── temp.mp3          # 临时文件 (处理后删除)
│   │   └── <原始音频文件>          # 上传的原始文件
│   ├── generated/               # 生成的音频 (时间戳)
│   ├── models/                  # AI 模型缓存
│   └── demo/                    # 演示文件 (计划中)
│
├── web_ui/                       # Web 前端界面
│   ├── index.html              # 主页面
│   ├── css/
│   │   └── style.css           # 样式
│   └── js/
│       └── app.js              # JavaScript 逻辑
│
├── web/                          # Flutter 前端 (开发中)
├── pyproject.toml               # 依赖配置
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone <your-repo> drum-trainer
cd drum-trainer

# 运行安装脚本 (自动配置 uv 和依赖)
./scripts/install.sh
```

**手动安装**：
```bash
# 安装 uv (如果未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.cargo/env"

# 安装项目依赖
uv sync
```

### 2. 启动 API 服务

```bash
# 方法 1: 使用脚本
./scripts/run.sh

# 方法 2: 直接运行
uv run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

# 方法 3: 指定设备
DEVICE=mps uv run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

访问：
- **Web UI**: http://localhost:8000/ui (推荐用于测试和演示)
- API 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

### 3. 使用 CLI

```bash
# 查看系统信息
uv run drum-trainer info

# 分离鼓声
uv run drum-trainer separate your_song.mp3 -o output/

# 音乐分析
uv run drum-trainer analyze your_song.mp3

# 生成鼓演奏
uv run drum-trainer generate your_song.mp3 -o output/ --style rock

# 完整处理 (推荐)
uv run drum-trainer complete your_song.mp3 -o output/
```

## 🌐 Web UI 使用指南

启动服务后访问 `http://localhost:8000/ui` 即可使用 Web 界面：

### 📤 上传音频

1. **拖放音频文件**到上传区域或点击"选择文件"
2. 支持格式：MP3, WAV, FLAC, OGG, M4A, WEBM
3. 文件**自动上传**到 `storage/uploaded/` 目录
4. 预览信息显示文件大小、时长、格式

### 🎧 YouTube 下载

1. 在 YouTube 下载区域粘贴视频链接
2. 可选：指定输出文件名
3. 点击"下载音频"开始下载
4. 文件保存到 `storage/uploaded/` 目录
5. **自动显示在音轨列表中**

### 🎵 音轨管理

**音轨列表 (Track List)**:
- 仅显示 `storage/uploaded/separated/` 目录中的分离结果
- 文件名如：`drum.wav`, `no_drums.wav`, `bass.wav`, `vocals.wav` 等
- 点击音轨即可播放

**播放控制**:
- **播放**: 开始播放选中的音轨
- **暂停**: 暂停播放
- **停止**: 停止所有音轨
- **循环**: 启用/禁用循环播放
- **音量**: 调整整体音量 (0-100%)
- **速度**: 调整播放速度 (0.5x - 2.0x)

### 📈 音频可视化

- **实时频谱**: 显示音频频谱可视化
- **波形显示**: 音频波形预览

### 🔧 工作流程

```
上传/下载音频 → 保存到 storage/uploaded/
    ↓
点击"确认处理" → 分离鼓声 → 保存到 storage/uploaded/separated/
    ↓
音轨列表展开 → 显示分离结果 → 可播放/试听
    ↓
点击"清除" → 删除 storage/uploaded/ → 音轨列表清空
```

### 🎛️ 端点按钮

- **刷新**: 刷新音轨列表
- **清除**: 删除所有上传文件和分离结果
- **上传**: 展开/折叠上传面板

### 📊 预览信息

当上传面板折叠时，`现在播放` 卡片会显示：
- 文件名
- 文件大小
- 音频时长
- 文件格式

## 🔧 API 使用

### 完整处理 (推荐)

```bash
curl -X POST "http://localhost:8000/generation/process" \
  -F "file=@your_song.mp3" \
  -o result.json
```

返回数据：
```json
{
  "status": "success",
  "message": "完整处理完成",
  "analysis": {
    "style": "rock",
    "bpm": 128,
    "energy": 0.65,
    "key": "C",
    "mood": "energetic",
    "structure": {
      "total_sections": 4,
      "types": {"intro": 1, "verse": 1, "chorus": 2},
      "sections": [
        {"type": "intro", "start": 0, "end": 16, "duration": 16},
        {"type": "verse", "start": 16, "end": 48, "duration": 32},
        {"type": "chorus", "start": 48, "end": 80, "duration": 32},
        {"type": "chorus", "start": 80, "end": 112, "duration": 32}
      ]
    },
    "rhythm_profile": {
      "main_pattern": "rock_standard",
      "complexity": 0.45,
      "recommended_practice": "基础节奏练习：保持稳定的四分音符"
    }
  },
  "generated": {
    "pattern": "rock_basic",
    "bpm": 128
  },
  "files": {
    "drum": "storage/generated/complete_20260114/separated/drum.wav",
    "no_drums": "storage/generated/complete_20260114/separated/no_drums.mp3",
    "generated_drums": "storage/generated/complete_20260114/generated/generated_drums.wav",
    "original_with_generated_drums": "storage/generated/complete_20260114/original_with_generated_drums.wav"
  },
  "processing_time": 45.2
}
```

### 单独功能

#### 分离鼓声
```bash
curl -X POST "http://localhost:8000/separation/separate" \
  -F "file=@your_song.mp3" \
  -F "chunk_duration=30"
```

#### 仅处理已上传的文件
```bash
# 先上传文件到 storage/uploaded/，然后处理
curl -X POST "http://localhost:8000/separation/separate_by_name" \
  -d "filename=your_song.mp3" \
  -d "chunk_duration=30"
```

#### 音乐分析
```bash
curl -X POST "http://localhost:8000/analysis/analyze" \
  -F "file=@your_song.mp3"
```

#### 生成鼓演奏
```bash
curl -X POST "http://localhost:8000/generation/generate" \
  -F "file=@your_song.mp3" \
  -F "style_hint=rock" \
  -F "complexity=0.6"
```

### 音轨管理 API

#### 列出分离结果
```bash
curl "http://localhost:8000/tracks/list"
# 返回 storage/uploaded/separated/ 中的音轨列表
```

#### 检查上传状态
```bash
curl "http://localhost:8000/tracks/status"
# 返回: has_uploaded, has_separated, 等状态信息
```

#### 获取音频文件
```bash
curl "http://localhost:8000/tracks/audio/drum.wav"
# 返回 storage/uploaded/separated/drum.wav 文件
```

#### 清除上传文件
```bash
curl -X POST "http://localhost:8000/separation/clear"
# 删除整个 storage/uploaded/ 目录
```

### YouTube 下载 API

#### 下载音频
```bash
curl -X POST "http://localhost:8000/youtube/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=...", "name": "my_track"}'
```

#### 下载并分离
```bash
curl -X POST "http://localhost:8000/youtube/separate" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=...", "chunk_size": 30}'
```

## 🎯 使用场景

### 1. 鼓手练习
- 获取歌曲的鼓部分（分离）
- 理解歌曲结构（分析）
- 生成练习伴奏（生成）

### 2. 音乐制作
- 创建鼓样本
- 快速原型
- 参考学习

### 3. 音乐教育
- 分析歌曲结构
- 节奏教学
- 风格识别

## 🔧 技术栈

### 后端
- **Python 3.10+**
- **PyTorch** + Metal 加速 (Apple Silicon)
- **Demucs** - 鼓声分离
- **Essentia** - 音乐描述符
- **Librosa** - 音频分析
- **FastAPI** - Web 服务
- **uv** - 依赖管理

### 前端 (计划)
- **Flutter** - 跨平台应用
- Web / iOS / Android 一套代码

## 📊 性能优化 (Apple Silicon)

### Metal 加速
```bash
# 自动检测并使用
uv run python -c "import torch; print(torch.backends.mps.is_available())"

# 手动指定
DEVICE=mps uv run uvicorn api.server:app --reload
```

### 依赖优化
- 使用预编译的 torch (支持 MPS)
- Demucs 从源码安装 (自动兼容)
- Essentia (可选，安装失败仍可使用核心功能)

### 内存管理
- 长音频自动分段处理 (默认 30秒/段)
- 模型懒加载
- 临时文件自动清理

## 🔧 故障排除

### 问题: Essentia 安装失败
```bash
# 解决方案 1: 使用 Homebrew
brew install essentia

# 解决方案 2: 跳过 Essentia
# 核心功能（分离和生成）不受影响
```

### 问题: 模型下载慢
```bash
# 首次运行会自动下载 (~1.5GB)
# 模型缓存在 storage/models/
# 可手动下载并放置在该目录
```

### 问题: 内存不足
```bash
# 降低分段时长
uv run drum-trainer complete song.mp3 --chunk-size 15
```

### 问题: Metal 不可用
```bash
# 检查 PyTorch 版本
uv run python -c "import torch; print(torch.__version__)"

# 应 >= 2.0.0
# 如果是 Intel Mac，会自动使用 CPU
```

## 📝 开发计划

### 已完成 ✅
- [x] Python 核心模块
- [x] Demucs 分离器
- [x] 音乐分析器 (风格/BPM/结构)
- [x] 段落检测器
- [x] 节奏识别器
- [x] 鼓生成器
- [x] FastAPI 服务
- [x] CLI 工具
- [x] Apple Silicon 优化
- [x] **Web UI 前端** (HTML/CSS/JS)
- [x] **音轨管理端点** (`/tracks/list`, `/tracks/status`, `/tracks/audio`)
- [x] **YouTube 下载集成** (保存到 `storage/uploaded/`)
- [x] **文件预览显示** (上传面板折叠时显示在现在播放卡片)
- [x] **分离结果查看** (`storage/uploaded/separated/` 子目录)
- [x] **清除功能** (删除整个 `storage/uploaded/` 目录)
- [x] **实时音频可视化** (频谱 + 波形)
- [x] **多轨同步播放** (支持同时播放多个分离音轨)

### 计划中 ⏳
- [ ] Flutter Web 前端 (开发中)
- [ ] iOS/Android App
- [ ] MIDI 导出
- [ ] 批量处理
- [ ] 离线缓存
- [ ] 高级 Fill 生成
- [ ] 智能编曲 (远期)
- [ ] Demo 文件展示功能 (未来计划)
- [ ] 音轨重命名/管理

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)

## 📄 许可证

MIT License

## 🎵 预期成果

完成安装后，您将获得：

✅ **Python API 服务** - 可独立运行
✅ **音乐理解能力** - 自动识别风格/结构/节奏
✅ **智能鼓生成** - 根据理解生成演奏
✅ **多种音频输出** - 仅鼓/混合/去鼓
✅ **Apple Silicon 优化** - Metal 加速

---

**开始使用**：
```bash
./scripts/install.sh
./scripts/run.sh
```

访问 http://localhost:8000/docs 查看完整 API 文档！
