# AutoGen 动态回退机制 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `autogen_software_team.py` 中实现「动态回退」：当任意角色在消息中包含回退关键词时，下一棒强制为 ProductManager，否则按固定顺序轮询（PM → Engineer → CodeReviewer → UserProxy）。

**Architecture:** 用 SelectorGroupChat 替代 RoundRobinGroupChat；通过自定义 selector_func(messages) 决定下一发言者：先检测最后一条消息是否包含回退关键词，若包含则返回 "ProductManager"，否则按 participants 顺序做 round-robin。从最后一条消息取可读文本时兼容 TextMessage、ToolCallSummaryMessage 等（content 或 to_text()）。不新增依赖与文件。

**Tech Stack:** Python 3, autogen-agentchat (SelectorGroupChat), 现有 OpenAIChatCompletionClient / TextMentionTermination。

**参考设计:** [docs/plans/2026-02-03-autogen-rollback-design.md](docs/plans/2026-02-03-autogen-rollback-design.md)

---

## Task 1: 回退关键词与「最后一条消息文本」辅助逻辑

**Files:**

- Modify: `demos/AutoGenDemo/autogen_software_team.py`（文件顶部 import 后、`create_openai_model_client` 前）

**Step 1: 添加常量和辅助函数**

在 `load_dotenv()` 之后、`def create_openai_model_client():` 之前插入：

```python
# 动态回退：当消息包含以下任一关键词时，下一棒交给 ProductManager
ROLLBACK_KEYWORDS = (
    "请产品经理重新审核",
    "需求变更",
    "REVIEW_BY_PM",
)


def _get_last_message_text(message) -> str:
    """从任意消息类型中提取可读文本，用于回退关键词检测。"""
    if hasattr(message, "to_text") and callable(getattr(message, "to_text")):
        out = message.to_text()
        return out if out is not None else ""
    return getattr(message, "content", "") or ""
```

**Step 2: 保存并确认无语法错误**

Run: `python -m py_compile demos/AutoGenDemo/autogen_software_team.py`  
Expected: 无输出（编译成功）

**Step 3: Commit**

```bash
git add demos/AutoGenDemo/autogen_software_team.py
git commit -m "feat(autogen-demo): add rollback keywords and last-message text helper"
```

---

## Task 2: 实现下一棒选择逻辑（round-robin + 回退）

**Files:**

- Modify: `demos/AutoGenDemo/autogen_software_team.py`

**Step 1: 添加 select_next_speaker 函数**

在 `_get_last_message_text` 之后、`def create_openai_model_client():` 之前添加：

```python
def select_next_speaker(messages, participant_names):
    """
    根据消息历史决定下一发言者。
    - 若最后一条消息包含回退关键词，返回 ProductManager。
    - 否则按 participant_names 顺序轮询。
    participant_names 顺序须为 [ProductManager, Engineer, CodeReviewer, UserProxy]。
    """
    if not messages:
        return participant_names[0] if participant_names else "ProductManager"
    last = messages[-1]
    last_source = getattr(last, "source", None) or ""
    text = _get_last_message_text(last)
    if any(kw in text for kw in ROLLBACK_KEYWORDS):
        return "ProductManager"
    if last_source == "user":
        return participant_names[0]
    try:
        idx = participant_names.index(last_source)
    except ValueError:
        return participant_names[0]
    return participant_names[(idx + 1) % len(participant_names)]
```

**Step 2: 确认无语法错误**

Run: `python -m py_compile demos/AutoGenDemo/autogen_software_team.py`  
Expected: 无输出（编译成功）

**Step 3: Commit**

```bash
git add demos/AutoGenDemo/autogen_software_team.py
git commit -m "feat(autogen-demo): add select_next_speaker for round-robin and rollback"
```

---

## Task 3: 使用 SelectorGroupChat 并接入 selector_func

**Files:**

- Modify: `demos/AutoGenDemo/autogen_software_team.py`

**Step 1: 修改 import**

将：

```python
from autogen_agentchat.teams import RoundRobinGroupChat
```

改为：

```python
from autogen_agentchat.teams import SelectorGroupChat
```

**Step 2: 在 run_software_development_team 中替换团队构造**

将：

