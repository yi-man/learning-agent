"""Chat API 路由测试"""
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
def mock_doubao_client():
    """Mock DoubaoClient"""
    mock_client = MagicMock()
    mock_client.model_name = "test-model"
    mock_client.chat = AsyncMock(return_value="AI response")
    mock_client.chat_stream = AsyncMock()
    async def stream_gen():
        yield "AI "
        yield "response"
    mock_client.chat_stream.return_value = stream_gen()
    return mock_client


def test_chat_endpoint_success(client, mock_doubao_client):
    """测试成功调用 chat 端点"""
    # 需要重置全局客户端，确保使用 mock
    import app.api.chat as chat_module
    original_client = chat_module.llm_client
    chat_module.llm_client = None
    
    try:
        with patch("app.api.chat.get_llm_client", return_value=mock_doubao_client):
            response = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}],
                    "temperature": 0.7
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert "session_id" in data
            assert "model" in data
            assert data["content"] == "AI response"
    finally:
        chat_module.llm_client = original_client


def test_chat_endpoint_with_session_id(client, mock_doubao_client):
    """测试使用 session_id 的对话"""
    import app.api.chat as chat_module
    original_client = chat_module.llm_client
    chat_module.llm_client = None
    
    try:
        session_id = generate_session_id()
        clear_history(session_id)
        
        with patch("app.api.chat.get_llm_client", return_value=mock_doubao_client):
            # 第一条消息
            response1 = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "First"}],
                    "session_id": session_id
                }
            )
            assert response1.status_code == 200
            
            # 第二条消息（应该包含历史）
            response2 = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Second"}],
                    "session_id": session_id
                }
            )
            assert response2.status_code == 200
    finally:
        chat_module.llm_client = original_client


def test_chat_simple_endpoint(client, mock_doubao_client):
    """测试简化版 chat 端点"""
    import app.api.chat as chat_module
    original_client = chat_module.llm_client
    chat_module.llm_client = None
    
    try:
        with patch("app.api.chat.get_llm_client", return_value=mock_doubao_client):
            response = client.post(
                "/chat/simple?message=Hello"
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"] == "AI response"
    finally:
        chat_module.llm_client = original_client


def test_clear_history_endpoint(client):
    """测试清除历史端点"""
    session_id = generate_session_id()
    response = client.delete(f"/chat/history/{session_id}")
    assert response.status_code == 200
    assert "cleared" in response.json()["message"].lower()


def test_chat_endpoint_error(client):
    """测试 API 错误处理"""
    import app.api.chat as chat_module
    original_client = chat_module.llm_client
    chat_module.llm_client = None
    
    try:
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(side_effect=Exception("API Error"))
        
        with patch("app.api.chat.get_llm_client", return_value=mock_client):
            response = client.post(
                "/chat",
                json={
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
            assert response.status_code == 500
            assert "Error generating response" in response.json()["detail"]
    finally:
        chat_module.llm_client = original_client
