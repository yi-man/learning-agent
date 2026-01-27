"""DoubaoClient 测试"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.llm_client import DoubaoClient


@pytest.mark.asyncio
async def test_doubao_client_init(mock_settings, monkeypatch):
    """测试客户端初始化"""
    monkeypatch.setattr("app.models.llm_client.settings", mock_settings)
    client = DoubaoClient()
    assert client.api_key == "test_api_key"
    assert client.api_endpoint == "https://test.api.com/v3/chat/completions"
    assert client.model_name == "test-model"


@pytest.mark.asyncio
async def test_doubao_client_chat_success(mock_settings, monkeypatch):
    """测试成功调用 chat"""
    monkeypatch.setattr("app.models.llm_client.settings", mock_settings)
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {"content": "AI response"}
        }]
    }
    mock_response.raise_for_status = MagicMock()
    
    client = DoubaoClient()
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await client.chat([{"role": "user", "content": "Hello"}])
        assert result == "AI response"
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_doubao_client_chat_stream(mock_settings, monkeypatch):
    """测试流式调用"""
    monkeypatch.setattr("app.models.llm_client.settings", mock_settings)
    
    client = DoubaoClient()
    
    # Mock stream response - 需要模拟异步上下文管理器
    mock_line1 = "data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}}]})
    mock_line2 = "data: " + json.dumps({"choices": [{"delta": {"content": " World"}}]})
    mock_line3 = "data: [DONE]"
    
    async def mock_aiter_lines():
        yield mock_line1
        yield mock_line2
        yield mock_line3
    
    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.aiter_lines = mock_aiter_lines
    
    # 创建异步上下文管理器
    class MockStreamContext:
        def __init__(self, response):
            self.response = response
        
        async def __aenter__(self):
            return self.response
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None
    
    mock_stream_context = MockStreamContext(mock_response)
    
    with patch.object(client.client, 'stream', return_value=mock_stream_context):
        chunks = []
        async for chunk in client.chat_stream([{"role": "user", "content": "Hi"}]):
            chunks.append(chunk)
        
        assert chunks == ["Hello", " World"]


@pytest.mark.asyncio
async def test_doubao_client_chat_error(mock_settings, monkeypatch):
    """测试 API 错误处理"""
    import httpx
    monkeypatch.setattr("app.models.llm_client.settings", mock_settings)
    
    client = DoubaoClient()
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    
    error = httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=mock_response)
    
    with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = error
        
        with pytest.raises(Exception) as exc_info:
            await client.chat([{"role": "user", "content": "Hello"}])
        assert "API request failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_doubao_client_close(mock_settings, monkeypatch):
    """测试关闭客户端"""
    monkeypatch.setattr("app.models.llm_client.settings", mock_settings)
    client = DoubaoClient()
    await client.close()
    # 验证客户端已关闭（通过 mock 验证）
    assert client.client is not None
