# Project Instructions (learning-agent)

你是这个仓库里的 coding agent。你的目标是：快速理解项目结构与功能，在不破坏现有行为的前提下完成需求，并遵循本项目既定的依赖与测试规范。

## 偏好（必须遵守）
- **回复语言**：默认使用**中文**回复用户（代码注释、变量名、文档可中英混用，以可读为准）。
- **强制工作树**：任何非微小改动（新功能/重构/跨文件修改/新增依赖/影响行为的修复）必须先用 `using-git-worktrees` skill 创建独立 git worktree，在隔离工作区开发，完成后再合并回主分支。
- **强制写计划（开发门槛）**：实现任何需求之前，必须使用 **`writing-plans` skill** 产出实施计划文档（写入 `docs/plans/YYYY-MM-DD-<topic>-implementation.md` 或项目约定路径）。**没有计划文档，不允许开始开发/改代码**。
- **强制 TDD**：本仓库强制采用 TDD：先写失败的测试 → 写最小实现让测试通过 → 重构并保持测试通过。不得在未写测试前实现功能逻辑。

## TL;DR
- 技术栈：FastAPI + Pydantic Settings + httpx + OpenAI SDK（可选）
- 主要能力：提供对话 API（支持 session_id 的内存上下文）
- 首选工作流：遵循 `.cursor/rules/` 中的 Superpowers 流程与依赖/测试规则；**强制 writing-plans → worktree → TDD**
- 常用命令：优先用 `make`（见 Makefile）

## Repository Map
- `app/main.py`
  - FastAPI 入口，注册路由：
    - `app.api.chat` → `/chat`
    - `app.api.chat_openai` → `/chat/openai`
  - 还有 `GET /` 和 `GET /health`
- `app/config.py`
  - 使用 `pydantic-settings` 从 `.env` / 环境变量读取配置（`Settings`）
- `app/api/chat.py`
  - 豆包 httpx 客户端路径 `/chat`（JSON body 版 + 简化版）
  - 依赖 `app/api/chat_history.py` 做内存历史
- `app/api/chat_openai.py`
  - OpenAI SDK 客户端路径 `/chat/openai`（JSON body 版 + 简化版）
  - 可通过 `LLM_BASE_URL` 调用兼容 OpenAI API 的供应商
- `app/api/chat_history.py`
  - **内存**对话历史（按 `session_id`），最多保留最近 `MAX_HISTORY_MESSAGES=20`
  - 注意：进程重启会丢失历史；不是持久化存储
- `app/models/llm_client.py`
  - `BaseLLMClient` 抽象 + `DoubaoClient`（httpx，支持 stream）
- `app/models/openai_client.py`
  - `OpenAIClient`（AsyncOpenAI，支持 stream）
- `.cursor/rules/`
  - 项目级规则（持续上下文）；包含依赖管理与测试验证等强制规范
- `requirements.txt`
  - Python 依赖的唯一来源（新增依赖必须更新这里）
- `env.example`
  - 环境变量示例（建议从它生成 `.env`）

## Demos（`demos/`）
示例代码与学习案例，各自有入口和依赖说明；修改 demos 时也要遵守 writing-plans + worktree + TDD。

- **`demos/demo1/`** — 旅行助手（天气 + 景点推荐）
  - 入口：`main.py`（直接运行）
  - 能力：Thought-Action 格式调用工具；`get_weather(city)`、`get_attraction(city, weather)`
  - 依赖：`llm_client.py`（OpenAI 兼容客户端）、`weather.py`、`search_attraction.py`；环境变量见根目录 `.env`（LLM_*、TAVILY_API_KEY 等）
  - 说明：`Readme.md` 仅简要说明「天气预报」

- **`demos/AutoGenDemo/`** — AutoGen 多智能体软件开发团队
  - 入口：`autogen_software_team.py`（`python autogen_software_team.py`）
  - 能力：ProductManager、Engineer、CodeReviewer、UserProxy 协作；需求 → 代码 → 审查 → 用户测试；支持质量监控（循环检测）与回退关键词触发 ProductManager 重新审核
  - 依赖：`autogen_agentchat`、`autogen_ext.models.openai` 等；本目录有 `requirements.txt`、`env.example`；根目录 `.env` 的 LLM_* 会被使用
  - 其他：`output.py` 为团队生成的示例应用（如比特币价格 Streamlit）；详见 `README.md`

