#!/bin/bash

# AI Agent Learning 项目初始化脚本

set -e

echo "🚀 开始初始化 AI Agent Learning 项目..."

# 检查 Python 版本
echo "📋 检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "ℹ️  虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "⬆️  升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "📥 安装项目依赖..."
pip install -r requirements.txt

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件"
    if [ -f "env.example" ]; then
        echo "📝 从 env.example 创建 .env 文件..."
        cp env.example .env
        echo "✅ .env 文件已创建，请编辑 .env 文件填入你的 API Key"
    else
        echo "⚠️  未找到 env.example 文件"
    fi
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "✨ 项目初始化完成！"
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，填入你的火山引擎 API Key"
echo "2. 运行项目: uvicorn app.main:app --reload"
echo "3. 访问 API 文档: http://localhost:8000/docs"
echo ""
echo "提示: 每次使用前需要激活虚拟环境: source venv/bin/activate"
