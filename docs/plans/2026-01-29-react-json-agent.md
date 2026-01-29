# ReAct JSON Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建 `react_json.py`，使用 JSON 格式解析 LLM 输出，替代正则表达式解析，提高鲁棒性。

**Architecture:** 基于现有的 `react.py`，创建新文件 `react_json.py`。修改 prompt 要求 LLM 输出 JSON 格式，使用 `json.loads()` 解析输出，保留与原有 `ReActAgent` 相同的接口和行为。

**Tech Stack:** Python, json (标准库), pytest (测试)

---

## Task 1: JSON 输出解析器

**Files:**
- Create: `demos/agent-framework/react_json.py`
- Test: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Write the failing test for JSON parsing**

```python
import json
import pytest
from demos.agent_framework.react_json import ReActJSONAgent

def test_parse_json_output():
    """测试解析 JSON 格式的 LLM 输出"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    
    # 测试正常的 JSON 输出
    json_text = '{"thought": "我需要搜索", "action": {"type": "tool_call", "tool_name": "Search", "input": "华为手机"}}'
    thought, action = agent._parse_output(json_text)
    
    assert thought == "我需要搜索"
    assert action["type"] == "tool_call"
    assert action["tool_name"] == "Search"
    assert action["input"] == "华为手机"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_parse_json_output -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'demos.agent_framework.react_json'"

**Step 3: Create minimal file structure**

Create: `demos/agent-framework/react_json.py`

```python
from typing import List, Dict, Any, Optional
import json
import re

from llm_client import HelloAgentsLLM
from tools import ToolExecutor


