"""LLM 客户端抽象层"""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import httpx

from app.config import settings


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成 token 数
            stream: 是否流式返回

        Returns:
            AI 回复内容
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        流式发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Yields:
            AI 回复的文本片段
        """
        pass


class DoubaoClient(BaseLLMClient):
    """火山引擎豆包模型客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        初始化豆包客户端

        Args:
            api_key: API 密钥，默认从配置读取
            api_endpoint: API 端点，默认从配置读取
            model_name: 模型名称，默认从配置读取
        """
        self.api_key = api_key or settings.api_key
        self.api_endpoint = api_endpoint or settings.api_endpoint
        self.model_name = model_name or settings.model_name
        self.client = httpx.AsyncClient(timeout=60.0)

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

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }

        # 火山引擎 API 使用 max_completion_tokens 而不是 max_tokens
        if max_completion_tokens:
            payload["max_completion_tokens"] = max_completion_tokens
        elif max_tokens:
            payload["max_completion_tokens"] = max_tokens

        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = await self.client.post(
                self.api_endpoint,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()

            # 解析响应
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unexpected response format: {result}")

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"API request failed with status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise Exception(f"Error calling Doubao API: {str(e)}")

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        reasoning_effort: Optional[str] = None
    ) -> AsyncIterator[str]:
        """流式发送聊天请求"""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        # 火山引擎 API 使用 max_completion_tokens 而不是 max_tokens
        if max_completion_tokens:
            payload["max_completion_tokens"] = max_completion_tokens
        elif max_tokens:
            payload["max_completion_tokens"] = max_tokens

        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with self.client.stream(
                "POST",
                self.api_endpoint,
                json=payload,
                headers=headers
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # 处理 SSE 格式
                    if line.startswith("data: "):
                        data_str = line[6:]  # 移除 "data: " 前缀
                        if data_str == "[DONE]":
                            break

                        try:
                            import json
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_json = e.response.json()
                if "error" in error_json:
                    error_detail = f" - {error_json['error']}"
            except:
                error_detail = f" - {e.response.text[:200]}"
            raise Exception(
                f"API request failed with status {e.response.status_code}{error_detail}")
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            raise Exception(f"Error calling Doubao API (stream): {error_msg}")

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
