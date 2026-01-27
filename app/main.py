"""FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, chat_openai
from app.config import settings

# 创建 FastAPI 应用
app = FastAPI(
    title="AI Agent Learning",
    description="基于 FastAPI 的 AI Agent 学习项目，集成火山引擎豆包模型",
    version="1.0.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(chat_openai.router)


@app.get("/")
async def root():
    """根路径"""
    return {"message": "AI Agent Learning API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host=settings.api_host, port=settings.api_port, reload=True
    )
