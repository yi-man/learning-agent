# AutoGen 软件开发团队：动态回退机制设计

**日期**：2026-02-03  
**范围**：`demos/AutoGenDemo/autogen_software_team.py`  
**状态**：已与需求方确认

---

## 1. 目的与成功标准

### 目的

在现有「按固定顺序发言」的 RoundRobin 式协作基础上，增加**动态回退**：当任何人（PM / 工程师 / 代码审查员 / 用户代理）在回复中表达「需求变更，需产品经理重新审核」时，**下一棒强制交给 ProductManager**，由 PM 重新做需求分析或澄清，再按原顺序继续（PM → Engineer → CodeReviewer → UserProxy）。

不改变现有四角色职责和对话风格，只增加「可回退到 PM」这一条规则。

### 成功标准

1. **默认行为**：未出现回退语时，发言顺序与当前一致，为 PM → Engineer → CodeReviewer → UserProxy 循环，直至 TERMINATE。
2. **回退行为**：任一角色在某条消息中包含约定的回退语（如「请产品经理重新审核」或「需求变更」等）时，紧接的下一棒必须是 ProductManager；之后继续按固定顺序轮转。
3. **触发方**：任意角色（包括 PM 自己）说出回退语均可触发；实现上不做「仅下游可触发」之类的限制。
4. **可验证**：通过一次「无回退」的完整任务和一次「有回退」的对话即可验证上述两点。

### 约束

- 仅修改 `autogen_software_team.py`，不新增项目依赖；使用 AutoGen 现有的 SelectorGroupChat + selector_func 能力实现。

---

## 2. 架构与组件

### 整体思路

用 **SelectorGroupChat** 替代 **RoundRobinGroupChat**，通过 **selector_func(messages) → str | None** 决定下一发言者。默认按固定顺序轮询（PM → Engineer → CodeReviewer → UserProxy）；当最后一条消息包含回退关键词时，下一棒强制为 ProductManager。

### 主要组件

1. **参与者列表**  
   保持现有四角色：`product_manager`, `engineer`, `code_reviewer`, `user_proxy`，顺序不变，用于在 selector_func 里计算「下一棒」下标。

2. **回退触发约定**

   - 关键词列表（可配置）：如 `"请产品经理重新审核"`、`"需求变更"`、`"REVIEW_BY_PM"`。
   - 检测方式：取 `messages[-1]` 的可读文本（如 `content` 或 `to_text()`），做字符串包含判断；任一关键词命中即视为触发回退。

3. **selector_func**

   - 输入：`messages: Sequence[BaseAgentEvent | BaseChatMessage]`。
   - 逻辑：
     - 若最后一条消息的文本包含回退关键词 → 返回 `"ProductManager"`。
     - 否则：根据 `messages[-1].source` 在 participants 中的下标，下一棒为 `(index + 1) % len(participants)`；若上一条是 `"user"`（任务初始消息），下一棒为 `participants[0]`（PM）。
   - 返回值：下一发言者的 `name`（str）。

4. **Team 构造**

   - `SelectorGroupChat(participants=..., model_client=..., termination_condition=..., selector_func=...)`；终止条件仍为 `TextMentionTermination("TERMINATE")`。
   - 可选：简短 `selector_prompt`，说明「默认按 PM→Engineer→CodeReviewer→UserProxy 顺序，遇需求变更则交由 ProductManager」；若 selector_func 始终返回具体 name，模型不会参与选人，prompt 仅作文档/兜底。

5. **智能体 system_message 补充**
   - 在 ProductManager、Engineer、CodeReviewer 的 system_message 末尾各加 1 ～ 2 句：若需求变更或实现与需求不符，请在回复中写明「请产品经理重新审核」。
   - 目的：让模型在合适场景下主动说出回退语，便于稳定触发动态回退。

### 不新增的

- 不新增文件、不新增依赖；不引入「仅某角色可触发」的白名单逻辑，任意角色说出回退语即触发。