class ReActJSONAgent:
    def __init__(
        self,
        llm_client: HelloAgentsLLM,
        tool_executor: ToolExecutor,
        max_steps: int = 5,
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history: List[str] = []

    def _parse_output(self, text: str):
        """解析 JSON 格式的 LLM 输出"""
        # 占位实现，返回 None
        return None, None
```

**Step 4: Run test to verify it fails with correct error**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_parse_json_output -v`
Expected: FAIL with assertion error (thought/action is None)

**Step 5: Implement JSON parsing**

Modify: `demos/agent-framework/react_json.py`

```python
    def _parse_output(self, text: str):
        """解析 JSON 格式的 LLM 输出"""
        try:
            # 尝试提取 JSON（可能在代码块中）
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # 尝试直接查找 JSON 对象
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return None, None
            
            data = json.loads(json_str)
            thought = data.get("thought")
            action = data.get("action")
            return thought, action
        except (json.JSONDecodeError, KeyError, AttributeError):
            return None, None
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_parse_json_output -v`
Expected: PASS

**Step 7: Commit**

```bash
git add demos/agent-framework/react_json.py tests/demos/agent-framework/test_react_json.py
git commit -m "feat: add JSON output parser for ReAct agent"
```

---

## Task 2: JSON Prompt Template

**Files:**
- Modify: `demos/agent-framework/react_json.py`

**Step 1: Write the failing test for prompt format**

```python
def test_prompt_contains_json_format():
    """测试 prompt 包含 JSON 格式要求"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    prompt = agent._build_prompt("测试问题", "工具描述", "")
    
    assert "JSON" in prompt or "json" in prompt
    assert "thought" in prompt.lower()
    assert "action" in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_prompt_contains_json_format -v`
Expected: FAIL with "AttributeError: 'ReActJSONAgent' object has no attribute '_build_prompt'"

**Step 3: Add prompt template and _build_prompt method**

Modify: `demos/agent-framework/react_json.py`

Add at top of file:

```python
REACT_JSON_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下：
{tools}

回答问题时候的注意点:
- 问题中涉及当前时间，需先计算出当前时间

请严格按照以下 JSON 格式进行回应：

```json
{{
  "thought": "你的思考过程，用于分析问题、拆解任务和规划下一步行动",
  "action": {{
    "type": "tool_call" | "finish",
    "tool_name": "工具名称（当 type 为 tool_call 时必需）",
    "input": "工具输入或最终答案（当 type 为 finish 时，这是最终答案）"
  }}
}}
```

重要说明：
- 当 type 为 "tool_call" 时，必须提供 tool_name 和 input
- 当 type 为 "finish" 时，只需提供 input（最终答案）
- 必须输出有效的 JSON，不要添加任何额外的文本或解释

现在，请开始解决以下问题：
Question: {question}
History: {history}
"""
```

Add method to class:

```python
    def _build_prompt(self, question: str, tools: str, history: str) -> str:
        """构建包含 JSON 格式要求的 prompt"""
        return REACT_JSON_PROMPT_TEMPLATE.format(
            tools=tools, question=question, history=history
        )
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_prompt_contains_json_format -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/react_json.py
git commit -m "feat: add JSON format prompt template"
```

---

## Task 3: Action Parser from JSON

**Files:**
- Modify: `demos/agent-framework/react_json.py`
- Test: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Write the failing test for action parsing**

```python
def test_parse_action_from_json():
    """测试从 JSON action 中解析工具名和输入"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    
    # 测试 tool_call 类型
    action_tool = {"type": "tool_call", "tool_name": "Search", "input": "华为手机"}
    tool_name, tool_input = agent._parse_action(action_tool)
    assert tool_name == "Search"
    assert tool_input == "华为手机"
    
    # 测试 finish 类型
    action_finish = {"type": "finish", "input": "最终答案"}
    tool_name, tool_input = agent._parse_action(action_finish)
    assert tool_name == "Finish"
    assert tool_input == "最终答案"
    
    # 测试无效 action
    action_invalid = {"type": "unknown"}
    tool_name, tool_input = agent._parse_action(action_invalid)
    assert tool_name is None
    assert tool_input is None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_parse_action_from_json -v`
Expected: FAIL with "AttributeError: '_parse_action' method not found or wrong signature"

**Step 3: Implement _parse_action method**

Modify: `demos/agent-framework/react_json.py`

```python
    def _parse_action(self, action: Dict[str, Any]):
        """从 JSON action 对象中解析工具名和输入"""
        if not isinstance(action, dict):
            return None, None
        
        action_type = action.get("type")
        if action_type == "tool_call":
            tool_name = action.get("tool_name")
            tool_input = action.get("input")
            return tool_name, tool_input
        elif action_type == "finish":
            final_answer = action.get("input", "")
            return "Finish", final_answer
        else:
            return None, None
```

**Step 4: Update _parse_output to return action dict**

Modify: `demos/agent-framework/react_json.py` - update `_parse_output`:

```python
    def _parse_output(self, text: str):
        """解析 JSON 格式的 LLM 输出"""
        try:
            # 尝试提取 JSON（可能在代码块中）
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # 尝试直接查找 JSON 对象
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return None, None
            
            data = json.loads(json_str)
            thought = data.get("thought")
            action = data.get("action")  # 返回 dict，不是字符串
            return thought, action
        except (json.JSONDecodeError, KeyError, AttributeError):
            return None, None
```

**Step 5: Update test_parse_json_output to match new return format**

Modify: `tests/demos/agent-framework/test_react_json.py`

```python
def test_parse_json_output():
    """测试解析 JSON 格式的 LLM 输出"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    
    # 测试正常的 JSON 输出
    json_text = '{"thought": "我需要搜索", "action": {"type": "tool_call", "tool_name": "Search", "input": "华为手机"}}'
    thought, action = agent._parse_output(json_text)
    
    assert thought == "我需要搜索"
    assert isinstance(action, dict)
    assert action["type"] == "tool_call"
    assert action["tool_name"] == "Search"
    assert action["input"] == "华为手机"
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/demos/agent-framework/test_react_json.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add demos/agent-framework/react_json.py tests/demos/agent-framework/test_react_json.py
git commit -m "feat: implement JSON action parser"
```

---

## Task 4: Main Run Loop

**Files:**
- Modify: `demos/agent-framework/react_json.py`
- Test: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Write the failing test for run method**

```python
from unittest.mock import Mock, MagicMock

def test_run_with_finish_action():
    """测试 run 方法处理 finish action"""
    mock_llm = Mock()
    mock_llm.think.return_value = '{"thought": "已完成", "action": {"type": "finish", "input": "最终答案"}}'
    
    mock_tool_executor = Mock()
    
    agent = ReActJSONAgent(llm_client=mock_llm, tool_executor=mock_tool_executor)
    result = agent.run("测试问题")
    
    assert result == "最终答案"
    mock_llm.think.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_run_with_finish_action -v`
Expected: FAIL with "AttributeError: 'ReActJSONAgent' object has no attribute 'run'"

**Step 3: Implement run method**

Modify: `demos/agent-framework/react_json.py`

```python
    def run(self, question: str):
        """运行 ReAct 循环，使用 JSON 格式解析"""
        self.history = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = self._build_prompt(question, tools_desc, history_str)

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误：LLM未能返回有效响应。")
                break

            thought, action = self._parse_output(response_text)
            if thought:
                print(f"🤔 思考: {thought}")
            if not action:
                print("警告：未能解析出有效的Action，流程终止。")
                break

            # 解析 action（现在是 dict）
            tool_name, tool_input = self._parse_action(action)
            if not tool_name:
                self.history.append("Observation: 无效的Action格式，请检查。")
                continue

            if tool_name == "Finish":
                # 如果是Finish指令，提取最终答案并结束
                print(f"🎉 最终答案: {tool_input}")
                return tool_input

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            tool_function = self.tool_executor.getTool(tool_name)
            observation = (
                tool_function(tool_input)
                if tool_function
                else f"错误：未找到名为 '{tool_name}' 的工具。"
            )

            print(f"👀 观察: {observation}")
            # 记录 action 为字符串格式（保持兼容）
            action_str = f"{tool_name}[{tool_input}]"
            self.history.append(f"Action: {action_str}")
            self.history.append(f"Observation: {observation}")

        print("已达到最大步数，流程终止。")
        return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_run_with_finish_action -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/react_json.py tests/demos/agent-framework/test_react_json.py
git commit -m "feat: implement main run loop with JSON parsing"
```

---

## Task 5: Tool Call Integration

**Files:**
- Modify: `demos/agent-framework/react_json.py`
- Test: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Write the failing test for tool call**

```python
def test_run_with_tool_call():
    """测试 run 方法处理工具调用"""
    mock_llm = Mock()
    # 第一次调用返回工具调用，第二次返回 finish
    mock_llm.think.side_effect = [
        '{"thought": "需要搜索", "action": {"type": "tool_call", "tool_name": "Search", "input": "测试"}}',
        '{"thought": "已完成", "action": {"type": "finish", "input": "答案"}}'
    ]
    
    mock_tool_executor = Mock()
    mock_tool = Mock(return_value="搜索结果")
    mock_tool_executor.getTool.return_value = mock_tool
    mock_tool_executor.getAvailableTools.return_value = "Search: 搜索工具"
    
    agent = ReActJSONAgent(llm_client=mock_llm, tool_executor=mock_tool_executor, max_steps=5)
    result = agent.run("测试问题")
    
    assert result == "答案"
    assert mock_tool.called
    assert len(mock_llm.think.call_args_list) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_run_with_tool_call -v`
Expected: May fail or pass depending on implementation - verify behavior

**Step 3: Run test to check current behavior**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_run_with_tool_call -v`
Expected: Should PASS if implementation is correct

**Step 4: Commit**

```bash
git add tests/demos/agent-framework/test_react_json.py
git commit -m "test: add tool call integration test"
```

---

## Task 6: Error Handling and Edge Cases

**Files:**
- Modify: `demos/agent-framework/react_json.py`
- Test: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Write tests for edge cases**

```python
def test_parse_output_with_code_block():
    """测试解析代码块中的 JSON"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    
    json_text = '''一些前置文本
```json
{"thought": "思考", "action": {"type": "finish", "input": "答案"}}
```
一些后置文本'''
    
    thought, action = agent._parse_output(json_text)
    assert thought == "思考"
    assert action["type"] == "finish"

def test_parse_output_invalid_json():
    """测试无效 JSON 的处理"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    
    invalid_text = "这不是 JSON 格式"
    thought, action = agent._parse_output(invalid_text)
    assert thought is None
    assert action is None

def test_parse_output_missing_fields():
    """测试缺少字段的 JSON"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    
    json_text = '{"thought": "只有思考"}'
    thought, action = agent._parse_output(json_text)
    assert thought == "只有思考"
    assert action is None
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/demos/agent-framework/test_react_json.py -v`
Expected: All tests PASS (implementation should already handle these cases)

**Step 3: Commit**

```bash
git add tests/demos/agent-framework/test_react_json.py
git commit -m "test: add edge case tests for JSON parsing"
```

---

## Task 7: Main Entry Point

**Files:**
- Modify: `demos/agent-framework/react_json.py`

**Step 1: Add main entry point**

Modify: `demos/agent-framework/react_json.py` - add at end of file:

```python
if __name__ == "__main__":
    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = (
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中"
        "找不到的信息时，应使用此工具。"
    )
    tool_executor.registerTool("Search", search_desc, search)
    agent = ReActJSONAgent(llm_client=llm, tool_executor=tool_executor)
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    agent.run(question)
```

**Step 2: Test manual execution**

Run: `cd demos/agent-framework && python react_json.py`
Expected: Should run without errors (may require .env configuration)

**Step 3: Commit**

```bash
git add demos/agent-framework/react_json.py
git commit -m "feat: add main entry point for react_json"
```

---

## Task 8: Integration Test

**Files:**
- Test: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Write integration test**

```python
def test_full_integration():
    """集成测试：模拟完整的 ReAct 流程"""
    mock_llm = Mock()
    # 模拟多轮对话
    mock_llm.think.side_effect = [
        '{"thought": "需要搜索信息", "action": {"type": "tool_call", "tool_name": "Search", "input": "华为手机"}}',
        '{"thought": "根据搜索结果，可以给出答案", "action": {"type": "finish", "input": "华为最新的手机是 Mate 60 Pro"}}'
    ]
    
    mock_tool_executor = Mock()
    mock_tool = Mock(return_value="华为 Mate 60 Pro 是2023年发布的最新旗舰手机")
    mock_tool_executor.getTool.return_value = mock_tool
    mock_tool_executor.getAvailableTools.return_value = "Search: 搜索工具"
    
    agent = ReActJSONAgent(llm_client=mock_llm, tool_executor=mock_tool_executor, max_steps=5)
    result = agent.run("华为最新的手机是哪一款？")
    
    assert result == "华为最新的手机是 Mate 60 Pro"
    assert mock_tool.called
    assert len(agent.history) == 2  # Action + Observation
```

**Step 2: Run integration test**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_full_integration -v`
Expected: PASS

**Step 3: Run all tests**

Run: `pytest tests/demos/agent-framework/test_react_json.py -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/demos/agent-framework/test_react_json.py
git commit -m "test: add full integration test"
```

---

## Summary

完成所有任务后，`react_json.py` 应该：

1. ✅ 使用 JSON 格式解析 LLM 输出（替代正则表达式）
2. ✅ 支持代码块中的 JSON 和直接 JSON 对象
3. ✅ 正确处理 tool_call 和 finish 两种 action 类型
4. ✅ 保持与原有 `react.py` 相同的接口和行为
5. ✅ 包含完整的错误处理和边界情况处理
6. ✅ 有完整的测试覆盖

**Next Steps:**
- 可以考虑添加 JSON Schema 验证（使用 jsonschema 库）
- 可以考虑添加 fallback 机制（JSON 解析失败时回退到正则表达式）
- 可以考虑性能优化（缓存解析结果等）
