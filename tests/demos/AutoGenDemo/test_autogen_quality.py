"""对话质量监控：quality_check 与 select_next_speaker 集成测试"""

import sys
from pathlib import Path

# 保证可导入 demos/AutoGenDemo 下的模块
sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent.parent.parent / "demos" / "AutoGenDemo"),
)

from autogen_software_team import quality_check, select_next_speaker

PARTICIPANT_NAMES = ["ProductManager", "Engineer", "CodeReviewer", "UserProxy"]


def _msg(source: str):
    """构造仅含 source 的模拟消息"""
    m = type("Msg", (), {"source": source})()
    return m


def test_quality_check_no_loop_when_insufficient_messages():
    """消息不足 2*K 时不判循环（K=4，仅 4 条）"""
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 1]
    has_anomaly, reason = quality_check(messages, PARTICIPANT_NAMES)
    assert has_anomaly is False
    assert reason is None


def test_quality_check_no_loop_when_sequence_differs():
    """最近 K 条与前 K 条不一致时不判循环"""
    # 两轮顺序：PM,E,CR,UP,PM,E,CR,UserProxy 但最后一条故意不同
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 2]
    messages[-1] = _msg("Engineer")  # 打破重复
    has_anomaly, reason = quality_check(messages, PARTICIPANT_NAMES)
    assert has_anomaly is False
    assert reason is None


def test_quality_check_detects_loop():
    """连续两轮发言者序列完全相同时判为循环"""
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 2]  # 8 条，后 4 与前 4 相同
    has_anomaly, reason = quality_check(messages, PARTICIPANT_NAMES)
    assert has_anomaly is True
    assert reason == "loop"


def test_select_next_speaker_returns_pm_when_quality_anomaly():
    """当 quality_check 判为循环时，select_next_speaker 返回 ProductManager"""
    messages = [_msg(n) for n in PARTICIPANT_NAMES * 2]
    next_speaker = select_next_speaker(messages, PARTICIPANT_NAMES)
    assert next_speaker == "ProductManager"
