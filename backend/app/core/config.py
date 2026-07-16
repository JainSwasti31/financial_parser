import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Financial Document Parser"
    API_V1_STR: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int
    
    # DATABASE_URL can be set in .env. Default to sqlite for easy local testing.
    DATABASE_URL: str = "sqlite:///./test.db"
    
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    FRONTEND_ORIGIN: str = "http://127.0.0.1:5173"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_BATCH_SIZE: int = 20
    DB_CONNECT_TIMEOUT_SECONDS: int = 10
    
    OCR_PROVIDER: str = "tesseract"
    AI_PROVIDER: str = "rule_based"
    GEMINI_API_KEY: Optional[str] = None
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