- **`demos/agent-framework/`** — 自建 Agent 范式（无独立入口，按脚本运行）
  - `react.py`：ReAct 范式，Thought-Action 文本解析，`ToolExecutor` + `search` 等工具
  - `react_json.py`：ReAct 的 JSON 版，结构化 `thought`/`action`，含 `ErrorTracker` 重试
  - `plan_and_solve.py`：Plan-and-Solve，先 LLM 生成步骤列表再逐步执行
  - `refleaction.py`：Reflection 相关逻辑（自反思/纠错）
  - `tools.py`：工具定义与 `ToolExecutor`
  - `llm_client.py`：`HelloAgentsLLM` 等，供上述脚本共用
  - `error_tracker.py`：错误追踪与重试，被 `react_json.py` 等使用
  - 说明：依赖根目录或各自 `.env`；与 `app/` 无耦合，仅供学习与实验

## Behavior / Product Intent
- 这是一个学习型/可扩展的 LLM API 服务骨架：
  - `/chat` 走豆包（httpx 直连 `LLM_API_ENDPOINT`）
  - `/chat/openai` 走 OpenAI SDK（可通过 `LLM_BASE_URL` 指向兼容 OpenAI 的服务）
- 对话上下文通过 `session_id` 维护：
  - 客户端首次不传 `session_id` → 服务端生成
  - 后续请求带 `session_id` → 合并历史 + 当前 messages
  - 可用 `clear_history` 清除某个会话的历史（如果该端点/参数存在）

## API Endpoints (high-signal)
- `POST /chat`
  - body: `messages`, 可选 `session_id`, `temperature`, `max_tokens`/`max_completion_tokens`, `reasoning_effort`, `stream`, `clear_history`
  - returns: `content`, `model`, `session_id`
- `POST /chat/simple`
  - query: `message`, 可选 `session_id`
- `POST /chat/openai`
- `POST /chat/openai/simple`
- `GET /health`, `GET /`

## Configuration (env)
配置由 `app/config.py` 定义，优先使用以下变量名（见 `env.example`）：
- `LLM_API_KEY`（必填）
- `LLM_API_ENDPOINT`（默认豆包 endpoint）
- `LLM_MODEL_ID`（默认 `doubao-seed-1-6-lite-251015`）
- `LLM_BASE_URL`（可选：OpenAI SDK 的 base_url，用于兼容 OpenAI API 的供应商）
- `LLM_TIMEOUT`（默认 60）
- `API_HOST` / `API_PORT`

注意：不要把真实密钥写入仓库；`.env` 应视为敏感文件。

## Local Dev / Commands
优先使用 `Makefile`（仓库内有 `make setup/dev/test/...`）：
- `make setup`：创建虚拟环境、安装依赖、创建 `.env`（从 `env.example`）
- `make dev`：启动服务（uvicorn reload）
- `make test`：运行测试
- `make test-cov`：覆盖率
- `make lint` / `make lint-fix` / `make format` / `make type-check`：如果对应工具已加入依赖则启用

## Non-negotiables (来自项目规则)
- 新增/更新 Python 依赖：**只能**改 `requirements.txt`，再 `pip install -r requirements.txt`
- 完成代码修改后：必须运行测试自测（至少 `pytest -v`，或按 Makefile 的 test 目标）
- 修复某个失败命令后：必须运行**完全相同**的命令验证

## Change Guidelines
- 尽量保持 API 兼容：不要随意改动请求/响应字段名
- 任何对「上下文/历史」的变更，都要明确是否会影响：
  - `session_id` 生成逻辑
  - 历史合并策略
  - 最大历史条数与 token 风险
- 对外依赖（LLM provider）尽量抽象在 `app/models/`，API 层只做参数解析与错误处理
