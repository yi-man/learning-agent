# ReAct 计算器工具和错误恢复机制实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 ReActJSONAgent 添加计算器工具（支持复杂数学表达式）和工具选择失败的处理机制（检测连续错误并引导智能体纠正）

**Architecture:** 
- 在 `tools.py` 中添加安全的计算器工具函数，使用受限的 `eval` 执行数学表达式
- 在 `ReActJSONAgent` 中添加错误跟踪器（`ErrorTracker`），记录工具调用失败历史
- 实现错误检测逻辑：统计连续失败次数、检测错误模式（重复调用不存在工具、参数格式错误等）
- 实现恢复策略：在 prompt 中添加错误提示、建议正确工具、达到阈值后降级处理

**Tech Stack:** Python, ast (标准库), pytest (测试)

---

## Task 1: 计算器工具实现

**Files:**
- Modify: `demos/agent-framework/tools.py`
- Test: `tests/demos/agent-framework/test_tools.py` (新建)

**Step 1: Write the failing test for calculator tool**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "demos" / "agent-framework"))

from tools import calculator

def test_calculator_basic_operations():
    """测试基础数学运算"""
    assert calculator("2 + 3") == "5"
    assert calculator("10 - 4") == "6"
    assert calculator("3 * 4") == "12"
    assert calculator("15 / 3") == "5.0"

def test_calculator_complex_expression():
    """测试复杂表达式"""
    assert calculator("(123 + 456) * 789 / 12") == "38032.5"
    assert calculator("2 ** 3") == "8"
    assert calculator("(10 + 5) * 2 - 3") == "27"

def test_calculator_invalid_input():
    """测试无效输入"""
    result = calculator("invalid expression")
    assert "错误" in result or "Error" in result.lower()

def test_calculator_security():
    """测试安全性（不应执行危险代码）"""
    # 尝试执行非数学表达式
    result = calculator("__import__('os').system('ls')")
    assert "错误" in result or "Error" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_tools.py::test_calculator_basic_operations -v`
Expected: FAIL with "NameError: name 'calculator' is not defined"

**Step 3: Implement calculator function**

在 `tools.py` 中添加：

```python
import math

def calculator(expression: str) -> str:
    """
    一个安全的数学计算器工具，可以执行数学表达式。
    支持基础运算（加减乘除、括号）和高级运算（幂、开方、三角函数、对数等）。
    
    参数:
        expression: 数学表达式字符串，例如 "(123 + 456) * 789 / 12"
    
    返回:
        计算结果字符串，如果出错则返回错误信息
    """
    print(f"🧮 正在执行 [Calculator] 计算: {expression}")
    try:
        # 创建安全的操作符字典
        safe_dict = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "math": math,
        }
        
        # 使用 eval 执行表达式（在受限环境中）
        result = eval(expression, safe_dict)
        
        # 格式化结果
        if isinstance(result, float):
            # 如果是整数形式的浮点数，返回整数
            if result.is_integer():
                return str(int(result))
            return str(result)
        return str(result)
    except Exception as e:
        return f"错误：计算失败 - {str(e)}。请确保表达式是有效的数学表达式。"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/tools.py tests/demos/agent-framework/test_tools.py
git commit -m "feat: add calculator tool with safe eval"
```

---

## Task 2: 错误跟踪器实现

**Files:**
- Create: `demos/agent-framework/error_tracker.py`
- Test: `tests/demos/agent-framework/test_error_tracker.py` (新建)

**Step 1: Write the failing test for ErrorTracker**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "demos" / "agent-framework"))

from error_tracker import ErrorTracker

def test_track_tool_not_found():
    """测试记录工具不存在错误"""
    tracker = ErrorTracker(max_consecutive_errors=3)
    tracker.record_error("NonExistentTool", "input", "工具不存在")
    
    assert tracker.consecutive_errors == 1
    assert tracker.error_patterns["tool_not_found"] == 1

def test_track_parameter_error():
    """测试记录参数错误"""
    tracker = ErrorTracker(max_consecutive_errors=3)
    tracker.record_error("Calculator", "invalid", "参数格式错误")
    
    assert tracker.consecutive_errors == 1
    assert tracker.error_patterns["parameter_error"] == 1

def test_detect_repeated_errors():
    """测试检测重复错误"""
    tracker = ErrorTracker(max_consecutive_errors=3)
    tracker.record_error("WrongTool", "input1", "工具不存在")
    tracker.record_error("WrongTool", "input2", "工具不存在")
    
    assert tracker.should_trigger_recovery() == False  # 2次，未达到阈值
    tracker.record_error("WrongTool", "input3", "工具不存在")
    assert tracker.should_trigger_recovery() == True  # 3次，达到阈值

def test_reset_on_success():
    """测试成功调用后重置错误计数"""
    tracker = ErrorTracker(max_consecutive_errors=3)
    tracker.record_error("WrongTool", "input", "错误")
    tracker.record_error("WrongTool", "input", "错误")
    tracker.record_success("CorrectTool", "input")
    
    assert tracker.consecutive_errors == 0
    assert tracker.error_patterns == {}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_error_tracker.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'error_tracker'"

**Step 3: Implement ErrorTracker class**

创建 `demos/agent-framework/error_tracker.py`:

```python
from typing import Dict, List
from collections import defaultdict

