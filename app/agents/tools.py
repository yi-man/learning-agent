"""Agent tools and executor."""

import math
import os
from typing import Any, Callable, Dict, Optional

from serpapi import SerpApiClient  # type: ignore[import-untyped]


def calculator(expression: str) -> str:
    """安全的数学计算器工具"""
    try:
        safe_dict = {
            "__builtins__": {},
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "math": math,
        }
        result = eval(expression, safe_dict)
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(result)
    except Exception as e:
        return f"错误：计算失败 - {str(e)}。请确保表达式是有效的数学表达式。"


def search(query: str) -> str:
    """基于 SerpApi 的搜索工具"""
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "错误：SERPAPI_API_KEY 未在环境变量中配置。"

        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "gl": "cn",
            "hl": "zh-cn",
        }
        client = SerpApiClient(params)
        results = client.get_dict()

        if "answer_box_list" in results:
            return "\n".join(results["answer_box_list"])
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
            return results["knowledge_graph"]["description"]
        if "organic_results" in results and results["organic_results"]:
            snippets = [
                f"[{i+1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                for i, res in enumerate(results["organic_results"][:3])
            ]
            return "\n\n".join(snippets)

        return f"对不起，没有找到关于 '{query}' 的信息。"
    except Exception as e:
        return f"搜索时发生错误: {e}"


class ToolExecutor:
    """工具执行器，负责管理和执行工具"""

    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, description: str, func: Callable[[str], str]):
        if name in self.tools:
            self.tools[name] = {"description": description, "func": func}
        else:
            self.tools[name] = {"description": description, "func": func}

    def get_tool(self, name: str) -> Optional[Callable[[str], str]]:
        return self.tools.get(name, {}).get("func")

    def get_available_tools(self) -> str:
        return "\n".join(
            [f"- {name}: {info['description']}" for name, info in self.tools.items()]
        )

    def run_tool(self, name: str, tool_input: str) -> str:
        tool_func = self.get_tool(name)
        if not tool_func:
            return f"错误：未找到名为 '{name}' 的工具。"
        try:
            return tool_func(tool_input)
        except Exception as e:
            return f"错误：工具执行失败 - {str(e)}"


def get_default_tool_executor() -> ToolExecutor:
    executor = ToolExecutor()
    executor.register_tool(
        "Calculator",
        "数学计算器，支持基础运算与常用函数",
        calculator,
    )
    executor.register_tool(
        "Search",
        "网页搜索引擎，用于查询时事或事实信息",
        search,
    )
    return executor
