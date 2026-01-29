import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "demos" / "agent-framework")
)

from tools import calculator


def test_calculator_basic_operations():
    """测试基础数学运算"""
    assert calculator("2 + 3") == "5"
    assert calculator("10 - 4") == "6"
    assert calculator("3 * 4") == "12"
    assert calculator("15 / 3") == "5"  # 整数形式浮点返回为整数


def test_calculator_complex_expression():
    """测试复杂表达式"""
    assert calculator("(123 + 456) * 789 / 12") == "38069.25"  # (579*789)/12
    assert calculator("2 ** 3") == "8"
    assert calculator("(10 + 5) * 2 - 3") == "27"


def test_calculator_invalid_input():
    """测试无效输入"""
    result = calculator("invalid expression")
    assert "错误" in result or "Error" in result.lower()


def test_calculator_security():
    """测试安全性（不应执行危险代码）"""
    # 尝试执行非数学表达式
    result = calculator("__import__('os').system('ls')")
    assert "错误" in result or "Error" in result.lower()
