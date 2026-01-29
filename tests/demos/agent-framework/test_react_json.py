import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "demos" / "agent-framework")
)

from react_json import ReActJSONAgent


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


def test_prompt_contains_json_format():
    """测试 prompt 包含 JSON 格式要求"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)
    prompt = agent._build_prompt("测试问题", "工具描述", "")

    assert "JSON" in prompt or "json" in prompt
    assert "thought" in prompt.lower()
    assert "action" in prompt.lower()


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


def test_run_with_finish_action():
    """测试 run 方法处理 finish action"""
    from unittest.mock import Mock

    mock_llm = Mock()
    mock_llm.think.return_value = (
        '{"thought": "已完成", "action": {"type": "finish", "input": "最终答案"}}'
    )

    mock_tool_executor = Mock()
    mock_tool_executor.getAvailableTools.return_value = "工具列表"

    agent = ReActJSONAgent(llm_client=mock_llm, tool_executor=mock_tool_executor)
    result = agent.run("测试问题")

    assert result == "最终答案"
    mock_llm.think.assert_called_once()


def test_run_with_tool_call():
    """测试 run 方法处理工具调用"""
    from unittest.mock import Mock

    mock_llm = Mock()
    # 第一次调用返回工具调用，第二次返回 finish
    mock_llm.think.side_effect = [
        '{"thought": "需要搜索", "action": {"type": "tool_call", "tool_name": "Search", "input": "测试"}}',
        '{"thought": "已完成", "action": {"type": "finish", "input": "答案"}}',
    ]

    mock_tool_executor = Mock()
    mock_tool = Mock(return_value="搜索结果")
    mock_tool_executor.getTool.return_value = mock_tool
    mock_tool_executor.getAvailableTools.return_value = "Search: 搜索工具"

    agent = ReActJSONAgent(
        llm_client=mock_llm, tool_executor=mock_tool_executor, max_steps=5
    )
    result = agent.run("测试问题")

    assert result == "答案"
    assert mock_tool.called
    assert len(mock_llm.think.call_args_list) == 2


def test_parse_output_with_code_block():
    """测试解析代码块中的 JSON"""
    agent = ReActJSONAgent(llm_client=None, tool_executor=None)

    json_text = """一些前置文本
```json
{"thought": "思考", "action": {"type": "finish", "input": "答案"}}
```
一些后置文本"""

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


def test_agent_tracks_tool_errors():
    """测试智能体跟踪工具错误"""
    from unittest.mock import Mock

    mock_llm = Mock()
    mock_llm.think.side_effect = [
        '{"thought": "尝试调用工具", "action": {"type": "tool_call", "tool_name": "NonExistentTool", "input": "test"}}',
        '{"thought": "再次尝试", "action": {"type": "tool_call", "tool_name": "NonExistentTool", "input": "test"}}',
        '{"thought": "使用正确工具", "action": {"type": "tool_call", "tool_name": "Search", "input": "test"}}',
        '{"thought": "已有结果", "action": {"type": "finish", "input": "测试答案"}}',
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
        max_consecutive_errors=2,
    )

    # 运行智能体
    agent.run("测试问题")

    # 验证错误被跟踪
    assert agent.error_tracker.consecutive_errors == 0  # 最后一次成功，已重置
    assert agent.error_tracker.error_patterns["tool_not_found"] >= 2


def test_agent_uses_calculator():
    """测试智能体使用计算器工具"""
    from unittest.mock import Mock
    from tools import calculator, ToolExecutor

    mock_llm = Mock()
    mock_llm.think.side_effect = [
        '{"thought": "需要计算表达式", "action": {"type": "tool_call", "tool_name": "Calculator", "input": "(123 + 456) * 789 / 12"}}',
        '{"thought": "计算完成，可以给出答案", "action": {"type": "finish", "input": "结果是 38069.25"}}',
    ]

    tool_executor = ToolExecutor()
    tool_executor.registerTool("Calculator", "计算器工具", calculator)

    agent = ReActJSONAgent(
        llm_client=mock_llm, tool_executor=tool_executor, max_steps=5
    )
    result = agent.run("计算 (123 + 456) * 789 / 12")

    assert "38069.25" in result or "38069" in result


def test_error_recovery_mechanism():
    """测试错误恢复机制"""
    from unittest.mock import Mock
    from tools import calculator, ToolExecutor

    mock_llm = Mock()
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
        max_consecutive_errors=3,
    )
    result = agent.run("计算 2 + 3")

    assert agent.error_tracker.error_patterns["tool_not_found"] >= 3
    assert "5" in result
    assert agent.error_tracker.consecutive_errors == 0


def test_full_integration():
    """集成测试：模拟完整的 ReAct 流程"""
    from unittest.mock import Mock

    mock_llm = Mock()
    # 模拟多轮对话
    mock_llm.think.side_effect = [
        '{"thought": "需要搜索信息", "action": {"type": "tool_call", "tool_name": "Search", "input": "华为手机"}}',
        '{"thought": "根据搜索结果，可以给出答案", "action": {"type": "finish", "input": "华为最新的手机是 Mate 60 Pro"}}',
    ]

    mock_tool_executor = Mock()
    mock_tool = Mock(return_value="华为 Mate 60 Pro 是2023年发布的最新旗舰手机")
    mock_tool_executor.getTool.return_value = mock_tool
    mock_tool_executor.getAvailableTools.return_value = "Search: 搜索工具"

    agent = ReActJSONAgent(
        llm_client=mock_llm, tool_executor=mock_tool_executor, max_steps=5
    )
    result = agent.run("华为最新的手机是哪一款？")

    assert result == "华为最新的手机是 Mate 60 Pro"
    assert mock_tool.called
    assert len(agent.history) == 2  # Action + Observation
