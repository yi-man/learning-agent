# AutoGen 对话质量监控 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `autogen_software_team.py` 中增加「对话质量监控」：检测发言者序列循环，检测到异常时强制下一棒为 ProductManager，并打结构化日志；与现有回退关键词逻辑共存（先质量异常 → 再回退关键词 → 再轮询）。

**Architecture:** 在现有 `select_next_speaker(messages, participant_names)` 前增加 `quality_check(messages, participant_names) -> (bool, str | None)`。循环检测：从 messages 仅取 `source in participant_names` 得到发言者序列（不包含 user），若长度 ≥ 2*K 且最近 K 条与再前 K 条完全一致则判为循环，返回 (True, "loop")；否则 (False, None)。select_next_speaker 内先调用 quality_check，若为 True 则打日志并返回 "ProductManager"，再执行原有回退关键词与轮询逻辑。不新增依赖与文件；偏离检测首版不实现（接口可留空返回 False）。

**Tech Stack:** Python 3, autogen-agentchat (SelectorGroupChat 已有), logging 标准库。

**设计依据:** 前述 brainstorming + 继续分析（循环精确规则、可观测性）；实施完成后可将设计写入 `docs/plans/2026-02-04-autogen-conversation-quality-monitor-design.md`。

---

## Task 1: 实现 quality_check（仅循环检测）并写测试

**Files:**

- Create: `tests/demos/AutoGenDemo/__init__.py`（空文件或仅 `# AutoGen demo tests`）
- Create: `tests/demos/AutoGenDemo/test_autogen_quality.py`
- Modify: `demos/AutoGenDemo/autogen_software_team.py`（在 `select_next_speaker` 之前添加 `quality_check`）

**Step 1: 写失败的测试**

在项目根目录下创建 `tests/demos/AutoGenDemo/test_autogen_quality.py`，内容如下（用简单对象模拟 message，仅需 `source` 属性）：

```python
"""对话质量监控：quality_check 与 select_next_speaker 集成测试"""
import sys
from pathlib import Path

# 保证可导入 demos/AutoGenDemo 下的模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "demos" / "AutoGenDemo"))

from autogen_software_team import quality_check, select_next_speaker

PARTICIPANT_NAMES = ["ProductManager", "Engineer", "CodeReviewer", "UserProxy"]


def _msg(source: str):
    """构造仅含 source 的模拟消息"""
    m = type("Msg", (), {"source": source})()
    return m


def test_quality_check_no_loop_when_insufficient_messages():
    """消息不足 2*K 时不判循环"""
    K = len(PARTICIPANT_NAMES)  # 4
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 1]  # 仅 4 条
    has_anomaly, reason = quality_check(messages, PARTICIPANT_NAMES)
    assert has_anomaly is False
    assert reason is None


def test_quality_check_no_loop_when_sequence_differs():
    """最近 K 条与前 K 条不一致时不判循环"""
    # 两轮顺序：PM,E,CR,UP,PM,E,CR,UserProxy 但最后一条故意不同
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 2]
    messages[-1] = _msg("Engineer")  # 打破重复
    has_anomaly, reason = quality_check(messages, PARTICIPANT_NAMES)
    assert has_anomaly is False
    assert reason is None


def test_quality_check_detects_loop():
    """连续两轮发言者序列完全相同时判为循环"""
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 2]  # 8 条，后 4 与前 4 相同
    has_anomaly, reason = quality_check(messages, PARTICIPANT_NAMES)
    assert has_anomaly is True
    assert reason == "loop"


def test_select_next_speaker_returns_pm_when_quality_anomaly():
    """当 quality_check 判为循环时，select_next_speaker 返回 ProductManager"""
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 2]
    next_speaker = select_next_speaker(messages, PARTICIPANT_NAMES)
    assert next_speaker == "ProductManager"
```

**Step 2: 运行测试并确认失败（缺少 quality_check）**

Run: `pytest tests/demos/AutoGenDemo/test_autogen_quality.py -v`  
Expected: FAIL（例如 `ImportError` 或 `quality_check` 未定义）

**Step 3: 实现 quality_check**

在 `demos/AutoGenDemo/autogen_software_team.py` 中，在 `def select_next_speaker(...):` **之前**插入：

