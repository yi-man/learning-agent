# Plan-and-Solve 动态重规划机制 — 设计文档

**目标：** 在执行过程中，当某一步无法完成或执行器主动请求时，能够触发重规划并继续执行，而不是沿用静态计划直到结束或失败。

**范围：** `demos/agent-framework/plan_and_solve.py` 中的 Planner、Executor、PlanAndSolveAgent。

---

## 1. 触发条件

| 类型 | 说明 | 实现方式 |
|------|------|----------|
| **A. 步骤执行失败** | 当前步骤抛错、超时，或 LLM 明确返回“无法完成” | 捕获异常 / 超时；可选：检测“无法完成”关键词 |
| **C. 执行器主动请求** | Executor 在回复中声明需要重规划 | 约定标记如 `[REPLAN] 原因`，解析后走重规划 |

可选扩展（后续迭代）：

- **B. 结果校验不通过**：用规则或 LLM 判断当前步骤结果不符合预期，将本步视为失败并触发重规划。

---

## 2. 架构概览

- **Planner**：保持不变，仅负责“从零规划”，输入问题，输出 `list[str]`。
- **Replanner**：新增模块，负责“基于执行状态再规划”。输入：原问题、原计划、已完成步骤与结果、失败步骤及原因；输出：新计划（从当前起的一系列步骤）。
- **Executor**：由“单次 for 循环”改为 **while 剩余步骤** 的循环；每步执行后根据成功/失败或“需要重规划”决定是继续执行还是调用 Replanner 并替换剩余计划。
- **PlanAndSolveAgent**：组装 Planner、Replanner、Executor；在 `run()` 中先生成初始计划，再调用支持重规划的执行循环。

数据流：

```
question → Planner → plan
                        ↓
         remaining_plan ← (初始为 plan 的拷贝)
                        ↓
    [取首步] → Executor 执行一步 → 成功? → 完成列表追加，剩余计划去掉首步，继续
                        ↓ 失败 / [REPLAN]
                        Replanner(question, 已完成, 失败步, 原因) → 新计划
                        ↓
                remaining_plan = 新计划；若空则终止，否则继续
```

---

## 3. 数据与接口

### 3.1 执行状态（用于 Replanner 输入）

在代码中可用简单结构传递，不必单独建类型文件；如需类型提示可内联或放在同文件顶部。

- `question: str` — 原始问题
- `plan: list[str]` — 当前（或原始）计划
- `completed: list[tuple[str, str]]` — 已完成步骤与结果，每项 `(step_description, step_result)`
- `failed_step: str | None` — 无法完成或请求重规划的那一步描述
- `failure_reason: str | None` — 异常信息或执行器声明的重规划原因

### 3.2 Replanner 接口

- 方法：`replan(question, plan, completed, failed_step, failure_reason) -> list[str]`
- 返回：从“当前”起的新步骤列表；空列表表示无法继续，由调用方终止执行。

### 3.3 Executor 与 Agent

- Executor：  
  - 输入：`question`、`plan`、可选 `replanner`、可选 `max_replans`（默认如 2）。  
  - 内部维护：`remaining_plan`（可变）、`completed` 列表。  
  - 单步执行：沿用现有 prompt，返回当前步结果字符串；若检测到 `[REPLAN]` 或异常，则视为“需要重规划”。
- PlanAndSolveAgent：  
  - 持有 `planner`、`replanner`、`executor`；  
  - `run(question)`：`plan = planner.plan(question)`，然后 `executor.execute(question, plan, replanner=..., max_replans=...)`。

---

## 4. Replanner Prompt 要点

- 说明角色：基于已有执行状态进行再规划。
- 输入内容：原问题、原计划、已完成步骤及结果、失败步骤及原因。
- 输出格式：与 Planner 一致，Python 列表字符串，如 `["步骤A", "步骤B", ...]`。
- 强调：新计划是“从当前起”的步骤，可省略已完成部分；若认为任务无法继续，可返回空列表或明确说明。

---

## 5. 执行循环逻辑（伪代码）

```text
remaining_plan = list(plan)
completed = []
replan_count = 0
final_answer = ""

while remaining_plan and replan_count <= max_replans:
    current_step = remaining_plan[0]
    try:
        result = execute_one_step(question, plan, completed, current_step)
        if "[REPLAN]" in result:
            # 解析原因，触发重规划
            reason = parse_replan_reason(result) or "执行器请求重规划"
            new_plan = replanner.replan(question, plan, completed, current_step, reason)
            replan_count += 1
            remaining_plan = new_plan if new_plan else []
            continue
        # 成功
        completed.append((current_step, result))
        remaining_plan.pop(0)
        final_answer = result
    except Exception as e:
        new_plan = replanner.replan(question, plan, completed, current_step, str(e))
        replan_count += 1
        remaining_plan = new_plan if new_plan else []
        if not remaining_plan:
            break

return final_answer 或 "任务未完成"
```

- `execute_one_step`：即当前 Executor 单步逻辑（构造 prompt、调用 LLM、解析回复）。
- `plan` 传入 prompt 时可用“当前完整计划”（原始或最近一次重规划结果），便于模型理解上下文。

---

## 6. 约束与边界

- **最大重规划次数**：如 `max_replans=2`，避免无限循环。
- **Replanner 返回空**：视为终止，返回已有最后答案或明确失败信息。
- **向后兼容**：若不传入 `replanner`，可退化为“无重规划”：失败即终止并返回当前状态（或抛错）。

---

## 7. 测试策略

- 单元测试：  
  - Replanner：给定 mock 的 question/plan/completed/failed_step/reason，校验返回格式为 `list[str]` 或空。  
  - Executor：mock Replanner，构造“第一步失败、重规划后第二步成功”的输入，校验最终答案和 completed 内容。
- 集成测试：可选，用简单问题 + 故意失败步骤，验证重规划被调用且能继续执行。

---

## 8. 实现顺序建议

1. 新增 **Replanner** 类与 prompt，在 `plan_and_solve.py` 中实现并解析返回的 `list[str]`。
2. 将 Executor 的“单步执行”抽成 `execute_one_step`，保持现有 prompt 与调用方式。
3. 在 Executor 中实现 **while 循环 + 失败/REPLAN 检测**，调用 Replanner 并更新 `remaining_plan`。
4. 在 PlanAndSolveAgent 中注入 Replanner、传入 `max_replans`，并接好 `run()` 流程。
5. 为 Replanner 与 Executor（重规划分支）补充测试，运行 `pytest -v` 验证。

实施时可使用 `writing-plans` 写出详细任务列表，再用 `executing-plans` 或 TDD 逐项完成。
