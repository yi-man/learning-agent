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

    def run(self, question: str):
        """运行 ReAct 循环，使用 JSON 格式解析"""
        self.history = []
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = self._build_prompt(question, tools_desc, history_str)

            messages = [{"role": "user", "content": prompt}]
            response_text = self.llm_client.think(messages=messages)
            if not response_text:
                print("错误：LLM未能返回有效响应。")
                break

            thought, action = self._parse_output(response_text)
            if thought:
                print(f"🤔 思考: {thought}")
            if not action:
                print("警告：未能解析出有效的Action，流程终止。")
                break

            # 解析 action（现在是 dict）
            tool_name, tool_input = self._parse_action(action)
            if not tool_name:
                self.history.append("Observation: 无效的Action格式，请检查。")
                continue

            if tool_name == "Finish":
                # 如果是Finish指令，提取最终答案并结束
                print(f"🎉 最终答案: {tool_input}")
                return tool_input

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            tool_function = self.tool_executor.getTool(tool_name)
            observation = (
                tool_function(tool_input)
                if tool_function
                else f"错误：未找到名为 '{tool_name}' 的工具。"
            )

            print(f"👀 观察: {observation}")
            # 记录 action 为字符串格式（保持兼容）
            action_str = f"{tool_name}[{tool_input}]"
            self.history.append(f"Action: {action_str}")
            self.history.append(f"Observation: {observation}")

        print("已达到最大步数，流程终止。")
        return None


if __name__ == "__main__":
    from tools import search

    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()
    search_desc = (
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中"
        "找不到的信息时，应使用此工具。"
    )
    tool_executor.registerTool("Search", search_desc, search)
    agent = ReActJSONAgent(llm_client=llm, tool_executor=tool_executor)
    question = "华为最新的手机是哪一款？它的主要卖点是什么？"
    agent.run(question)
