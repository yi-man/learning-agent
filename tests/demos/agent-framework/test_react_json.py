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

    agent = ReActJSONAgent(llm_client=mock_llm, tool_executor=mock_tool_executor, max_steps=5)
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
