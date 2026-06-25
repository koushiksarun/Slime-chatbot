from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Slime"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production-use-secrets-manager"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://chatbot:chatbot@localhost:5432/chatbot_db"
    DATABASE_URL_SYNC: str = "postgresql://chatbot:chatbot@localhost:5432/chatbot_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # Default LLM provider: "openai" or "gemini"
    DEFAULT_LLM_PROVIDER: str = "openai"

    # Vector DB
    VECTOR_DB_PROVIDER: str = "chroma"  # "chroma" or "pinecone"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    PINECONE_INDEX_NAME: str = "chatbot-index"

    # HuggingFace
    HF_TOKEN: str = ""
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-mpnet-base-v2"

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "txt", "md"]

    # RAG
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RETRIEVAL: int = 6
    SIMILARITY_THRESHOLD: float = 0.7

    # Memory
    CONVERSATION_WINDOW_SIZE: int = 20
    SUMMARIZE_AFTER_TURNS: int = 40

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 500

    # External APIs
    TAVILY_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Admin
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "change-in-production"

    # Monitoring
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
