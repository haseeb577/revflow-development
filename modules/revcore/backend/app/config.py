from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "RevCore API"
    app_version: str = "1.0.0"
    database_url: str = "postgresql://revcore_user:revcore_secure_2026@localhost:5432/revcore"
    redis_url: str = "redis://localhost:6379/0"
    api_host: str = "0.0.0.0"
    api_port: int = 8004
    debug: bool = False
    
    class Config:
        env_file = "/opt/shared-api-engine/.env"
        env_prefix = "REVCORE_"
        extra = "ignore"  # This fixes the error!

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
