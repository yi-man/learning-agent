# Tool Retrieval (按需检索) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现方案 B：按 query 检索 top-k 工具，只将检索到的工具描述注入 prompt，从而在工具数量增加时保持上下文可控。

**Architecture:** 在现有 `ToolExecutor` 上增加可检索元数据（keywords/summary）、基于关键词重叠的评分与 top-k 选取；`ReActJSONAgent` 构建 prompt 时调用 `getToolsForQuery(question, history, top_k)` 替代 `getAvailableTools()`。执行仍按工具名从全量注册表查找，保证未出现在当轮 prompt 中的工具也可被调用（若模型从 history 得知名称）。

**Tech Stack:** Python 3.x，无新增依赖；检索采用纯关键词重叠评分（中英文均可）。

---

## Task 1: 扩展 ToolExecutor 的注册与检索

**Files:**
- Modify: `demos/agent-framework/tools.py`

**Step 1: 扩展 registerTool 支持可选 keywords**

- 签名改为 `registerTool(self, name, description, func, *, keywords=None)`。
- `keywords` 为可选字符串或字符串列表，用于检索；存为 `info["keywords"]`（归一化为字符串）。
- 保持 `getAvailableTools()` 行为不变（仍返回全量 `- name: description`）。

**Step 2: 实现 getToolsForQuery(query, history=None, top_k=10)**

- 输入：`query`（当前问题）、`history`（可选，可拼接进检索文本）、`top_k`。
- 对每个工具构造检索文本：`name + " " + description + " " + (keywords or "")`。
- 检索文本：`query + " " + (history or "")`。
- 评分：将 query（与 history）按空格和常见标点分词，在工具检索文本中统计出现次数（不区分大小写），得分 = 匹配词数；可选用对数或长度归一化。
- 按得分降序排序，取前 `top_k`；若工具数 ≤ top_k 则全返回。
- 返回：与 `getAvailableTools()` 相同格式的字符串，但只包含被选中的工具（`- name: description`）。

**Step 3: 运行现有 tests**

- Run: `pytest tests/demos/agent-framework/test_tools.py -v`
- Expected: PASS（registerTool 兼容旧调用：keywords 默认 None）。

---

## Task 2: 为工具检索编写测试

**Files:**
- Modify: `tests/demos/agent-framework/test_tools.py`

**Step 1: 编写检索测试**

- `test_get_tools_for_query_returns_subset`: 注册 Search、Calculator，query 含「计算」，top_k=1，返回的字符串应包含 Calculator 且仅 1 个工具。
- `test_get_tools_for_query_respects_top_k`: 注册 3 个工具，query 通用，top_k=2，返回恰好 2 个工具。
- `test_get_tools_for_query_fallback_all_when_few_tools`: 注册 2 个工具，top_k=10，返回 2 个工具（全量）。

**Step 2: 运行并确保通过**

- Run: `pytest tests/demos/agent-framework/test_tools.py -v`

---

## Task 3: ReActJSONAgent 使用 getToolsForQuery

**Files:**
- Modify: `demos/agent-framework/react_json.py`

**Step 1: 在 run() 中替换 tools 来源**

- 当前：`tools_desc = self.tool_executor.getAvailableTools()`。
- 改为：`tools_desc = self.tool_executor.getToolsForQuery(question, history=history_str, top_k=10)`（或可配置的 top_k）。
- 其余逻辑不变（错误恢复中「可用工具列表」已基于当轮 `tools_desc`，无需改）。

**Step 2: 运行相关测试**

- Run: `pytest tests/demos/agent-framework/ -v`
- Expected: 现有 test 仍通过；若有集成测试则一并通过。

---

## Task 4: 提交与文档

- 将上述改动提交，commit message 示例：`feat(agent-framework): add tool retrieval by query (getToolsForQuery)`。
- 在 `docs/plans/2026-01-29-tool-retrieval.md` 末尾添加「Done」小节，记录完成的任务与可选后续（如 embedding 检索、top_k 可配置）。
