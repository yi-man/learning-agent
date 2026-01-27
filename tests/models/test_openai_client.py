"""OpenAIClient 测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_openai_client_init(mock_settings, monkeypatch):
    """测试客户端初始化"""
    monkeypatch.setattr("app.models.openai_client.settings", mock_settings)
    client = OpenAIClient()
    assert client.api_key == "test_api_key"
    assert client.model_name == "test-model"


@pytest.mark.asyncio
async def test_openai_client_chat_success(mock_settings, monkeypatch):
    """测试成功调用 chat"""
    monkeypatch.setattr("app.models.openai_client.settings", mock_settings)

    mock_choice = MagicMock()
    mock_choice.message.content = "AI response"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    client = OpenAIClient()
    with patch.object(
        client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await client.chat([{"role": "user", "content": "Hello"}])
        assert result == "AI response"
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_client_chat_stream(mock_settings, monkeypatch):
    """测试流式调用"""
    monkeypatch.setattr("app.models.openai_client.settings", mock_settings)

    client = OpenAIClient()

    # Mock stream chunks
    mock_chunk1 = MagicMock()
    mock_delta1 = MagicMock()
    mock_delta1.content = "Hello"
    mock_chunk1.choices = [MagicMock(delta=mock_delta1)]

    mock_chunk2 = MagicMock()
    mock_delta2 = MagicMock()
    mock_delta2.content = " World"
    mock_chunk2.choices = [MagicMock(delta=mock_delta2)]

    async def mock_stream():
        yield mock_chunk1
        yield mock_chunk2

    with patch.object(
        client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_stream()

        chunks = []
        async for chunk in client.chat_stream([{"role": "user", "content": "Hi"}]):
            chunks.append(chunk)

        assert chunks == ["Hello", " World"]


@pytest.mark.asyncio
async def test_openai_client_chat_error(mock_settings, monkeypatch):
    """测试 API 错误处理"""
    monkeypatch.setattr("app.models.openai_client.settings", mock_settings)

    client = OpenAIClient()
    with patch.object(
        client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = Exception("API Error")

        with pytest.raises(Exception) as exc_info:
            await client.chat([{"role": "user", "content": "Hello"}])
        assert "Error calling OpenAI API" in str(exc_info.value)
