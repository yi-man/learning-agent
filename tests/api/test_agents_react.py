"""Agents ReAct API 路由测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAIClient"""
    mock_client = MagicMock()
    mock_client.model_name = "test-model"
    mock_client.chat = AsyncMock(
        return_value='{"thought":"done","action":{"type":"finish","input":"ok"}}'
    )
    return mock_client


def test_agents_react_generates_session_id(client, mock_openai_client):
    """未提供 session_id 时自动生成"""
    import app.api.agents_react as agents_react_module

    original_client = agents_react_module.openai_client
    agents_react_module.openai_client = None

    try:
        with patch(
            "app.api.agents_react.get_openai_client", return_value=mock_openai_client
        ):
            response = client.post(
                "/agents/react",
                json={"messages": [{"role": "user", "content": "2+2?"}]},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"]
            assert data["content"]
            assert "trace" not in data
    finally:
        agents_react_module.openai_client = original_client


def test_agents_react_returns_trace_when_enabled(client, mock_openai_client):
    """return_trace=true 时返回 trace"""
    import app.api.agents_react as agents_react_module

    original_client = agents_react_module.openai_client
    agents_react_module.openai_client = None

    try:
        with patch(
            "app.api.agents_react.get_openai_client", return_value=mock_openai_client
        ):
            response = client.post(
                "/agents/react",
                json={
                    "messages": [{"role": "user", "content": "2+2?"}],
                    "return_trace": True,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "trace" in data
            assert isinstance(data["trace"], list)
            assert data["trace"]
    finally:
        agents_react_module.openai_client = original_client


def test_agents_react_tool_call_calculator(client, mock_openai_client):
    """工具调用路径（Calculator）"""
    import app.api.agents_react as agents_react_module

    tool_call = '{"thought":"calc","action":{"type":"tool_call","tool_name":"Calculator","input":"2+2"}}'
    finish = '{"thought":"done","action":{"type":"finish","input":"4"}}'
    mock_openai_client.chat = AsyncMock(side_effect=[tool_call, finish])

    original_client = agents_react_module.openai_client
    agents_react_module.openai_client = None

    try:
        with patch(
            "app.api.agents_react.get_openai_client", return_value=mock_openai_client
        ):
            response = client.post(
                "/agents/react",
                json={
                    "messages": [{"role": "user", "content": "2+2?"}],
                    "return_trace": True,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "4"
            assert any(step.get("observation") == "4" for step in data.get("trace", []))
    finally:
        agents_react_module.openai_client = original_client


def test_agents_react_uses_history(client, mock_openai_client):
    """同 session_id 时会合并历史"""
    import app.api.agents_react as agents_react_module

    original_client = agents_react_module.openai_client
    agents_react_module.openai_client = None

    try:
        with patch(
            "app.api.agents_react.get_openai_client", return_value=mock_openai_client
        ):
            first = client.post(
                "/agents/react",
                json={"messages": [{"role": "user", "content": "first"}]},
            ).json()
            session_id = first["session_id"]

            client.post(
                "/agents/react",
                json={
                    "session_id": session_id,
                    "messages": [{"role": "user", "content": "second"}],
                },
            )

            last_call_messages = mock_openai_client.chat.call_args_list[-1][0][0]
            prompt_text = last_call_messages[-1]["content"]
            assert "first" in prompt_text
            assert "second" in prompt_text
    finally:
        agents_react_module.openai_client = original_client
