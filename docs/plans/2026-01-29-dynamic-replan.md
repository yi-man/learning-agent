# Plan-and-Solve 动态重规划 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 当某步无法完成（异常/超时）或执行器主动请求（[REPLAN]）时触发重规划并继续执行。

**Architecture:**

- 在 `plan_and_solve.py` 中新增 Replanner 类：输入 question、plan、completed、failed_step、failure_reason，输出新步骤列表（与 Planner 同格式解析）
- Executor 改为 while 剩余步骤：单步成功则去掉首步继续；失败或检测到 [REPLAN] 则调用 Replanner 替换剩余计划，并限制 max_replans
- PlanAndSolveAgent 注入 Replanner 与 max_replans，run() 中调用带 replanner 的 execute

**Tech Stack:** Python, ast, pytest, demos/agent-framework/plan_and_solve.py

---

## Task 1: Replanner 类与解析

**Files:**

- Modify: `demos/agent-framework/plan_and_solve.py`
- Create: `tests/demos/agent-framework/test_plan_and_solve.py`

**Step 1: Write the failing test for Replanner**

在 `tests/demos/agent-framework/test_plan_and_solve.py` 中创建文件并写入：

```python
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "demos" / "agent-framework")
)

from plan_and_solve import Replanner


def test_replanner_returns_list():
    """Replanner.replan 应返回 list[str] 或空列表"""
    class MockLLM:
        def think(self, messages):
            return '```python\n["新步骤A", "新步骤B"]\n```'

    replanner = Replanner(MockLLM())
    result = replanner.replan(
        question="q",
        plan=["步1", "步2"],
        completed=[],
        failed_step="步1",
        failure_reason="超时",
    )
    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)
    assert result == ["新步骤A", "新步骤B"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_plan_and_solve.py::test_replanner_returns_list -v`
Expected: FAIL (Replanner 未定义)

**Step 3: Implement Replanner**

在 `plan_and_solve.py` 中，在 Executor 定义之前（# --- 3. 执行器 之前）添加：

```python
# --- 2.5 重规划器 (Replanner) 定义 ---
REPLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。原计划在执行某一步时失败或需要调整，请基于当前状态给出从当前起的新计划。
输入：原问题、原计划、已完成步骤与结果、失败的步骤及原因。
请输出从当前起的新步骤列表（可省略已完成部分）。若认为任务无法继续，可输出空列表 []。

# 原问题:
{question}

# 原计划:
{plan}

# 已完成步骤与结果:
{completed}

# 失败的步骤:
{failed_step}

# 失败原因:
{failure_reason}

请严格按照以下格式输出新计划，```python与```作为前后缀是必要的:
```python
["步骤A", "步骤B", ...]
```
或
```python
[]
```
"""


class Replanner:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def replan(
        self,
        question: str,
        plan: list[str],
        completed: list[tuple[str, str]],
        failed_step: str,
        failure_reason: str,
    ) -> list[str]:
        completed_str = "\n".join(
            f"步骤: {s}\n结果: {r}" for s, r in completed
        ) or "无"
        prompt = REPLANNER_PROMPT_TEMPLATE.format(
            question=question,
            plan=plan,
            completed=completed_str,
            failed_step=failed_step,
            failure_reason=failure_reason,
        )
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages=messages) or ""
        try:
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            new_plan = ast.literal_eval(plan_str)
            return new_plan if isinstance(new_plan, list) else []
        except (ValueError, SyntaxError, IndexError, TypeError):
            return []
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_plan_and_solve.py::test_replanner_returns_list -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/plan_and_solve.py tests/demos/agent-framework/test_plan_and_solve.py
git commit -m "feat: add Replanner for dynamic replanning"
```

---

## Task 2: Executor 单步抽取与重规划循环

**Files:**

- Modify: `demos/agent-framework/plan_and_solve.py`
- Modify: `tests/demos/agent-framework/test_plan_and_solve.py`

**Step 1: Write the failing test for execute with replan**

在 `test_plan_and_solve.py` 末尾添加：

