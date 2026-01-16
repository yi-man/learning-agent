"""配置管理模块"""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # API 配置（通用配置，可用于各种模型提供者）
    api_key: str
    api_endpoint: str = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    model_name: str = "doubao-seed-1-6-lite-251015"  # 默认模型，可在 .env 中覆盖

    # OpenAI SDK 配置（可选，用于兼容 OpenAI API 格式的模型）
    # 如果配置，OpenAI SDK 将使用此 base_url；否则使用默认 OpenAI API
    base_url: Optional[str] = None

    # FastAPI 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# 全局配置实例
settings = Settings()
