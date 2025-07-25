# config.py - Configuration management
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from dotenv import load_dotenv
from functools import lru_cache
import secrets

# Load .env explicitly
load_dotenv()


class Settings(BaseSettings):
    """Application settings with validation and backward compatibility"""

    # Database
    database_url: str = Field(default="sqlite:///./legal_ai.db", env="DATABASE_URL")
    redis_url: Optional[str] = Field(
        default="redis://localhost:6379/0", env="REDIS_URL"
    )

    # AI Service - Local Ollama
    ollama_base_url: str = Field(
        default="http://localhost:11434", env="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="llama3.2:1b", env="OLLAMA_MODEL")
    ai_provider: str = Field(default="ollama", env="AI_PROVIDER")

    # AI Service Settings
    enable_ai_fallback: bool = Field(default=True, env="ENABLE_AI_FALLBACK")
    ai_timeout_seconds: int = Field(default=300, env="AI_TIMEOUT_SECONDS")

    # File Storage
    upload_directory: str = Field(default="uploads", env="UPLOAD_DIRECTORY")
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY", min_length=32)
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY", min_length=32)
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    encryption_master_key: Optional[str] = Field(None, env="ENCRYPTION_MASTER_KEY")
    ENCRYPTION_KEY: str = Field(..., env="ENCRYPTION_KEY")
    disable_auth: bool = Field(
        default=True, env="DISABLE_AUTH"
    )  # Temporarily hardcoded to True

    # API Settings
    api_title: str = Field(default="Legal AI Assistant", env="API_TITLE")
    api_version: str = Field(default="1.0.0", env="API_VERSION")
    debug: bool = Field(default=False, env="DEBUG")

    # Email/Alerts
    email_enabled: bool = Field(default=False, env="EMAIL_ENABLED")
    alert_email_recipients: List[str] = Field(
        default_factory=list, env="ALERT_EMAIL_RECIPIENTS"
    )

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"], env="CORS_ORIGINS"
    )

    # Demo mode
    demo_mode: bool = Field(default=False, env="DEMO_MODE")

    # Allowed file extensions
    allowed_extensions: List[str] = Field(
        default=[".pdf", ".docx", ".txt"], env="ALLOWED_EXTENSIONS"
    )

    @field_validator("JWT_SECRET_KEY", "secret_key")
    def validate_secret_keys(cls, v):
        if len(v) < 32:
            raise ValueError("Secret keys must be at least 32 characters")
        return v

    @field_validator("ENCRYPTION_KEY")
    def validate_encryption_key(cls, v):
        try:
            from cryptography.fernet import Fernet

            # Validate it's a valid Fernet key
            if v and v != "generate-new-key":
                Fernet(v.encode() if isinstance(v, str) else v)
        except Exception:
            raise ValueError("Invalid Fernet encryption key")
        return v

    @field_validator("cors_origins", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Handle JSON string from env var
            import json

            try:
                return json.loads(v)
            except:
                # Fall back to comma-separated
                return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator(
        "disable_auth", "debug", "demo_mode", "email_enabled", mode="before"
    )
    def parse_bool(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    @field_validator("alert_email_recipients", mode="before")
    def parse_email_recipients(cls, v):
        if isinstance(v, str):
            return [email.strip() for email in v.split(",") if email.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True  # Respect exact case for backward compatibility
        extra = "ignore"  # Ignore extra fields from .env

    # Properties for backward compatibility
    @property
    def allowed_origins(self):
        return self.cors_origins


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create global settings instance
settings = get_settings()

# Debug print to verify settings loaded correctly
if settings.debug:
    print(f"🔧 Config loaded - AI Provider: {settings.ai_provider}")
    print(f"🔧 Config loaded - Ollama URL: {settings.ollama_base_url}")
    print(f"🔧 Config loaded - Auth disabled: {settings.disable_auth}")
