from typing import List, Dict, Any
import json
import re

from error_tracker import ErrorTracker
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
        max_consecutive_errors: int = 3,
    ):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.max_consecutive_errors = max_consecutive_errors
        self.history: List[str] = []
        self.error_tracker = ErrorTracker(max_consecutive_errors=max_consecutive_errors)

    def _build_prompt(self, question: str, tools: str, history: str) -> str:
        """构建包含 JSON 格式要求和错误恢复提示的 prompt"""
        base_prompt = REACT_JSON_PROMPT_TEMPLATE.format(
            tools=tools, question=question, history=history
        )

        # 如果检测到错误模式，添加恢复提示
        if self.error_tracker.should_trigger_recovery():
            error_summary = self.error_tracker.get_error_summary()
            recovery_hint = f"\n\n⚠️ 重要提示：检测到连续工具调用错误（{error_summary}）。请仔细检查可用工具列表，确保使用正确的工具名称和参数格式。"
            base_prompt += recovery_hint

            # 建议正确的工具（基于可用工具列表）
            available_tool_names = [
                line.split(":")[0].strip("- ").strip()
                for line in tools.split("\n")
                if line.strip().startswith("-")
            ]
            if available_tool_names:
                base_prompt += f"\n可用工具名称: {', '.join(available_tool_names)}"

        return base_prompt

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
        """运行 ReAct 循环，使用 JSON 格式解析，集成错误跟踪"""
        self.history = []
        self.error_tracker.reset()
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

            if not tool_function:
                # 工具不存在，记录错误
                error_msg = f"错误：未找到名为 '{tool_name}' 的工具。"
                self.error_tracker.record_error(tool_name, tool_input, error_msg)
                observation = error_msg
            else:
                try:
                    observation = tool_function(tool_input)
                    # 检查是否返回错误消息
                    if isinstance(observation, str) and (
                        "错误" in observation or "Error" in observation.lower()
                    ):
                        self.error_tracker.record_error(
                            tool_name, tool_input, observation
                        )
                    else:
                        self.error_tracker.record_success(tool_name, tool_input)
                except Exception as e:
                    error_msg = f"错误：工具执行失败 - {str(e)}"
                    self.error_tracker.record_error(tool_name, tool_input, error_msg)
                    observation = error_msg

            print(f"👀 观察: {observation}")
            action_str = f"{tool_name}[{tool_input}]"
            self.history.append(f"Action: {action_str}")
            self.history.append(f"Observation: {observation}")

            if self.error_tracker.should_trigger_recovery() and current_step >= 3:
                print("⚠️ 警告：连续工具调用错误过多，建议检查工具配置或问题描述。")

        print("已达到最大步数，流程终止。")
        return None


if __name__ == "__main__":
    from tools import search, calculator

    llm = HelloAgentsLLM()
    tool_executor = ToolExecutor()

    # 注册搜索工具
    search_desc = (
        "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中"
        "找不到的信息时，应使用此工具。"
    )
    tool_executor.registerTool("Search", search_desc, search)

    # 注册计算器工具
    calculator_desc = (
        "一个数学计算器工具。当你需要执行数学计算时，应使用此工具。"
        "支持基础运算（加减乘除、括号）和高级运算（幂、开方、三角函数、对数等）。"
        "输入应该是有效的数学表达式，例如：'(123 + 456) * 789 / 12'"
    )
    tool_executor.registerTool("Calculator", calculator_desc, calculator)

    agent = ReActJSONAgent(
        llm_client=llm,
        tool_executor=tool_executor,
        max_consecutive_errors=3,
    )
    question = "计算 (123 + 456) × 789 / 12 = ? 的结果"
    agent.run(question)
