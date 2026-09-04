from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # API Keys - Should be provided via environment variables (e.g. GEMINI_API_KEYS='["key1", "key2"]')
    GEMINI_API_KEYS: list[str] = []
    
    # App Config
    APP_NAME: str = "StockSense AI Engine"
    DEBUG: bool = False
    
    # Model Config
    GEMINI_MODEL: str = "gemini-3.6-flash"
    
    # This allows loading from a .env file locally
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
