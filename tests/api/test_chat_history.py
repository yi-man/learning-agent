"""对话历史管理模块测试"""

import pytest
from app.api.chat_history import (
    generate_session_id,
    get_history,
    add_message,
    clear_history,
    merge_history_and_messages,
    MAX_HISTORY_MESSAGES,
)


def test_generate_session_id():
    """测试生成会话 ID"""
    session_id = generate_session_id()
    assert isinstance(session_id, str)
    assert len(session_id) > 0
    # 验证 UUID 格式
    assert session_id.count("-") == 4


def test_get_history_empty():
    """测试获取空历史"""
    session_id = generate_session_id()
    history = get_history(session_id)
    assert history == []


def test_add_message():
    """测试添加消息"""
    session_id = generate_session_id()
    add_message(session_id, "user", "Hello")
    add_message(session_id, "assistant", "Hi there")

    history = get_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there"


def test_history_limit():
    """测试历史消息数量限制"""
    session_id = generate_session_id()
    # 添加超过限制的消息
    for i in range(MAX_HISTORY_MESSAGES + 5):
        add_message(session_id, "user", f"Message {i}")

    history = get_history(session_id)
    assert len(history) == MAX_HISTORY_MESSAGES
    # 应该保留最新的消息
    assert history[-1]["content"] == f"Message {MAX_HISTORY_MESSAGES + 4}"


def test_clear_history():
    """测试清除历史"""
    session_id = generate_session_id()
    add_message(session_id, "user", "Hello")
    assert len(get_history(session_id)) == 1

    clear_history(session_id)
    assert len(get_history(session_id)) == 0


def test_merge_history_and_messages():
    """测试合并历史和当前消息"""
    session_id = generate_session_id()
    add_message(session_id, "user", "First")
    add_message(session_id, "assistant", "Response")

    current_messages = [{"role": "user", "content": "Second"}]
    merged = merge_history_and_messages(session_id, current_messages)

    assert len(merged) == 3
    assert merged[0]["content"] == "First"
    assert merged[2]["content"] == "Second"


def test_merge_without_session_id():
    """测试无 session_id 时只返回当前消息"""
    current_messages = [{"role": "user", "content": "Hello"}]
    merged = merge_history_and_messages(None, current_messages)
    assert merged == current_messages
