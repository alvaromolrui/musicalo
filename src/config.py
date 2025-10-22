"""
Configuration management for Music Assistant.
Centralized configuration using Pydantic Settings.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Telegram Configuration
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_allowed_users: str = Field(..., env="TELEGRAM_ALLOWED_USERS")
    
    # Navidrome Configuration
    navidrome_url: str = Field(..., env="NAVIDROME_URL")
    navidrome_username: str = Field(..., env="NAVIDROME_USERNAME")
    navidrome_password: str = Field(..., env="NAVIDROME_PASSWORD")
    
    # ListenBrainz Configuration
    listenbrainz_token: str = Field(..., env="LISTENBRAINZ_TOKEN")
    listenbrainz_username: str = Field(..., env="LISTENBRAINZ_USERNAME")
    
    # PostgreSQL Configuration
    postgres_host: str = Field("postgres", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    postgres_db: str = Field("music_assistant", env="POSTGRES_DB")
    postgres_user: str = Field("music_user", env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    
    # Ollama Configuration
    ollama_base_url: str = Field("http://ollama:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field("qwen2.5:3b", env="OLLAMA_MODEL")
    
    # Application Configuration
    sync_interval: int = Field(3600, env="SYNC_INTERVAL")  # seconds
    embedding_model: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # ChromaDB Configuration
    chroma_persist_directory: str = "/app/data/chroma"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def telegram_allowed_user_ids(self) -> List[int]:
        """Parse comma-separated user IDs into a list of integers."""
        if not self.telegram_allowed_users:
            return []
        try:
            return [int(uid.strip()) for uid in self.telegram_allowed_users.split(",") if uid.strip()]
        except ValueError:
            raise ValueError("Invalid TELEGRAM_ALLOWED_USERS format. Use comma-separated integers.")
    
    @property
    def database_url(self) -> str:
        """Generate PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def database_url_sync(self) -> str:
        """Generate synchronous PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get the database URL for SQLAlchemy."""
    return settings.database_url


def get_database_url_sync() -> str:
    """Get the synchronous database URL for SQLAlchemy."""
    return settings.database_url_sync


def is_user_allowed(user_id: int) -> bool:
    """Check if a user ID is in the allowed users list."""
    return user_id in settings.telegram_allowed_user_ids