class ErrorTracker:
    """
    跟踪工具调用错误，检测错误模式并触发恢复机制
    """
    
    def __init__(self, max_consecutive_errors: int = 3):
        """
        初始化错误跟踪器
        
        参数:
            max_consecutive_errors: 触发恢复机制的最大连续错误次数
        """
        self.max_consecutive_errors = max_consecutive_errors
        self.consecutive_errors = 0
        self.error_history: List[Dict[str, str]] = []
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self.failed_tools: Dict[str, int] = defaultdict(int)  # 工具名 -> 失败次数
    
    def record_error(self, tool_name: str, tool_input: str, error_message: str):
        """
        记录一次工具调用错误
        
        参数:
            tool_name: 工具名称
            tool_input: 工具输入
            error_message: 错误消息
        """
        self.consecutive_errors += 1
        error_record = {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "error_message": error_message,
        }
        self.error_history.append(error_record)
        
        # 分析错误类型
        if "未找到" in error_message or "不存在" in error_message:
            self.error_patterns["tool_not_found"] += 1
        elif "参数" in error_message or "格式" in error_message or "invalid" in error_message.lower():
            self.error_patterns["parameter_error"] += 1
        else:
            self.error_patterns["other_error"] += 1
        
        # 记录失败的工具
        self.failed_tools[tool_name] += 1
    
    def record_success(self, tool_name: str, tool_input: str):
        """
        记录一次成功的工具调用，重置连续错误计数
        
        参数:
            tool_name: 工具名称
            tool_input: 工具输入
        """
        self.consecutive_errors = 0
    
    def should_trigger_recovery(self) -> bool:
        """
        判断是否应该触发恢复机制
        
        返回:
            True 如果连续错误次数达到阈值
        """
        return self.consecutive_errors >= self.max_consecutive_errors
    
    def get_error_summary(self) -> str:
        """
        获取错误摘要，用于生成恢复提示
        
        返回:
            错误摘要字符串
        """
        if not self.error_history:
            return ""
        
        summary_parts = []
        if self.error_patterns["tool_not_found"] > 0:
            summary_parts.append(f"工具不存在错误: {self.error_patterns['tool_not_found']}次")
        if self.error_patterns["parameter_error"] > 0:
            summary_parts.append(f"参数错误: {self.error_patterns['parameter_error']}次")
        
        if self.failed_tools:
            most_failed = max(self.failed_tools.items(), key=lambda x: x[1])
            summary_parts.append(f"最常失败的工具: {most_failed[0]} ({most_failed[1]}次)")
        
        return "；".join(summary_parts)
    
    def get_recent_errors(self, count: int = 3) -> List[Dict[str, str]]:
        """
        获取最近的错误记录
        
        参数:
            count: 返回的记录数量
        
        返回:
            最近的错误记录列表
        """
        return self.error_history[-count:]
    
    def reset(self):
        """重置所有错误跟踪"""
        self.consecutive_errors = 0
        self.error_history = []
        self.error_patterns = defaultdict(int)
        self.failed_tools = defaultdict(int)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_error_tracker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/error_tracker.py tests/demos/agent-framework/test_error_tracker.py
