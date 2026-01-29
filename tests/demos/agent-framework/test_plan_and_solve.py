import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "demos" / "agent-framework")
)

from plan_and_solve import Replanner


def test_replanner_returns_list():
    """Replanner.replan 应返回 list[str] 或空列表"""

    class MockLLM:
        def think(self, messages):
            return '```python\n["新步骤A", "新步骤B"]\n```'

    replanner = Replanner(MockLLM())
    result = replanner.replan(
        question="q",
        plan=["步1", "步2"],
        completed=[],
        failed_step="步1",
        failure_reason="超时",
    )
    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)
    assert result == ["新步骤A", "新步骤B"]


def test_execute_with_replan_on_replan_marker():
    """当步骤返回含 [REPLAN] 时，应调用 Replanner 并用新计划继续执行"""

    class MockLLM:
        def __init__(self):
            self.call_count = 0

        def think(self, messages):
            self.call_count += 1
            if self.call_count == 1:
                return "[REPLAN] 需要更多信息"
            return "替代步骤1的结果"

    from plan_and_solve import Executor

    class MockReplanner:
        def replan(self, question, plan, completed, failed_step, failure_reason):
            return ["替代步骤1"]  # 只替代一步，第二次 think 即返回结果

    llm = MockLLM()
    executor = Executor(llm)
    result = executor.execute(
        question="q",
        plan=["原步1", "原步2"],
        replanner=MockReplanner(),
        max_replans=2,
    )
    assert "替代步骤1的结果" in result or result == "替代步骤1的结果"
