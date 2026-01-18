#!/bin/bash

# 启动 Drum Trainer API 服务

cd "$(dirname "$0")/.."

echo "🚀 启动 Drum Trainer API 服务..."
echo ""

# 检查依赖
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: uv 未安装"
    echo "请运行: ./scripts/install.sh"
    exit 1
fi

# 启动服务
uv run uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
