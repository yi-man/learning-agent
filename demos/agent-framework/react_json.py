from typing import List, Dict, Any
import json
import re

from llm_client import HelloAgentsLLM
from tools import ToolExecutor

REACT_JSON_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下：
{tools}

回答问题时候的注意点:
- 问题中涉及当前时间，需先计算出当前时间

请严格按照以下 JSON 格式进行回应：

```json
{{
  "thought": "你的思考过程，用于分析问题、拆解任务和规划下一步行动",
  "action": {{
    "type": "tool_call" | "finish",
    "tool_name": "工具名称（当 type 为 tool_call 时必需）",
    "input": "工具输入或最终答案（当 type 为 finish 时，这是最终答案）"
  }}
}}
```

重要说明：
- 当 type 为 "tool_call" 时，必须提供 tool_name 和 input
- 当 type 为 "finish" 时，只需提供 input（最终答案）
- 必须输出有效的 JSON，不要添加任何额外的文本或解释

现在，请开始解决以下问题：
Question: {question}
History: {history}
"""


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

    def _build_prompt(self, question: str, tools: str, history: str) -> str:
        """构建包含 JSON 格式要求的 prompt"""
        return REACT_JSON_PROMPT_TEMPLATE.format(
            tools=tools, question=question, history=history
        )

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
            action = data.get("action")  # 返回 dict，不是字符串
            return thought, action
        except (json.JSONDecodeError, KeyError, AttributeError):
            return None, None

    def _parse_action(self, action: Dict[str, Any]):
        """从 JSON action 对象中解析工具名和输入"""
        if not isinstance(action, dict):
            return None, None

        action_type = action.get("type")
        if action_type == "tool_call":
            tool_name = action.get("tool_name")
            tool_input = action.get("input")
            return tool_name, tool_input
        elif action_type == "finish":
            final_answer = action.get("input", "")
            return "Finish", final_answer
        else:
            return None, None
