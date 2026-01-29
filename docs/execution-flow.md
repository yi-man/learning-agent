# Superpowers 全流程执行图

本文档描述完整的 Superpowers 开发工作流（从对话开始到合并/完成），以及执行阶段的细节。

## 1. Superpowers 全流程总览

```mermaid
flowchart TB
    Start[对话开始] --> UsingSuperpowers["1. using-superpowers（强制）\n建立技能使用方式"]
    UsingSuperpowers --> Brainstorm["2. brainstorming\n理解意图、探索方案、验证设计"]
    Brainstorm --> Worktree["3. using-git-worktrees\n创建隔离工作区与功能分支"]
    Worktree --> WritingPlans["4. writing-plans\n分解小任务、写实施计划、保存到 docs/plans/"]
    WritingPlans --> Choice{执行方式?}

    Choice -->|本会话| Subagent["5a. subagent-driven-development\n每任务派子代理 + spec/code 审查"]
    Choice -->|新会话| ExecPlans["5b. executing-plans\n新会话中执行全部任务"]

    Subagent --> TDD1["实施中: test-driven-development\nRED → GREEN → REFACTOR"]
    ExecPlans --> TDD2["实施中: test-driven-development\n按计划步骤执行 + 验证"]

    TDD1 --> Debug{遇问题?}
    TDD2 --> Debug
    Debug -->|是| Systematic["systematic-debugging\n4 阶段根因分析"]
    Systematic --> TDD1
    Debug -->|否| MoreTasks{还有任务?}
    MoreTasks -->|是| Subagent
    MoreTasks -->|否| Review

    Subagent --> Review
    ExecPlans --> Review["6. Code Review（一次）\n执行全部完成后提醒用户 review"]
    Review --> UserReview[用户本地 review]
    UserReview --> Confirm[用户确认 review 完成]
    Confirm --> Finish["7. finishing-a-development-branch\n验证测试 → 选项 1 合并（或 2/3/4）"]
    Finish --> End[完成: 合并 / PR / 保留 / 丢弃]
```

## 2. 全流程时序（简化）

```mermaid
sequenceDiagram
    participant User as 用户
    participant Agent as Agent

    Note over Agent: 对话开始
    Agent->>Agent: using-superpowers（强制）

    Agent->>User: brainstorming：理解需求、设计方案
    User->>Agent: 确认设计

    Agent->>Agent: using-git-worktrees：创建 worktree + 功能分支
    Agent->>Agent: writing-plans：写计划，保存到 docs/plans/

    Agent->>User: 选执行方式：本会话 Subagent 或 新会话 Executing Plans?
    User->>Agent: 选择

    Note over Agent: 实施（TDD，遇问题用 systematic-debugging）
    loop 任务
        Agent->>Agent: 执行任务、验证、提交
    end

    Agent->>User: 执行完成。请 review 所有改动；确认后我执行选项 1 合并
    User->>User: 本地 review
    User->>Agent: review 完成 / 选 1

    Agent->>Agent: finishing-a-development-branch：验证测试、执行选项 1
    Agent->>User: 已合并（或 PR/保留/丢弃）
```

## 3. 阶段与技能对应

| 阶段 | 技能 | 说明 |
|------|------|------|
| 对话开始 | using-superpowers | 强制先建立如何找技能、用技能 |
| 设计 | brainstorming | 理解意图、探索方案、验证设计 |
| 隔离工作区 | using-git-worktrees | 创建 worktree + 功能分支，目录入 .gitignore |
| 计划 | writing-plans | 小任务、文件路径、测试步骤，TDD/YAGNI/DRY |
| 执行方式 | 用户选择 | **Subagent-Driven**（本会话）或 **Parallel Session**（新会话 executing-plans） |
| 实施 | test-driven-development | RED → GREEN → REFACTOR，每 TDD 循环后提交 |
| 遇问题 | systematic-debugging | 4 阶段根因分析、防御性检查 |
| Code Review | 一次（本项目默认） | 全部任务完成后提醒用户 review，确认后执行选项 1 |
| 完成分支 | finishing-a-development-branch | 验证测试 → 4 选项（本地合并/PR/保留/丢弃）→ 清理 worktree |

## 4. Executing Plans 详细流程（Parallel Session）

当用户选择「新会话 + executing-plans」时，在新会话中的具体步骤：

```mermaid
flowchart TB
    subgraph load [Step 1: 加载与审查计划]
        A[读取计划文件] --> B[审查计划，识别疑问或风险]
        B --> C{有疑问?}
        C -->|是| D[与用户沟通，暂不执行]
        C -->|否| E[创建 TodoWrite，进入执行]
    end

    subgraph execute [Step 2: 执行全部任务]
        E --> F[任务 1: in_progress → 按步骤执行 → 验证 → completed]
        F --> G[任务 2: ...]
        G --> H[任务 N: ...]
        H --> I{遇到 blocker?}
        I -->|是| J[停止并询问用户]
        I -->|否| K[全部任务完成]
    end

    subgraph report [Step 3: 一次性报告]
        K --> L[列出已实现内容与验证结果]
        L --> M["提醒用户: 请本地 review；review 完成后回复，我将执行选项 1 合并"]
        M --> N[等待用户回复]
    end

    subgraph finish [Step 4: 用户确认后完成]
        N --> O{用户确认 review 完成?}
        O -->|是| P[finishing-a-development-branch]
        P --> Q[验证测试 → 执行选项 1: squash merge]
        Q --> S[清理 worktree]
        O -->|用户要求修改或其它选项| T[按用户新选择处理]
    end
```

## 5. 相关文件

- 工作流规则：`.cursor/rules/superpowers-workflow.mdc`
- 技能目录：`.cursor/skills/`
  - executing-plans、subagent-driven-development、writing-plans
  - finishing-a-development-branch、test-driven-development、systematic-debugging
  - brainstorming、using-git-worktrees、requesting-code-review、receiving-code-review
