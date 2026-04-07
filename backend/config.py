"""
Waya Bot Builder - Configuration Module
Centralized configuration management with validation
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Telegram Configuration
    telegram_bot_token: str = Field(
        ...,
        alias="TELEGRAM_BOT_TOKEN",
        description="Telegram Bot API token from @BotFather"
    )
    
    # Groq AI Configuration
    groq_api_key: str = Field(
        ...,
        alias="GROQ_API_KEY",
        description="Groq API key for AI features"
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model to use"
    )
    groq_max_tokens: int = Field(
        default=2048,
        description="Maximum tokens for AI responses"
    )
    
    # ElevenLabs Voice AI Configuration
    elevenlabs_api_key: Optional[str] = Field(
        default=None,
        alias="ELEVENLABS_API_KEY",
        description="ElevenLabs API key for text-to-speech"
    )
    elevenlabs_default_voice: str = Field(
        default="Rachel",
        description="Default ElevenLabs voice"
    )
    elevenlabs_model: str = Field(
        default="eleven_multilingual_v2",
        description="ElevenLabs model to use"
    )
    
    # Hume AI Emotion Configuration
    hume_api_key: Optional[str] = Field(
        default=None,
        alias="HUME_API_KEY",
        description="Hume AI API key for emotion detection"
    )
    
    # Database Configuration
    database_url: str = Field(
        ...,
        alias="DATABASE_URL",
        description="PostgreSQL connection URL"
    )
    db_pool_min_size: int = Field(default=5, description="Minimum DB pool size")
    db_pool_max_size: int = Field(default=20, description="Maximum DB pool size")
    
    # Bot Configuration
    bot_name: str = Field(default="Waya", description="Bot display name")
    bot_username: Optional[str] = Field(default=None, description="Bot username")
    max_conversation_history: int = Field(
        default=20,
        description="Max messages to keep in conversation context"
    )
    
    # Feature Flags
    enable_reminders: bool = Field(default=True)
    enable_notes: bool = Field(default=True)
    enable_tasks: bool = Field(default=True)
    enable_polls: bool = Field(default=True)
    enable_ai_suggestions: bool = Field(default=True)
    enable_custom_bots: bool = Field(default=True)
    enable_analytics: bool = Field(default=True)
    enable_voice_ai: bool = Field(default=True, description="Enable ElevenLabs voice features")
    enable_emotion_ai: bool = Field(default=True, description="Enable Hume AI emotion features")
    
    # Rate Limiting
    rate_limit_messages: int = Field(default=30, description="Messages per minute")
    rate_limit_ai_requests: int = Field(default=20, description="AI requests per minute")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