git commit -m "feat: add ErrorTracker for tool error monitoring"
```

---

## Task 3: 集成错误跟踪到 ReActJSONAgent

**Files:**
- Modify: `demos/agent-framework/react_json.py`
- Test: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Write the failing test for error recovery integration**

```python
def test_agent_tracks_tool_errors():
    """测试智能体跟踪工具错误"""
    from unittest.mock import Mock
    from error_tracker import ErrorTracker
    
    mock_llm = Mock()
    mock_llm.think.side_effect = [
        '{"thought": "尝试调用工具", "action": {"type": "tool_call", "tool_name": "NonExistentTool", "input": "test"}}',
        '{"thought": "再次尝试", "action": {"type": "tool_call", "tool_name": "NonExistentTool", "input": "test"}}',
        '{"thought": "使用正确工具", "action": {"type": "tool_call", "tool_name": "Search", "input": "test"}}',
    ]
    
    mock_tool_executor = Mock()
    mock_tool_executor.getTool.side_effect = [
        None,  # 第一次：工具不存在
        None,  # 第二次：工具不存在
        Mock(return_value="搜索结果"),  # 第三次：成功
    ]
    mock_tool_executor.getAvailableTools.return_value = "- Search: 搜索工具"
    
    agent = ReActJSONAgent(
        llm_client=mock_llm,
        tool_executor=mock_tool_executor,
        max_steps=5,
        max_consecutive_errors=2
    )
    
    # 运行智能体
    agent.run("测试问题")
    
    # 验证错误被跟踪
    assert agent.error_tracker.consecutive_errors == 0  # 最后一次成功，已重置
    assert agent.error_tracker.error_patterns["tool_not_found"] >= 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_agent_tracks_tool_errors -v`
Expected: FAIL (ErrorTracker not integrated yet)

**Step 3: Integrate ErrorTracker into ReActJSONAgent**

修改 `react_json.py`:

```python
from error_tracker import ErrorTracker

