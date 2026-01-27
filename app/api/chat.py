"""对话 API 端点"""

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.chat_history import (
    add_message,
    clear_history,
    generate_session_id,
    merge_history_and_messages,
)
from app.models.llm_client import DoubaoClient

router = APIRouter(prefix="/chat", tags=["chat"])

# 全局 LLM 客户端实例
llm_client: Optional[DoubaoClient] = None


def get_llm_client() -> DoubaoClient:
    """获取 LLM 客户端实例（单例模式）"""
    global llm_client
    if llm_client is None:
        llm_client = DoubaoClient()
    return llm_client


class Message(BaseModel):
    """消息模型"""

    role: str = Field(..., description="消息角色：user, assistant, system")
    content: Union[str, List[Dict[str, Any]]] = Field(
        ..., description="消息内容，可以是字符串或多模态内容数组"
    )


class ChatRequest(BaseModel):
    """聊天请求模型"""

    messages: List[Message] = Field(..., description="消息列表")
    session_id: Optional[str] = Field(
        None, description="会话 ID，用于维护对话上下文。如果不提供，将创建新会话"
    )
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数，控制随机性")
    max_tokens: Optional[int] = Field(
        None,
        gt=0,
        description="最大生成 token 数（兼容参数，实际使用 max_completion_tokens）",
    )
    max_completion_tokens: Optional[int] = Field(
        None, gt=0, description="最大完成 token 数（火山引擎 API 参数）"
    )
    reasoning_effort: Optional[str] = Field(
        None, description="推理努力程度：low, medium, high"
    )
    stream: bool = Field(False, description="是否流式返回")
    clear_history: bool = Field(False, description="是否清除历史对话")


class ChatResponse(BaseModel):
    """聊天响应模型"""

    content: str = Field(..., description="AI 回复内容")
    model: str = Field(..., description="使用的模型名称")
    session_id: str = Field(..., description="会话 ID，用于后续对话")


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口（支持上下文）

    接收用户消息，调用 AI 模型生成回复。
    如果提供 session_id，将使用历史对话上下文。
    """
    try:
        client = get_llm_client()

        # 如果请求清除历史，先清除
        if request.clear_history and request.session_id:
            clear_history(request.session_id)

        # 生成或使用会话 ID
        session_id = request.session_id or generate_session_id()

        # 转换当前消息格式
        current_messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        # 合并历史消息和当前消息
        all_messages = merge_history_and_messages(session_id, current_messages)

        # 调用 LLM
        if request.stream:
            # 流式响应（这里简化处理，返回完整内容）
            # 实际应用中可以使用 StreamingResponse
            content = ""
            async for chunk in client.chat_stream(
                all_messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                max_completion_tokens=request.max_completion_tokens,
                reasoning_effort=request.reasoning_effort,
            ):
                content += chunk
        else:
            content = await client.chat(
                all_messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                max_completion_tokens=request.max_completion_tokens,
                reasoning_effort=request.reasoning_effort,
                stream=False,
            )

        # 保存对话历史
        # 保存用户消息
        for msg in current_messages:
            if msg["role"] == "user":
                add_message(session_id, "user", msg["content"])

        # 保存 AI 回复
        add_message(session_id, "assistant", content)

        return ChatResponse(
            content=content, model=client.model_name, session_id=session_id
        )

    except Exception as e:
        import traceback

        error_detail = str(e) if str(e) else repr(e)
        # 在开发环境中，可以打印完整的错误堆栈
        print(f"Error in chat: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error generating response: {error_detail}"
        )


@router.post("/simple")
async def chat_simple(
    message: str = Query(..., description="用户消息"),
    session_id: Optional[str] = Query(
        None, description="会话 ID，用于维护对话上下文。首次请求可不提供，将自动创建"
    ),
):
    """
    简化版对话接口（支持上下文）

    直接接收字符串消息，返回 AI 回复。
    支持通过 session_id 维护对话上下文。
    """
    try:
        client = get_llm_client()

        # 生成或使用会话 ID
        session_id = session_id or generate_session_id()

        # 合并历史消息和当前消息
        current_messages = [{"role": "user", "content": message}]
        all_messages = merge_history_and_messages(session_id, current_messages)

        # 调试：打印消息格式（开发环境）
        print(f"DEBUG: Session ID: {session_id}")
        print(f"DEBUG: Total messages count: {len(all_messages)}")
        # 只打印前2条
        print(
            f"DEBUG: Messages format: {all_messages[:2] if len(all_messages) > 0 else 'empty'}"
        )

        # 调用 LLM
        content = await client.chat(all_messages)

        # 保存对话历史
        add_message(session_id, "user", message)
        add_message(session_id, "assistant", content)

        return {
            "message": content,
            "model": client.model_name,
            "session_id": session_id,
        }

    except Exception as e:
        import traceback

        error_detail = str(e) if str(e) else repr(e)
        # 在开发环境中，可以打印完整的错误堆栈
        print(f"Error in chat_simple: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Error generating response: {error_detail}"
        )


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """
    清除指定会话的对话历史
    """
    clear_history(session_id)
    return {"message": f"History cleared for session {session_id}"}