```python
def quality_check(messages, participant_names):
    """
    检测对话质量异常（首版仅循环）。
    返回 (has_anomaly: bool, reason: str | None)，reason 为 "loop" 或 None。
    发言者序列仅包含 source in participant_names 的消息，不包含 user。
    """
    if not messages or not participant_names:
        return False, None
    K = len(participant_names)
    names_set = set(participant_names)
    sources = [
        getattr(m, "source", None)
        for m in messages
        if getattr(m, "source", None) in names_set
    ]
    if len(sources) < 2 * K:
        return False, None
    if sources[-K:] == sources[-2 * K : -K]:
        return True, "loop"
    return False, None
```

**Step 4: 再次运行测试**

Run: `pytest tests/demos/AutoGenDemo/test_autogen_quality.py -v`  
Expected: `test_quality_check_*` 通过，`test_select_next_speaker_returns_pm_when_quality_anomaly` 可能仍失败（因 select_next_speaker 尚未接入 quality_check）。

**Step 5: Commit**

```bash
git add demos/AutoGenDemo/autogen_software_team.py tests/demos/AutoGenDemo/__init__.py tests/demos/AutoGenDemo/test_autogen_quality.py
git commit -m "feat(autogen-demo): add quality_check for loop detection and tests"
```

---

## Task 2: 在 select_next_speaker 中接入 quality_check 并打日志

**Files:**

- Modify: `demos/AutoGenDemo/autogen_software_team.py`（文件顶部增加 `import logging`；在 `select_next_speaker` 开头调用 quality_check 并处理返回值）

**Step 1: 添加 logging 并修改 select_next_speaker**

- 在文件顶部 `import os` 附近增加：`import logging`
- 在 `load_dotenv()` 之后、常量定义之前增加：`logger = logging.getLogger(__name__)`
- 修改 `select_next_speaker`：在 `if not messages:` 判断**之后**、原有 `last = messages[-1]` 逻辑**之前**，插入：

```python
    has_anomaly, reason = quality_check(messages, participant_names)
    if has_anomaly and reason:
        logger.info(
            "quality_monitor",
            extra={"reason": reason, "action": "force_ProductManager"},
        )
        return "ProductManager"
```

保持其后逻辑不变（回退关键词检测 → user → 轮询）。

**Step 2: 运行全部相关测试**

Run: `pytest tests/demos/AutoGenDemo/test_autogen_quality.py -v`  
Expected: 全部 PASS

**Step 3: 确认语法与回归**

Run: `python -m py_compile demos/AutoGenDemo/autogen_software_team.py`  
Expected: 无输出

**Step 4: Commit**

```bash
git add demos/AutoGenDemo/autogen_software_team.py
git commit -m "feat(autogen-demo): wire quality_check into select_next_speaker with logging"
```

---

## Task 3: 可选 — 写入设计文档

**Files:**

- Create: `docs/plans/2026-02-04-autogen-conversation-quality-monitor-design.md`

将前述 brainstorming + 继续分析整理为设计文档（目的、成功标准、架构、循环/偏离规则、与回退逻辑顺序、可观测性、测试与验收、不做的内容）。若时间紧可跳过，实施完成后补写即可。

---

## 验收（手动）

- **无异常：** 使用现有比特币任务跑一遍，行为与加监控前一致（PM → Engineer → CodeReviewer → UserProxy 至 TERMINATE）。
- **有循环：** 若某次运行中对话恰好形成两轮相同发言者序列，控制台或日志中应出现一次 `quality_monitor` 且下一棒为 ProductManager。
- **与回退共存：** 出现回退关键词时仍优先回退；质量异常与回退关键词同时满足时，先被 quality_check 命中即返回 PM，逻辑正确。

---

## 执行选项

计划已保存到 `docs/plans/2026-02-04-autogen-conversation-quality-monitor-implementation.md`。两种执行方式：

1. **Subagent-Driven（本会话）**：按任务逐个执行，每任务后 review，迭代快。  
   - **需用子技能：** @superpowers:subagent-driven-development

2. **Parallel Session（新会话）**：在独立会话中打开 worktree，用 executing-plans 按检查点批量执行。  
   - **需用子技能：** 新会话使用 @superpowers:executing-plans

你选哪种？
