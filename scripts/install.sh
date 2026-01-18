#!/bin/bash

# Drum Trainer 安装脚本
# 优化 Apple Silicon (M系列芯片)

set -e

echo "🥁 Drum Trainer 安装脚本"
echo "=========================="

# 检测操作系统
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  警告: 此脚本针对 macOS 优化，其他系统可能需要手动安装"
fi

# 检测 Apple Silicon
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    echo "✅ 检测到 Apple Silicon (M系列芯片)"
    echo "   将使用 Metal 加速"
else
    echo "ℹ️  Intel Mac 或其他架构"
fi

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo ""
    echo "📦 安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env"
    echo "✅ uv 安装完成"
else
    echo "✅ uv 已安装"
fi

# 安装 Essentia 的特殊说明
echo ""
echo "⚠️  重要: Essentia 依赖"
echo "对于 Apple Silicon，Essentia 可能需要从源码编译"
echo "如果安装失败，可以跳过它（主要功能仍可用）"
read -p "继续安装？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "安装已取消"
    exit 1
fi

# 创建虚拟环境并安装
echo ""
echo "🔧 创建虚拟环境并安装依赖..."

# 导出环境变量以优化安装
export LDFLAGS="-L/opt/homebrew/lib"
export CPPFLAGS="-I/opt/homebrew/include"

# 安装依赖
uv sync --all-extras

echo ""
echo "✅ 依赖安装完成"

# 创建必要目录
mkdir -p storage/temp
mkdir -p storage/generated
mkdir -p storage/models

echo ""
echo "📁 创建目录结构"

# 下载 Demucs 模型（首次运行时）
echo ""
echo "📥 首次运行时将自动下载 Demucs 模型 (~1.5GB)"
echo "   模型将缓存在 storage/models/ 目录"

# 创建环境变量示例
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# Drum Trainer 配置
DEVICE=auto          # auto, mps, cuda, cpu
CHUNK_DURATION=30    # 长音频分段处理时长（秒）
MAX_FILE_SIZE=500    # 最大文件大小（MB）
LOG_LEVEL=info
EOF
    echo "✅ 创建 .env 配置文件"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "快速启动:"
echo "  1. 启动 API 服务: uv run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000"
echo "  2. 访问文档: http://localhost:8000/docs"
echo "  3. 使用 CLI: uv run drum-trainer info"
echo ""
echo "示例:"
echo "  # 分离鼓声"
echo "  uv run drum-trainer separate your_song.mp3 -o output/"
echo ""
echo "  # 音乐分析"
echo "  uv run drum-trainer analyze your_song.mp3"
echo ""
echo "  # 完整处理"
echo "  uv run drum-trainer complete your_song.mp3"
