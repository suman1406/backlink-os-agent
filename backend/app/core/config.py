from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Autonomous Backlink Outreach"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017/outreach_platform"
    
    # Providers
    USE_MOCK_SEARCH: bool = False
    USE_MOCK_CRAWLER: bool = False
    
    # APIs
    GEMINI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    CEREBRAS_API_KEY: Optional[str] = None
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    TESTING_EMAIL_ADDRESS: Optional[str] = None
    
    # System behavior
    MAX_RETRIES: int = 3
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file="../../.env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
