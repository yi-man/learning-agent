"""pytest 配置和共享 fixtures"""

import pytest
from unittest.mock import AsyncMock
from app.config import Settings


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing"""
    settings = Settings(
        llm_api_key="test_api_key",
        llm_api_endpoint="https://test.api.com/v3/chat/completions",
        llm_model_id="test-model",
        llm_timeout=30,
        api_host="127.0.0.1",
        api_port=8000,
    )
    return settings


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient"""
    return AsyncMock()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI AsyncOpenAI client"""
    return AsyncMock()