class ReActJSONAgent:
    def __init__(
        self,
        llm_client: HelloAgentsLLM,
        tool_executor: ToolExecutor,
        max_steps: int = 5,
        max_consecutive_errors: int = 3,
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.max_consecutive_errors = max_consecutive_errors
        self.history: List[str] = []
        self.error_tracker = ErrorTracker(max_consecutive_errors=max_consecutive_errors)

    def _build_prompt(self, question: str, tools: str, history: str) -> str:
        """构建包含 JSON 格式要求和错误恢复提示的 prompt"""
        base_prompt = REACT_JSON_PROMPT_TEMPLATE.format(
            tools=tools, question=question, history=history
        )
        
        # 如果检测到错误模式，添加恢复提示
        if self.error_tracker.should_trigger_recovery():
            error_summary = self.error_tracker.get_error_summary()
            recovery_hint = f"\n\n⚠️ 重要提示：检测到连续工具调用错误（{error_summary}）。请仔细检查可用工具列表，确保使用正确的工具名称和参数格式。"
            base_prompt += recovery_hint
            
            # 建议正确的工具（基于可用工具列表）
            available_tool_names = [line.split(":")[0].strip("- ") for line in tools.split("\n") if line.strip().startswith("-")]
            if available_tool_names:
                base_prompt += f"\n可用工具名称: {', '.join(available_tool_names)}"
        
        return base_prompt

    def run(self, question: str):
        """运行 ReAct 循环，使用 JSON 格式解析，集成错误跟踪"""
        self.history = []
        self.error_tracker.reset()  # 重置错误跟踪
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
            
            if not tool_function:
                # 工具不存在，记录错误
                error_msg = f"错误：未找到名为 '{tool_name}' 的工具。"
                self.error_tracker.record_error(tool_name, tool_input, error_msg)
                observation = error_msg
            else:
                try:
                    observation = tool_function(tool_input)
                    # 检查是否返回错误消息
                    if isinstance(observation, str) and ("错误" in observation or "Error" in observation.lower()):
                        self.error_tracker.record_error(tool_name, tool_input, observation)
                    else:
                        # 成功调用
                        self.error_tracker.record_success(tool_name, tool_input)
                except Exception as e:
                    # 工具执行异常
                    error_msg = f"错误：工具执行失败 - {str(e)}"
                    self.error_tracker.record_error(tool_name, tool_input, error_msg)
                    observation = error_msg

            print(f"👀 观察: {observation}")
            action_str = f"{tool_name}[{tool_input}]"
            self.history.append(f"Action: {action_str}")
            self.history.append(f"Observation: {observation}")
            
            # 如果达到最大错误次数，考虑降级处理
            if self.error_tracker.should_trigger_recovery() and current_step >= 3:
                print("⚠️ 警告：连续工具调用错误过多，建议检查工具配置或问题描述。")
                # 可以选择继续或提前终止
                # break  # 可选：提前终止

        print("已达到最大步数，流程终止。")
        return None
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/demos/agent-framework/test_react_json.py::test_agent_tracks_tool_errors -v`
Expected: PASS

**Step 5: Commit**

```bash
git add demos/agent-framework/react_json.py tests/demos/agent-framework/test_react_json.py
git commit -m "feat: integrate ErrorTracker into ReActJSONAgent"
```

---

## Task 4: 注册计算器工具并更新示例

**Files:**
- Modify: `demos/agent-framework/react_json.py` (main 部分)

**Step 1: Update main example to include calculator**

修改 `react_json.py` 的 `__main__` 部分：

```python
if __name__ == "__main__":
    from tools import search, calculator

    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    
    # 注册搜索工具
    search_desc = (
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中"
        "找不到的信息时，应使用此工具。"
    )
    tool_executor.registerTool("Search", search_desc, search)
    
    # 注册计算器工具
    calculator_desc = (
        "一个数学计算器工具。当你需要执行数学计算时，应使用此工具。"
        "支持基础运算（加减乘除、括号）和高级运算（幂、开方、三角函数、对数等）。"
        "输入应该是有效的数学表达式，例如：'(123 + 456) * 789 / 12'"
    )
    tool_executor.registerTool("Calculator", calculator_desc, calculator)
    
    agent = ReActJSONAgent(llm_client=llm, tool_executor=tool_executor, max_consecutive_errors=3)
    question = "计算 (123 + 456) × 789 / 12 = ? 的结果"
    agent.run(question)
```

**Step 2: Test the example manually**

Run: `cd demos/agent-framework && python react_json.py`
Expected: Agent should use Calculator tool and return the result

**Step 3: Commit**

```bash
git add demos/agent-framework/react_json.py
git commit -m "feat: register calculator tool in ReActJSONAgent example"
```

---

## Task 5: 集成测试和文档

**Files:**
- Modify: `tests/demos/agent-framework/test_react_json.py`

**Step 1: Add integration test for calculator**

```python
def test_agent_uses_calculator():
    """测试智能体使用计算器工具"""
    from unittest.mock import Mock
    from tools import calculator, ToolExecutor
    
    mock_llm = Mock()
    mock_llm.think.side_effect = [
        '{"thought": "需要计算表达式", "action": {"type": "tool_call", "tool_name": "Calculator", "input": "(123 + 456) * 789 / 12"}}',
        '{"thought": "计算完成，可以给出答案", "action": {"type": "finish", "input": "结果是 38032.5"}}',
    ]
    
    tool_executor = ToolExecutor()
    tool_executor.registerTool("Calculator", "计算器工具", calculator)
    
    agent = ReActJSONAgent(llm_client=mock_llm, tool_executor=tool_executor, max_steps=5)
    result = agent.run("计算 (123 + 456) * 789 / 12")
    
    assert "38032.5" in result or "38032" in result
```

**Step 2: Add integration test for error recovery**

```python
def test_error_recovery_mechanism():
    """测试错误恢复机制"""
    from unittest.mock import Mock
    from tools import calculator, ToolExecutor
    
    mock_llm = Mock()
    # 模拟连续3次调用错误工具，然后使用正确工具
    mock_llm.think.side_effect = [
        '{"thought": "尝试错误工具", "action": {"type": "tool_call", "tool_name": "WrongTool", "input": "test"}}',
        '{"thought": "再次尝试错误工具", "action": {"type": "tool_call", "tool_name": "WrongTool", "input": "test"}}',
        '{"thought": "第三次尝试错误工具", "action": {"type": "tool_call", "tool_name": "WrongTool", "input": "test"}}',
        '{"thought": "使用正确工具", "action": {"type": "tool_call", "tool_name": "Calculator", "input": "2 + 3"}}',
        '{"thought": "完成", "action": {"type": "finish", "input": "答案是 5"}}',
    ]
    
    tool_executor = ToolExecutor()
    tool_executor.registerTool("Calculator", "计算器工具", calculator)
    
    agent = ReActJSONAgent(
        llm_client=mock_llm,
        tool_executor=tool_executor,
        max_steps=10,
        max_consecutive_errors=3
    )
    result = agent.run("计算 2 + 3")
    
    # 验证错误被跟踪
    assert agent.error_tracker.error_patterns["tool_not_found"] >= 3
    # 验证最终成功
    assert "5" in result
    # 验证最后一次调用重置了错误计数
    assert agent.error_tracker.consecutive_errors == 0
```

**Step 3: Run all tests**

Run: `pytest tests/demos/agent-framework/ -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add tests/demos/agent-framework/test_react_json.py
git commit -m "test: add integration tests for calculator and error recovery"
```

---

## 总结

本计划实现了：

1. **计算器工具** (`tools.py`): 使用安全的 `eval` 执行数学表达式，支持复杂计算
2. **错误跟踪器** (`error_tracker.py`): 跟踪工具调用错误，检测错误模式（工具不存在、参数错误等）
3. **错误恢复机制** (`react_json.py`): 
   - 检测连续错误（结合失败次数和错误模式）
   - 在 prompt 中添加错误提示
   - 建议正确的工具名称
   - 达到阈值后警告或降级处理
4. **完整测试**: 单元测试和集成测试覆盖所有功能

所有代码遵循 TDD 原则，先写测试再实现功能。
