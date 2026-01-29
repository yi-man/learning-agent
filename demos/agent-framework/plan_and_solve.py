import ast
from llm_client import HelloAgentsLLM
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量，处理文件不存在异常
try:
    load_dotenv()
except FileNotFoundError:
    print("警告：未找到 .env 文件，将使用系统环境变量。")
except Exception as e:
    print(f"警告：加载 .env 文件时出错: {e}")

# --- 1. LLM客户端定义 ---
# 假设你已经有llm_client.py文件，里面定义了HelloAgentsLLM类

# --- 2. 规划器 (Planner) 定义 ---
PLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。
你的输出必须是一个Python列表，其中每个元素都是一个描述子任务的字符串。

问题: {question}

请严格按照以下格式输出你的计划，```python与```作为前后缀是必要的:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""


class Planner:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def plan(self, question: str) -> list[str]:
        prompt = PLANNER_PROMPT_TEMPLATE.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        print("--- 正在生成计划 ---")
        response_text = self.llm_client.think(messages=messages) or ""
        print(f"✅ 计划已生成:\n{response_text}")

        try:
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except (ValueError, SyntaxError, IndexError) as e:
            print(f"❌ 解析计划时出错: {e}")
            print(f"原始响应: {response_text}")
            return []
        except Exception as e:
            print(f"❌ 解析计划时发生未知错误: {e}")
            return []


# --- 2.5 重规划器 (Replanner) 定义 ---
REPLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。原计划在执行某一步时失败或需要调整，请基于当前状态给出从当前起的新计划。
输入：原问题、原计划、已完成步骤与结果、失败的步骤及原因。
请输出从当前起的新步骤列表（可省略已完成部分）。若认为任务无法继续，可输出空列表 []。

# 原问题:
{question}

# 原计划:
{plan}

# 已完成步骤与结果:
{completed}

# 失败的步骤:
{failed_step}

# 失败原因:
{failure_reason}

请严格按照以下格式输出新计划，```python与```作为前后缀是必要的:
```python
["步骤A", "步骤B", ...]
```
或
```python
[]
```
"""


class Replanner:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def replan(
        self,
        question: str,
        plan: list[str],
        completed: list[tuple[str, str]],
        failed_step: str,
        failure_reason: str,
    ) -> list[str]:
        completed_str = "\n".join(f"步骤: {s}\n结果: {r}" for s, r in completed) or "无"
        prompt = REPLANNER_PROMPT_TEMPLATE.format(
            question=question,
            plan=plan,
            completed=completed_str,
            failed_step=failed_step,
            failure_reason=failure_reason,
        )
        messages = [{"role": "user", "content": prompt}]
        response_text = self.llm_client.think(messages=messages) or ""
        try:
            plan_str = response_text.split("```python")[1].split("```")[0].strip()
            new_plan = ast.literal_eval(plan_str)
            return new_plan if isinstance(new_plan, list) else []
        except (ValueError, SyntaxError, IndexError, TypeError):
            return []


# --- 3. 执行器 (Executor) 定义 ---
EXECUTOR_PROMPT_TEMPLATE = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决“当前步骤”，并仅输出该步骤的最终答案，不要输出任何额外的解释或对话。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请仅输出针对“当前步骤”的回答:
"""


def _parse_replan_reason(response_text: str) -> str:
    """从含 [REPLAN] 的回复中解析原因。"""
    if "[REPLAN]" not in response_text:
        return ""
    part = response_text.split("[REPLAN]", 1)[-1].strip()
    return part[:200] if part else "执行器请求重规划"


class Executor:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def execute_one_step(
        self,
        question: str,
        plan: list[str],
        history: str,
        current_step: str,
    ) -> str:
        """执行单步，返回该步的回复文本。"""
        prompt = EXECUTOR_PROMPT_TEMPLATE.format(
            question=question,
            plan=plan,
            history=history if history else "无",
            current_step=current_step,
        )
        messages = [{"role": "user", "content": prompt}]
        return self.llm_client.think(messages=messages) or ""

    def execute(
        self,
        question: str,
        plan: list[str],
        replanner: Replanner | None = None,
        max_replans: int = 2,
    ) -> str:
        remaining_plan = list(plan)
        completed: list[tuple[str, str]] = []
        replan_count = 0
        final_answer = ""
        step_index = 0

        print("\n--- 正在执行计划 ---")
        while remaining_plan and replan_count <= max_replans:
            current_step = remaining_plan[0]
            step_index += 1
            print(f"\n-> 正在执行步骤 {step_index}/{len(plan)}: {current_step}")
            history = "\n".join(
                f"步骤: {s}\n结果: {r}" for s, r in completed
            ) or "无"

            try:
                response_text = self.execute_one_step(
                    question=question,
                    plan=plan,
                    history=history,
                    current_step=current_step,
                )
            except Exception as e:
                response_text = f"[REPLAN] {e!s}"

            if "[REPLAN]" in response_text and replanner is not None:
                reason = _parse_replan_reason(response_text) or "执行器请求重规划"
                new_plan = replanner.replan(
                    question=question,
                    plan=plan,
                    completed=completed,
                    failed_step=current_step,
                    failure_reason=reason,
                )
                replan_count += 1
                remaining_plan = new_plan if new_plan else []
                if not remaining_plan:
                    break
                continue

            completed.append((current_step, response_text))
            remaining_plan.pop(0)
            final_answer = response_text
            print(f"✅ 步骤 {step_index} 已完成，结果: {final_answer}")

        return final_answer


# --- 4. 智能体 (Agent) 整合 ---
class PlanAndSolveAgent:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client
        self.planner = Planner(self.llm_client)
        self.executor = Executor(self.llm_client)
        self.replanner = Replanner(self.llm_client)

    def run(self, question: str):
        print(f"\n--- 开始处理问题 ---\n问题: {question}")
        plan = self.planner.plan(question)
        if not plan:
            print("\n--- 任务终止 --- \n无法生成有效的行动计划。")
            return
        final_answer = self.executor.execute(
            question,
            plan,
            replanner=self.replanner,
            max_replans=2,
        )
        print(f"\n--- 任务完成 ---\n最终答案: {final_answer}")


# --- 5. 主函数入口 ---
if __name__ == "__main__":
    try:
        llm_client = HelloAgentsLLM()
        agent = PlanAndSolveAgent(llm_client)
        question = (
            "一个水果店周一卖出了15个苹果。周二卖出的苹果数量是周一的两倍。"
            "周三卖出的数量比周二少了5个。请问这三天总共卖出了多少个苹果？"
        )
        agent.run(question)
    except ValueError as e:
        print(e)
