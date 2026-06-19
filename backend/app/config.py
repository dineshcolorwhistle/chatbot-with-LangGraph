"""
Application configuration loaded from environment variables.
Uses Pydantic Settings for type-safe configuration management.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    Central configuration class for the entire application.
    All values are loaded from the .env file or environment variables.
    """

    # ── MongoDB ──────────────────────────────────────────────
    MONGODB_URI: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URI")
    MONGODB_DB_NAME: str = Field(default="chatbot_langgraph", description="MongoDB database name")

    # ── Pinecone ─────────────────────────────────────────────
    PINECONE_API_KEY: str = Field(default="", description="Pinecone API key")
    PINECONE_INDEX_NAME: str = Field(default="chatbot-index", description="Pinecone index name")

    # ── LLM Provider ─────────────────────────────────────────
    LLM_PROVIDER: str = Field(default="ollama", description="LLM provider: 'openai' or 'ollama'")
    LLM_MODEL: str = Field(default="llama3.1", description="LLM model name")
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama server base URL")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")

    # ── Embeddings ───────────────────────────────────────────
    EMBEDDING_MODEL: str = Field(default="nomic-embed-text", description="Ollama embedding model name")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", description="OpenAI embedding model name")

    # ── SMTP Email ───────────────────────────────────────────
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    SMTP_USER: str = Field(default="", description="SMTP username/email")
    SMTP_PASSWORD: str = Field(default="", description="SMTP password or app password")
    SMTP_FROM_EMAIL: str = Field(default="", description="Sender email address")

    # ── Admin Seeding ────────────────────────────────────────
    ADMIN_EMAIL: str = Field(default="admin@example.com", description="Default admin email for seeding")
    ADMIN_PASSWORD: str = Field(default="admin123", description="Default admin password for seeding")

    # ── JWT Authentication ───────────────────────────────────
    JWT_SECRET_KEY: str = Field(default="your-secret-key-change-this", description="JWT signing secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_EXPIRY_HOURS: int = Field(default=24, description="JWT token expiry in hours")

    # ── Chatbot Settings ─────────────────────────────────────
    MAX_USER_MESSAGES: int = Field(default=5, description="Maximum user messages per session before limit warning")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


# Singleton settings instance used across the application
settings = Settings()
