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
