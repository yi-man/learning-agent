#!/bin/bash

# Superpowers Skills 更新脚本（快捷方式）
# 这是 install-superpowers.sh 的快捷方式，专门用于更新

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"
exec "$SCRIPT_DIR/install-superpowers.sh"
