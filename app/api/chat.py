"""对话 API 端点"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
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
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: List[Message] = Field(..., description="消息列表")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数，控制随机性")
    max_tokens: Optional[int] = Field(None, gt=0, description="最大生成 token 数")
    stream: bool = Field(False, description="是否流式返回")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str = Field(..., description="AI 回复内容")
    model: str = Field(..., description="使用的模型名称")


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口
    
    接收用户消息，调用 AI 模型生成回复
    """
    try:
        client = get_llm_client()
        
        # 转换消息格式
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # 调用 LLM
        if request.stream:
            # 流式响应（这里简化处理，返回完整内容）
            # 实际应用中可以使用 StreamingResponse
            content = ""
            async for chunk in client.chat_stream(
                messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ):
                content += chunk
        else:
            content = await client.chat(
                messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=False
            )
        
        return ChatResponse(
            content=content,
            model=client.model_name
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )


@router.post("/simple")
async def chat_simple(message: str = Query(..., description="用户消息")):
    """
    简化版对话接口
    
    直接接收字符串消息，返回 AI 回复
    """
    try:
        client = get_llm_client()
        
        messages = [{"role": "user", "content": message}]
        content = await client.chat(messages)
        
        return {
            "message": content,
            "model": client.model_name
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )
