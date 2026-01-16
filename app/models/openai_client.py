"""OpenAI SDK 客户端"""
from typing import Any, AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.models.llm_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """使用 OpenAI SDK 的客户端，兼容所有 OpenAI API 格式的大模型"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        初始化 OpenAI 客户端

        Args:
            api_key: API 密钥，默认从配置读取
            base_url: API 基础 URL，默认从配置读取。如果未配置，将使用 OpenAI 官方 API
            model_name: 模型名称，默认从配置读取
        """
        self.api_key = api_key or settings.api_key
        self.base_url = base_url or settings.base_url
        self.model_name = model_name or settings.model_name

        # 初始化 OpenAI 客户端
        client_kwargs = {
            "api_key": self.api_key,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncOpenAI(**client_kwargs)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """发送聊天请求（非流式）"""
        if stream:
            # 如果要求流式，但调用的是非流式方法，则收集流式结果
            full_response = ""
            async for chunk in self.chat_stream(messages, temperature, max_tokens, max_completion_tokens, reasoning_effort):
                full_response += chunk
            return full_response

        # 构建请求参数
        request_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }

        # OpenAI API 使用 max_tokens，但某些兼容 API 可能使用 max_completion_tokens
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        elif max_completion_tokens:
            request_params["max_tokens"] = max_completion_tokens

        # reasoning_effort 是某些模型特有的参数
        if reasoning_effort:
            request_params["reasoning_effort"] = reasoning_effort

        try:
            response = await self.client.chat.completions.create(**request_params)

            # 解析响应
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content or ""
            else:
                raise ValueError(f"Unexpected response format: {response}")

        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            raise Exception(f"Error calling OpenAI API: {error_msg}")

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None
    ) -> AsyncIterator[str]:
        """流式发送聊天请求"""
        # 构建请求参数
        request_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        # OpenAI API 使用 max_tokens，但某些兼容 API 可能使用 max_completion_tokens
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        elif max_completion_tokens:
            request_params["max_tokens"] = max_completion_tokens

        # reasoning_effort 是某些模型特有的参数
        if reasoning_effort:
            request_params["reasoning_effort"] = reasoning_effort

        try:
            stream = await self.client.chat.completions.create(**request_params)

            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        yield delta.content

        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            raise Exception(f"Error calling OpenAI API (stream): {error_msg}")

    async def close(self):
        """关闭客户端连接"""
        # AsyncOpenAI 客户端会自动管理连接，无需手动关闭
        pass

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
