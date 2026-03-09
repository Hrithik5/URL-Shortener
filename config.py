"""
config.py
Centralised configuration using pydantic-settings.
All values can be overridden via environment variables or a .env file.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./urls.db"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # ZooKeeper
    zk_hosts: str = "127.0.0.1:2181"

    # Application
    base_url: str = "http://localhost:8000"
    default_expiry_hours: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