```python
    # 创建团队聊天
    team_chat = RoundRobinGroupChat(
        participants=[product_manager, engineer, code_reviewer, user_proxy],
        termination_condition=termination,
        max_turns=20,  # 增加最大轮次
    )
```

改为：

```python
    participants = [product_manager, engineer, code_reviewer, user_proxy]
    participant_names = [p.name for p in participants]

    def selector_func(messages):
        return select_next_speaker(messages, participant_names)

    team_chat = SelectorGroupChat(
        participants=participants,
        model_client=model_client,
        termination_condition=termination,
        selector_func=selector_func,
        max_turns=20,
    )
```

**Step 3: 运行脚本做一次无回退的回归验证**

Run: `cd demos/AutoGenDemo && python -c "
import asyncio
from autogen_software_team import run_software_development_team
asyncio.run(run_software_development_team())
"`

Expected: 能正常跑完（需配置 .env 中的 LLM_API_KEY 等）。控制台可见发言顺序为 ProductManager → Engineer → CodeReviewer → UserProxy 循环，最终出现 TERMINATE。若环境未配置，可只做语法检查：`python -m py_compile demos/AutoGenDemo/autogen_software_team.py`。

**Step 4: Commit**

```bash
git add demos/AutoGenDemo/autogen_software_team.py
git commit -m "feat(autogen-demo): switch to SelectorGroupChat with rollback selector_func"
```

---

## Task 4: 为 PM / Engineer / CodeReviewer 补充 system_message（回退提示）

**Files:**

- Modify: `demos/AutoGenDemo/autogen_software_team.py`

**Step 1: 产品经理 system_message 末尾补充**

在 `create_product_manager` 中，将 system_message 的结尾从：

```python
请简洁明了地回应，并在分析完成后说"请工程师开始实现"。"""
```

改为：

```python
请简洁明了地回应，并在分析完成后说"请工程师开始实现"。

若需求有变更，可要求工程师或审查员在回复中写明「请产品经理重新审核」，以便重新分析需求。"""
```

**Step 2: 工程师 system_message 末尾补充**

在 `create_engineer` 中，将 system_message 的结尾从：

```python
请提供完整的可运行代码，并在完成后说"请代码审查员检查"。"""
```

改为：

```python
请提供完整的可运行代码，并在完成后说"请代码审查员检查"。

若实现过程中发现需求与当前实现不一致或需求变更，请在回复末尾说明并写「请产品经理重新审核」。"""
```

**Step 3: 代码审查员 system_message 末尾补充**

在 `create_code_reviewer` 中，将 system_message 的结尾从：

```python
请提供具体的审查意见，完成后说"代码审查完成，请用户代理测试"。"""
```

改为：

```python
请提供具体的审查意见，完成后说"代码审查完成，请用户代理测试"。

若发现实现与需求文档不符或存在需求歧义，请建议交由产品经理重新确认，并在回复中写「请产品经理重新审核」。"""
```

**Step 4: 确认无语法错误**

Run: `python -m py_compile demos/AutoGenDemo/autogen_software_team.py`  
Expected: 无输出（编译成功）

**Step 5: Commit**

```bash
git add demos/AutoGenDemo/autogen_software_team.py
git commit -m "docs(autogen-demo): add rollback hint to PM, Engineer, CodeReviewer system_message"
```

---

## 验收（手动）

- **无回退：** 使用现有比特币任务跑一遍，顺序为 PM → Engineer → CodeReviewer → UserProxy 循环至 TERMINATE。
- **有回退：** 在任务中或临时在 CodeReviewer 的 system_message 中强调「发现与需求不符时务必写『请产品经理重新审核』」，跑一遍，确认出现该句后下一棒为 ProductManager，之后顺序恢复。

---

## 执行选项

计划已保存到 `docs/plans/2026-02-03-autogen-rollback-implementation.md`。两种执行方式：

1. **Subagent-Driven（本会话）**：按任务逐个执行，每任务后 review，迭代快。

   - **需用子技能：** @superpowers:subagent-driven-development

2. **Parallel Session（新会话）**：在独立会话中打开 worktree，用 executing-plans 按检查点批量执行。
   - **需用子技能：** 新会话使用 @superpowers:executing-plans

你选哪种？
