"""ReAct JSON Agent runner."""

import json
import re
from typing import Any, Dict, List, Optional

from app.agents.tools import ToolExecutor, get_default_tool_executor
from app.models.openai_client import OpenAIClient

REACT_JSON_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

可用工具如下：
{tools}

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

Question: {question}
History: {history}
Steps: {steps}
"""


class ReActJSONAgent:
    def __init__(
        self,
        llm_client: OpenAIClient,
        tool_executor: Optional[ToolExecutor] = None,
        max_steps: int = 5,
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor or get_default_tool_executor()
        self.max_steps = max_steps

    def _parse_output(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if not json_match:
                    return None
                json_str = json_match.group(0)
            return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError, TypeError):
            return None

    async def run(
        self,
        question: str,
        history_text: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
    ) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        step_history: List[str] = []
        tools_desc = self.tool_executor.get_available_tools()

        for _ in range(self.max_steps):
            prompt = REACT_JSON_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_text,
                steps="\n".join(step_history),
            )

            messages = [{"role": "user", "content": prompt}]
            response_text = await self.llm_client.chat(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                max_completion_tokens=max_completion_tokens,
                reasoning_effort=reasoning_effort,
                stream=False,
            )

            data = self._parse_output(response_text)
            if not data:
                trace.append(
                    {
                        "thought": None,
                        "action": {"type": "finish", "input": "无效的 JSON 输出"},
                        "observation": None,
                    }
                )
                return {"content": "无效的 JSON 输出", "trace": trace}

            thought = data.get("thought")
            action = data.get("action") or {}
            action_type = action.get("type")

            if action_type == "finish":
                final_answer = action.get("input", "")
                trace.append(
                    {"thought": thought, "action": action, "observation": None}
                )
                return {"content": final_answer, "trace": trace}

            if action_type == "tool_call":
                tool_name = action.get("tool_name")
                tool_input = action.get("input", "")
                if not isinstance(tool_name, str) or not tool_name:
                    trace.append(
                        {
                            "thought": thought,
                            "action": action,
                            "observation": "错误：tool_name 为空或无效。",
                        }
                    )
                    return {"content": "错误：tool_name 为空或无效。", "trace": trace}
                observation = self.tool_executor.run_tool(tool_name, tool_input)
                trace.append(
                    {
                        "thought": thought,
                        "action": action,
                        "observation": observation,
                    }
                )
                step_history.append(f"Action: {tool_name}[{tool_input}]")
                step_history.append(f"Observation: {observation}")
                continue

            trace.append(
                {
                    "thought": thought,
                    "action": {"type": "finish", "input": "无效的 action 类型"},
                    "observation": None,
                }
            )
            return {"content": "无效的 action 类型", "trace": trace}

        trace.append(
            {
                "thought": None,
                "action": {"type": "finish", "input": "超过最大步数"},
                "observation": None,
            }
        )
        return {"content": "超过最大步数", "trace": trace}
