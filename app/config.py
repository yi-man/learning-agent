"""配置管理模块"""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # 火山引擎 API 配置
    doubao_api_key: str
    doubao_api_endpoint: str = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    doubao_model_name: str = "doubao-seed-1-6-lite-251015"  # 默认模型，可在 .env 中覆盖

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
