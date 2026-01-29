from typing import List
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
        try:
            # 尝试提取 JSON（可能在代码块中）
            json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # 尝试直接查找 JSON 对象
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
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
