"""Chat OpenAI API 路由测试"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.api.chat_history import clear_history, generate_session_id


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAIClient"""
    mock_client = MagicMock()
    mock_client.model_name = "test-model"
    mock_client.chat = AsyncMock(return_value="AI response")
    mock_client.chat_stream = AsyncMock()

    async def stream_gen():
        yield "AI "
        yield "response"

    mock_client.chat_stream.return_value = stream_gen()
    return mock_client


def test_chat_openai_endpoint_success(client, mock_openai_client):
    """测试成功调用 chat_openai 端点"""
    import app.api.chat_openai as chat_openai_module

    original_client = chat_openai_module.openai_client
    chat_openai_module.openai_client = None

    try:
        with patch(
            "app.api.chat_openai.get_openai_client", return_value=mock_openai_client
        ):
            response = client.post(
                "/chat/openai",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "temperature": 0.7,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert "session_id" in data
            assert "model" in data
    finally:
        chat_openai_module.openai_client = original_client


def test_chat_openai_simple_endpoint(client, mock_openai_client):
    """测试简化版 chat_openai 端点"""
    import app.api.chat_openai as chat_openai_module

    original_client = chat_openai_module.openai_client
    chat_openai_module.openai_client = None

    try:
        with patch(
            "app.api.chat_openai.get_openai_client", return_value=mock_openai_client
        ):
            response = client.post("/chat/openai/simple?message=Hello")
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
    finally:
        chat_openai_module.openai_client = original_client
