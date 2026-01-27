#!/bin/bash

# Superpowers Skills 安装脚本
# 用于下载和安装 Superpowers skills 到 .cursor/skills/ 目录

set -e

echo "🚀 开始安装 Superpowers Skills..."

# 检查是否在项目根目录
if [ ! -f "README.md" ] && [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 创建目录
mkdir -p .cursor/skills .cursor/rules

# 临时克隆 Superpowers 仓库
TEMP_DIR=$(mktemp -d)
echo "📥 正在从 GitHub 下载 Superpowers skills..."
git clone --depth 1 https://github.com/obra/superpowers.git "$TEMP_DIR"

# 复制 skills
echo "📦 正在复制 skills..."
cp -r "$TEMP_DIR/skills"/* .cursor/skills/

# 清理临时文件
rm -rf "$TEMP_DIR"

# 统计安装的 skills 数量
SKILL_COUNT=$(ls -1 .cursor/skills/ | wc -l | tr -d ' ')

echo ""
echo "✅ Superpowers Skills 安装完成！"
echo "📊 已安装 $SKILL_COUNT 个 skills"
echo ""
echo "已安装的 skills:"
ls -1 .cursor/skills/ | sed 's/^/  - /'
echo ""
echo "下一步："
echo "1. Skills 已自动安装到 .cursor/skills/ 目录"
echo "2. Cursor 会自动识别这些 skills"
echo "3. 查看 README.md 了解如何使用 Superpowers 工作流"
echo ""
echo "💡 提示: 要更新 skills，重新运行此脚本即可"
