from collections import defaultdict
from typing import Dict, List


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
        elif (
            "参数" in error_message
            or "格式" in error_message
            or "invalid" in error_message.lower()
        ):
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
            summary_parts.append(
                f"工具不存在错误: {self.error_patterns['tool_not_found']}次"
            )
        if self.error_patterns["parameter_error"] > 0:
            summary_parts.append(
                f"参数错误: {self.error_patterns['parameter_error']}次"
            )

        if self.failed_tools:
            most_failed = max(self.failed_tools.items(), key=lambda x: x[1])
            summary_parts.append(
                f"最常失败的工具: {most_failed[0]} ({most_failed[1]}次)"
            )

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
