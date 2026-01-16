"""对话历史管理模块"""
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional

# 内存存储对话历史
# 格式: {session_id: [{"role": "user", "content": "..."}, ...]}
chat_histories: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

# 最大历史消息数（避免 token 超限）
MAX_HISTORY_MESSAGES = 20


def generate_session_id() -> str:
    """生成新的会话 ID"""
    return str(uuid.uuid4())


def get_history(session_id: str) -> List[Dict[str, Any]]:
    """获取指定会话的历史消息"""
    return chat_histories.get(session_id, [])


def add_message(session_id: str, role: str, content: Any):
    """添加消息到历史记录"""
    if session_id not in chat_histories:
        chat_histories[session_id] = []

    chat_histories[session_id].append({
        "role": role,
        "content": content
    })

    # 限制历史长度，只保留最近的 N 条消息
    if len(chat_histories[session_id]) > MAX_HISTORY_MESSAGES:
        # 保留最近的 N 条消息（从后往前取）
        chat_histories[session_id] = chat_histories[session_id][-MAX_HISTORY_MESSAGES:]


def clear_history(session_id: str):
    """清除指定会话的历史"""
    if session_id in chat_histories:
        del chat_histories[session_id]


def merge_history_and_messages(
    session_id: Optional[str],
    current_messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    合并历史消息和当前消息

    Args:
        session_id: 会话 ID，如果为 None 则不使用历史
        current_messages: 当前请求的消息列表

    Returns:
        合并后的消息列表
    """
    if not session_id:
        return current_messages

    history = get_history(session_id)
    # 合并历史消息和当前消息
    return history + current_messages
