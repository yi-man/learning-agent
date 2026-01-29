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