```python
def test_execute_with_replan_on_replan_marker():
    """当步骤返回含 [REPLAN] 时，应调用 Replanner 并用新计划继续执行"""
    class MockLLM:
        def __init__(self):
            self.call_count = 0
        def think(self, messages):
            self.call_count += 1
            # 第1次：第一步返回 [REPLAN]，第2次：Replanner 返回新计划，第3次：新计划第一步成功
            if self.call_count == 1:
                return "[REPLAN] 需要更多信息"
            if self.call_count == 2:
                return '```python\n["替代步骤1", "替代步骤2"]\n```'
            return "替代步骤1的结果"

    from plan_and_solve import Executor
    class MockReplanner:
        def replan(self, question, plan, completed, failed_step, failure_reason):
            return ["替代步骤1", "替代步骤2"]

    llm = MockLLM()
    executor = Executor(llm)
    result = executor.execute(
        question="q",
        plan=["原步1", "原步2"],
        replanner=MockReplanner(),
        max_replans=2,
    )
    assert "替代步骤1的结果" in result or result == "替代步骤1的结果"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_plan_and_solve.py::test_execute_with_replan_on_replan_marker -v`
Expected: FAIL (execute 不支持 replanner 参数或未实现重规划循环)

**Step 3: Implement execute loop and replan**

- 在 Executor 中新增 `execute_one_step(self, question, plan, history, current_step) -> str`，将当前单步 prompt + think 逻辑移入，返回 response_text。
- 将 `execute` 改为接受可选 `replanner=None`、`max_replans=2`；内部 `remaining_plan = list(plan)`，`completed = []`，`replan_count = 0`；`while remaining_plan and replan_count <= max_replans`：取 `current_step = remaining_plan[0]`，调用 `execute_one_step`；若返回中含 `[REPLAN]` 且 replanner 非 None：解析原因（或整段），调用 `replanner.replan(...)`，用返回值替换 `remaining_plan`，`replan_count += 1`，continue；否则：`completed.append((current_step, result))`，`remaining_plan.pop(0)`，`final_answer = result`。循环结束后 return final_answer 或 completed 最后一答。
- 若 replanner 为 None，保持原 for 循环行为（不重规划）。

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_plan_and_solve.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/plan_and_solve.py tests/demos/agent-framework/test_plan_and_solve.py
git commit -m "feat: Executor while loop and replan on failure or [REPLAN]"
```

---

## Task 3: PlanAndSolveAgent 接入 Replanner

**Files:**

- Modify: `demos/agent-framework/plan_and_solve.py`
- Modify: `tests/demos/agent-framework/test_plan_and_solve.py`

**Step 1: Write the failing test for Agent.run with replanner**

在 `test_plan_and_solve.py` 末尾添加：

```python
def test_agent_uses_replanner():
    """PlanAndSolveAgent.run 应使用 Replanner 调用 executor.execute"""
    class MockLLM:
        def think(self, messages):
            content = messages[0]["content"]
            if "请严格按照以下格式输出你的计划" in content:
                return '```python\n["步1", "步2"]\n```'
            if "请严格按照以下格式输出新计划" in content:
                return '```python\n["新步1"]\n```'
            return "步1结果"

    from plan_and_solve import PlanAndSolveAgent
    agent = PlanAndSolveAgent(MockLLM())
    # 无异常、能跑完即可；内部会创建 Replanner 并传给 executor
    agent.run("test question")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_plan_and_solve.py::test_agent_uses_replanner -v`
Expected: 若 executor.execute 已要求 replanner 参数且 Agent 未传，则 FAIL；否则可能 PASS，则本 Task 仅确保 Agent 显式传入 replanner。

**Step 3: Implement Agent wiring**

- PlanAndSolveAgent.__init__ 中：`self.replanner = Replanner(self.llm_client)`。
- run() 中：`self.executor.execute(question, plan, replanner=self.replanner, max_replans=2)`。

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_plan_and_solve.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/plan_and_solve.py tests/demos/agent-framework/test_plan_and_solve.py
git commit -m "feat: PlanAndSolveAgent wires Replanner and max_replans"
```