---

## 3. 数据流与异常/边界

### 数据流（概念）

1. 用户发起任务 → 初始消息 `source="user"`。
2. selector_func 被调用：`messages[-1].source == "user"` → 下一棒为 `participants[0]`（ProductManager）。
3. 之后每轮：上一发言者发言完毕，selector_func 再次被调用；若最后一条消息文本包含回退关键词 → 返回 `"ProductManager"`，否则返回 `(当前下标 + 1) % 4` 对应的角色名。
4. 流程持续到某条消息触发 `TextMentionTermination("TERMINATE")`，团队停止。

### 回退场景示例

Engineer 或 CodeReviewer 发现实现与需求不符，在回复末尾写「请产品经理重新审核」→ 下一棒强制 PM；PM 重新分析/澄清后说「请工程师开始实现」→ 下一棒按轮询为 Engineer，继续开发。

### 异常与边界

1. **messages 为空或仅一条（user）**  
   仅一条（user）时：下一棒固定为 `participants[0]`（PM），不访问 `messages[-2]`，避免越界。

2. **最后一条不是 TextMessage**  
   若 `messages[-1]` 为 ToolCallRequestEvent、ToolCallSummaryMessage 等，需有统一「可读文本」方式（如 `getattr(m, "content", "")` 或消息类型的 `to_text()`）。若无文本则当空串处理，不命中回退关键词，按轮询选下一棒。

3. **上一发言者不在 participants 中**  
   理论上不应出现（都是 team 内发言）。若出现：在 participants 中找不到 `messages[-1].source` 时，可退回为 `participants[0]`（PM），保证总有下一棒。

4. **回退关键词误命中**  
   若自然叙述中出现「需求变更」等词但并非请求回退，也会触发。若需更稳，可后续收窄为「请产品经理重新审核」或「REVIEW_BY_PM」等更明确的短语；首版用简单包含判断即可。

### 不做的

- 不因单次选人失败而重试或弹窗；不持久化回退次数；不限制回退次数（由 max_turns 统一限制总轮次）。

---

## 4. 测试与验收

### 测试目标

- 确认默认仍是固定顺序轮询（PM → Engineer → CodeReviewer → UserProxy）。
- 确认出现回退语时，下一棒一定是 ProductManager，且之后顺序恢复轮询直至 TERMINATE。

### 建议用例

1. **无回退（回归）**  
   使用现有比特币价格应用任务，不在对话中刻意触发回退语。  
   验收：发言顺序为 PM → Engineer → CodeReviewer → UserProxy 循环，最终某条消息包含 TERMINATE，任务正常结束。可与当前 RoundRobin 版本对比，行为一致即可。

2. **有回退（新能力）**  
   在任务描述或某角色 system_message 中诱导一次「需求变更，请产品经理重新审核」（例如在任务里加一句「若发现需求不清可请产品经理重新审核」，或临时让 CodeReviewer 的 system_message 强调「发现与需求不符时务必写『请产品经理重新审核』」）。  
   验收：在出现包含回退关键词的消息之后，下一棒发言者为 ProductManager；PM 发言后，下一棒按轮询为 Engineer，流程继续直至 TERMINATE。

### 验收标准（与第一节一致）

- 默认：顺序固定、无回退时行为与现有一致。
- 回退：任意角色说出回退语 → 下一棒为 ProductManager。
- 实现：仅改 `autogen_software_team.py`，使用 SelectorGroupChat + selector_func，无新依赖。

### 不做的

- 不写自动化单元测试（除非后续要求）；以手工跑上述两场景为主。
- 不测 max_turns 用尽、网络/API 失败等，由现有框架处理。

---

## 5. 实施参考

- 实现计划见项目内已有计划文档（RoundRobin 动态回退机制）。
- 实施时：先写 selector_func 与回退关键词列表，再替换 RoundRobinGroupChat 为 SelectorGroupChat，最后补充各角色 system_message。
