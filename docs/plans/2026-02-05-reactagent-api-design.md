# ReAct JSON API 设计文档

## 背景与目标
本项目已有 `/chat` 与 `/chat/openai` 对话端点，具备 session_id 维护历史的能力。本次新增一个 JSON ReAct 端点，复用 `OpenAIClient`，并提供受控工具调用与可选 trace，面向生产默认只返回最终答案。

目标：
- 新增 `/agents/react` 端点，采用 JSON ReAct 输出格式。
- 默认支持 `Calculator` 与 `Search` 两类工具。
- 继续使用 `session_id` 历史机制，仅保存 user/assistant 内容。
- 通过参数控制是否返回 trace。

非目标：
- 不引入额外的多智能体编排或长期记忆。
- 不持久化工具调用细节到历史。

## 接口设计（草案）
请求体（示意）：
- `messages`: 与 `/chat/openai` 同结构（role/content）
- `session_id`: 可选，若不传则自动生成
- `temperature` / `max_tokens` / `max_completion_tokens` / `reasoning_effort`
- `max_steps`: ReAct 最大步骤（默认 5）
- `return_trace`: 是否返回 trace（默认 false）
- `clear_history`: 是否清空历史（默认 false）

响应体（示意）：
- `content`: 最终答案
- `model`: 模型名称
- `session_id`: 会话 ID
- `trace`: 可选，仅在 `return_trace=true` 时返回

## 架构与组件
- 新增 `app/api/agents_react.py` 作为路由层。
- 新增 `app/agents/react_agent.py` 作为 ReAct 运行器（JSON 解析、步骤循环、错误追踪）。
- 新增 `app/agents/tools.py` 作为工具注册与执行层（受控白名单）。
- 复用 `app/models/openai_client.py` 做 LLM 调用，避免重复客户端逻辑。

## 数据流
1. API 接收请求 → 处理 `clear_history` 与 `session_id`。
2. 合并历史与当前消息（仅 user/assistant 内容）。
3. 运行 ReAct 循环：
   - 构建 JSON ReAct prompt（含工具说明）。
   - 解析 LLM 输出 JSON。
   - 若 `action.type=tool_call` → 执行工具 → 记录 observation。
   - 若 `action.type=finish` → 返回最终答案。
4. 写入历史（仅当前用户消息与最终答案）。
5. 根据 `return_trace` 返回 trace。

## 工具策略
- 默认注册 `Calculator` 与 `Search`，采用白名单。
- 工具执行统一封装：超时、异常返回标准错误字符串。
- 不在历史中记录工具调用，仅在 trace 中返回。

## 错误处理
- JSON 解析失败：返回 400，包含可读错误说明（不泄露 prompt）。
- 工具不存在或执行异常：作为 observation 写入 trace，并继续下一步（计入错误计数）。
- 连续错误超过阈值：提前结束，返回可读错误。
- LLM 调用失败：返回 500，保留统一错误信息格式。

## 测试策略
- 新增 API 测试覆盖：
  - 无 session_id → 自动生成并返回。
  - 有 session_id → 历史累积生效。
  - `return_trace=true` → 响应包含 trace。
  - 工具调用成功与失败分支。
- 单测/集成测试使用 `pytest` 与 `TestClient`（或 `httpx.AsyncClient`）进行端点验证。
