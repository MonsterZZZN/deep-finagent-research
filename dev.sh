#!/bin/bash
# ============================================================
# finagent-research 开发助手脚本
# 用法：bash dev.sh <命令>
#   bash dev.sh up        # 拉代码 + 同步依赖
#   bash dev.sh serve     # 启动研究服务（8001）
#   bash dev.sh install   # 装全部依赖
# ============================================================

cd "$(dirname "$0")" || exit 1
if [ -d venv ]; then
    source venv/bin/activate
fi

case "$1" in
  up)
    echo "📥 拉取最新代码..."
    if ! git pull; then
        echo "❌ 拉取失败（网络？），代码未更新"
        exit 1
    fi
    echo "📦 同步依赖..."
    pip install -q -r requirements.txt || echo "⚠️  部分依赖安装有问题"
    echo "✅ 更新完成"
    ;;
  install)
    pip install -r requirements.txt
    ;;
  serve)
    echo "🚀 启动 finagent-research 服务..."
    cd src && python -m deep_research.api.server
    ;;
  *)
    echo "用法: bash dev.sh [up|install|serve]"
    ;;
esac
