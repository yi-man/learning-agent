.PHONY: help setup dev install test test-cov test-watch test-file clean format lint type-check install-superpowers update-superpowers docs serve-docs check-env

# 变量定义
PYTHON := python3
VENV := venv
VENV_BIN := $(VENV)/bin
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest
PYTHON_CMD := $(VENV_BIN)/python
UVICORN := $(VENV_BIN)/uvicorn

# 默认目标：显示帮助信息
.DEFAULT_GOAL := help

help: ## 显示所有可用任务和说明
	@echo "AI Agent Learning - Makefile 命令"
	@echo ""
	@echo "基础任务:"
	@echo "  make setup             初始化项目（创建虚拟环境、安装依赖、创建 .env）"
	@echo "  make dev               启动应用（开发模式）"
	@echo "  make install           安装依赖（从 requirements.txt）"
	@echo ""
	@echo "测试任务:"
	@echo "  make test              运行所有测试"
	@echo "  make test-cov          运行测试并生成覆盖率报告"
	@echo "  make test-watch        监控文件变化并自动运行测试"
	@echo "  make test-file FILE=   运行指定测试文件（例如: make test-file FILE=tests/test_main.py）"
	@echo ""
	@echo "清理任务:"
	@echo "  make clean             清理所有缓存文件（Python 缓存、pytest 缓存、覆盖率报告等）"
	@echo ""
	@echo "代码质量任务:"
	@echo "  make format            格式化代码（使用 black，如果已安装）"
	@echo "  make lint              代码检查（使用 ruff，如果已安装）"
	@echo "  make type-check        类型检查（使用 mypy，如果已安装）"
	@echo ""
	@echo "Superpowers 管理:"
	@echo "  make install-superpowers   安装/更新 Superpowers skills"
	@echo "  make update-superpowers    更新 Superpowers skills（快捷方式）"
	@echo ""
	@echo "文档任务:"
	@echo "  make docs              生成 API 文档（如果配置了文档工具）"
	@echo "  make serve-docs        本地启动文档服务器"
	@echo ""
	@echo "辅助任务:"
	@echo "  make check-env         检查环境配置（Python 版本、虚拟环境、.env 文件）"
	@echo "  make help              显示此帮助信息"
	@echo ""

# 检查虚拟环境是否存在
check-venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "❌ 虚拟环境不存在，请先运行 'make setup' 初始化项目"; \
		exit 1; \
	fi

# 检查 .env 文件是否存在
check-env-file:
	@if [ ! -f ".env" ]; then \
		echo "⚠️  警告: 未找到 .env 文件"; \
		echo "请创建 .env 文件并填入你的 API Key（参考 env.example）"; \
	fi

setup: ## 初始化项目（创建虚拟环境、安装依赖、创建 .env）
	@echo "🚀 开始初始化 AI Agent Learning 项目..."
	@echo "📋 检查 Python 版本..."
	@$(PYTHON) --version
	@if [ ! -d "$(VENV)" ]; then \
		echo "📦 创建虚拟环境..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "✅ 虚拟环境创建成功"; \
	else \
		echo "ℹ️  虚拟环境已存在，跳过创建"; \
	fi
	@echo "🔧 升级 pip..."
	@$(PIP) install --upgrade pip
	@echo "📥 安装项目依赖..."
	@$(PIP) install -r requirements.txt
	@if [ ! -f ".env" ]; then \
		echo "⚠️  未找到 .env 文件"; \
		if [ -f "env.example" ]; then \
			echo "📝 从 env.example 创建 .env 文件..."; \
			cp env.example .env; \
			echo "✅ .env 文件已创建，请编辑 .env 文件填入你的 API Key"; \
		else \
			echo "⚠️  未找到 env.example 文件"; \
		fi; \
	else \
		echo "✅ .env 文件已存在"; \
	fi
	@echo ""
	@echo "✨ 项目初始化完成！"
	@echo ""
	@echo "下一步："
	@echo "1. 编辑 .env 文件，填入你的 API Key"
	@echo "2. 运行项目: make dev"
	@echo "3. 访问 API 文档: http://localhost:8000/docs"
	@echo ""

install: check-venv ## 安装依赖（从 requirements.txt）
	@echo "📥 安装项目依赖..."
	@$(PIP) install -r requirements.txt
	@echo "✅ 依赖安装完成"

dev: check-venv check-env-file ## 启动应用（开发模式）
	@echo "🚀 启动 AI Agent Learning..."
	@echo "访问 http://localhost:8000/docs 查看 API 文档"
	@echo "按 Ctrl+C 停止服务"
	@echo ""
	@$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

test: check-venv ## 运行所有测试
	@echo "🧪 运行测试..."
	@$(PYTEST) -v

