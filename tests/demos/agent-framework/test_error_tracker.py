import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "demos" / "agent-framework")
)

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

    assert tracker.should_trigger_recovery() is False  # 2次，未达到阈值
    tracker.record_error("WrongTool", "input3", "工具不存在")
    assert tracker.should_trigger_recovery() is True  # 3次，达到阈值


def test_reset_on_success():
    """测试成功调用后重置错误计数"""
    tracker = ErrorTracker(max_consecutive_errors=3)
    tracker.record_error("WrongTool", "input", "错误")
    tracker.record_error("WrongTool", "input", "错误")
    tracker.record_success("CorrectTool", "input")

    assert tracker.consecutive_errors == 0
    # record_success 只重置 consecutive_errors，不清空 error_patterns
    assert tracker.error_patterns["other_error"] == 2
