#!/bin/bash

# Superpowers Skills 安装/更新脚本
# 用于下载和安装/更新 Superpowers skills 到 .cursor/skills/ 目录

set -e

# 检查是否在项目根目录
if [ ! -f "README.md" ] && [ ! -f "requirements.txt" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查是否已安装
IS_UPDATE=false
if [ -d ".cursor/skills" ] && [ "$(ls -A .cursor/skills 2>/dev/null)" ]; then
    IS_UPDATE=true
    OLD_COUNT=$(ls -1 .cursor/skills/ 2>/dev/null | wc -l | tr -d ' ')
    echo "📋 检测到已安装的 Superpowers Skills ($OLD_COUNT 个)"
    echo "🔄 开始更新..."
else
    echo "🚀 开始安装 Superpowers Skills..."
fi

# 创建目录
mkdir -p .cursor/skills .cursor/rules

# 临时克隆 Superpowers 仓库
TEMP_DIR=$(mktemp -d)
echo "📥 正在从 GitHub 下载最新版本的 Superpowers skills..."
git clone --depth 1 https://github.com/obra/superpowers.git "$TEMP_DIR"

# 获取版本信息
COMMIT_HASH=$(cd "$TEMP_DIR" && git rev-parse --short HEAD)
COMMIT_DATE=$(cd "$TEMP_DIR" && git log -1 --format=%ci | cut -d' ' -f1)

# 备份现有 skills（如果存在）
if [ "$IS_UPDATE" = true ]; then
    BACKUP_DIR=".cursor/skills.backup.$(date +%Y%m%d_%H%M%S)"
    echo "💾 备份现有 skills 到 $BACKUP_DIR"
    cp -r .cursor/skills "$BACKUP_DIR"
    echo "✅ 备份完成"
fi

# 复制 skills
echo "📦 正在复制 skills..."
rm -rf .cursor/skills/*
cp -r "$TEMP_DIR/skills"/* .cursor/skills/

# 清理临时文件
rm -rf "$TEMP_DIR"

# 统计安装的 skills 数量
SKILL_COUNT=$(ls -1 .cursor/skills/ | wc -l | tr -d ' ')

echo ""
if [ "$IS_UPDATE" = true ]; then
    echo "✅ Superpowers Skills 更新完成！"
    echo "📊 更新前: $OLD_COUNT 个 skills"
    echo "📊 更新后: $SKILL_COUNT 个 skills"
else
    echo "✅ Superpowers Skills 安装完成！"
    echo "📊 已安装 $SKILL_COUNT 个 skills"
fi

echo ""
echo "📌 版本信息:"
echo "  - Commit: $COMMIT_HASH"
echo "  - 日期: $COMMIT_DATE"
echo ""
echo "已安装的 skills:"
ls -1 .cursor/skills/ | sed 's/^/  - /'
echo ""

if [ "$IS_UPDATE" = true ]; then
    echo "💡 提示:"
    echo "  - 旧版本已备份到: $BACKUP_DIR"
    echo "  - 如需恢复，可以手动复制备份目录的内容"
    echo "  - 备份目录可以安全删除"
else
    echo "下一步："
    echo "1. Skills 已自动安装到 .cursor/skills/ 目录"
    echo "2. Cursor 会自动识别这些 skills"
    echo "3. 查看 README.md 了解如何使用 Superpowers 工作流"
fi

echo ""
echo "🔄 要再次更新，重新运行此脚本即可: ./scripts/install-superpowers.sh"