test-cov: check-venv ## 运行测试并生成覆盖率报告
	@echo "🧪 运行测试并生成覆盖率报告..."
	@$(PYTEST) --cov=app --cov-report=html --cov-report=term -v
	@echo ""
	@echo "✅ 覆盖率报告已生成: htmlcov/index.html"

test-watch: check-venv ## 监控文件变化并自动运行测试
	@echo "👀 监控文件变化并自动运行测试..."
	@echo "按 Ctrl+C 停止监控"
	@$(PYTEST) -v --looponfail

test-file: check-venv ## 运行指定测试文件（使用: make test-file FILE=tests/test_main.py）
	@if [ -z "$(FILE)" ]; then \
		echo "❌ 错误: 请指定测试文件，例如: make test-file FILE=tests/test_main.py"; \
		exit 1; \
	fi
	@echo "🧪 运行测试文件: $(FILE)"
	@$(PYTEST) -v $(FILE)

clean: ## 清理所有缓存文件
	@echo "🧹 清理缓存文件..."
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@rm -rf .pytest_cache 2>/dev/null || true
	@rm -rf .coverage .coverage.* 2>/dev/null || true
	@rm -rf htmlcov 2>/dev/null || true
	@echo "✅ 缓存清理完成"

format: check-venv ## 格式化代码（使用 black，如果已安装）
	@echo "🎨 格式化代码..."
	@if $(VENV_BIN)/python -c "import black" 2>/dev/null; then \
		$(VENV_BIN)/black . --exclude=venv; \
		echo "✅ 代码格式化完成"; \
	else \
		echo "⚠️  black 未安装，跳过格式化"; \
		echo "提示: 如需使用格式化功能，请在 requirements.txt 中添加 black"; \
	fi

lint: check-venv ## 代码检查（使用 ruff，如果已安装）
	@echo "🔍 代码检查..."
	@if command -v $(VENV_BIN)/ruff >/dev/null 2>&1; then \
		$(VENV_BIN)/ruff check . --exclude=venv; \
		echo "✅ 代码检查完成"; \
	else \
		echo "⚠️  ruff 未安装，跳过代码检查"; \
		echo "提示: 如需使用代码检查功能，请在 requirements.txt 中添加 ruff"; \
	fi

type-check: check-venv ## 类型检查（使用 mypy，如果已安装）
	@echo "🔎 类型检查..."
	@if $(VENV_BIN)/python -c "import mypy" 2>/dev/null; then \
		$(VENV_BIN)/mypy app --ignore-missing-imports; \
		echo "✅ 类型检查完成"; \
	else \
		echo "⚠️  mypy 未安装，跳过类型检查"; \
		echo "提示: 如需使用类型检查功能，请在 requirements.txt 中添加 mypy"; \
	fi

install-superpowers: ## 安装/更新 Superpowers skills
	@echo "📦 安装/更新 Superpowers skills..."
	@bash scripts/install-superpowers.sh

update-superpowers: ## 更新 Superpowers skills（快捷方式）
	@echo "🔄 更新 Superpowers skills..."
	@bash scripts/update-superpowers.sh

docs: check-venv ## 生成 API 文档（如果配置了文档工具）
	@echo "📚 生成 API 文档..."
	@echo "⚠️  文档生成功能尚未配置"
	@echo "提示: FastAPI 自动生成 API 文档，访问 http://localhost:8000/docs 查看"

serve-docs: check-venv ## 本地启动文档服务器
	@echo "📚 启动文档服务器..."
	@echo "⚠️  文档服务器功能尚未配置"
	@echo "提示: FastAPI 自动生成 API 文档，运行 'make dev' 后访问 http://localhost:8000/docs"

check-env: ## 检查环境配置
	@echo "🔍 检查环境配置..."
	@echo "Python 版本:"
	@$(PYTHON) --version || echo "❌ Python 未安装或不在 PATH 中"
	@echo ""
	@echo "虚拟环境:"
	@if [ -d "$(VENV)" ]; then \
		echo "✅ 虚拟环境存在: $(VENV)"; \
		echo "   Python 版本: $$($(PYTHON_CMD) --version 2>/dev/null || echo '未激活')"; \
	else \
		echo "❌ 虚拟环境不存在，运行 'make setup' 初始化"; \
	fi
	@echo ""
	@echo ".env 文件:"
	@if [ -f ".env" ]; then \
		echo "✅ .env 文件存在"; \
	else \
		echo "⚠️  .env 文件不存在，运行 'make setup' 创建"; \
	fi
	@echo ""
	@echo "依赖检查:"
	@if [ -d "$(VENV)" ]; then \
		$(PIP) list --format=freeze 2>/dev/null | head -5 2>/dev/null || echo "⚠️  无法列出已安装的包"; \
	fi
