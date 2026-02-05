"""ReAct JSON Agent API 端点"""

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.chat_history import (
    add_message,
    clear_history,
    generate_session_id,
    merge_history_and_messages,
)
from app.agents.react_agent import ReActJSONAgent
from app.models.openai_client import OpenAIClient

router = APIRouter(prefix="/agents", tags=["agents-react"])

# 全局 OpenAI 客户端实例
openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """获取 OpenAI 客户端实例（单例模式）"""
    global openai_client
    if openai_client is None:
        openai_client = OpenAIClient()
    return openai_client


def _content_to_text(content: Union[str, List[Dict[str, Any]]]) -> str:
    if isinstance(content, str):
        return content
    return str(content)


class Message(BaseModel):
    """消息模型"""

    role: str = Field(..., description="消息角色：user, assistant, system")
    content: Union[str, List[Dict[str, Any]]] = Field(
        ..., description="消息内容，可以是字符串或多模态内容数组"
    )


class ReactRequest(BaseModel):
    """ReAct 请求模型"""

    messages: List[Message] = Field(..., description="消息列表")
    session_id: Optional[str] = Field(
        None, description="会话 ID，用于维护对话上下文。如果不提供，将创建新会话"
    )
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数，控制随机性")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大生成 token 数")
    max_completion_tokens: Optional[int] = Field(
        None, gt=0, description="最大完成 token 数（兼容参数）"
    )
    reasoning_effort: Optional[str] = Field(
        None, description="推理努力程度：low, medium, high"
    )
    max_steps: int = Field(5, gt=0, description="ReAct 最大步数")
    return_trace: bool = Field(False, description="是否返回 trace")
    clear_history: bool = Field(False, description="是否清除历史对话")


class ReactResponse(BaseModel):
    """ReAct 响应模型"""

    content: str = Field(..., description="最终答案")
    model: str = Field(..., description="使用的模型名称")
    session_id: str = Field(..., description="会话 ID，用于后续对话")
    trace: Optional[List[Dict[str, Any]]] = Field(None, description="可选 trace")


@router.post("/react", response_model=ReactResponse, response_model_exclude_none=True)
async def agents_react(request: ReactRequest):
    """ReAct JSON 端点"""
    try:
        client = get_openai_client()

        if request.clear_history and request.session_id:
            clear_history(request.session_id)

        session_id = request.session_id or generate_session_id()
        current_messages = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        all_messages = merge_history_and_messages(session_id, current_messages)
        history_text = "\n".join(
            [
                f"{msg['role']}: {_content_to_text(msg['content'])}"
                for msg in all_messages
            ]
        )
        question = next(
            (
                _content_to_text(msg["content"])
                for msg in reversed(current_messages)
                if msg["role"] == "user"
            ),
            "",
        )

        agent = ReActJSONAgent(
            llm_client=client,
            max_steps=request.max_steps,
        )
        result = await agent.run(
            question=question,
            history_text=history_text,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_completion_tokens=request.max_completion_tokens,
            reasoning_effort=request.reasoning_effort,
        )

        for msg in current_messages:
            if msg["role"] == "user":
                add_message(session_id, "user", msg["content"])
        add_message(session_id, "assistant", result["content"])

        return ReactResponse(
            content=result["content"],
            model=client.model_name,
            session_id=session_id,
            trace=result["trace"] if request.return_trace else None,
        )
    except Exception as e:
        error_detail = str(e) if str(e) else repr(e)
        raise HTTPException(
            status_code=500, detail=f"Error generating response: {error_detail}"
        )
