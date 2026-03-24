import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "nexabank")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "lutfor123")

    @classmethod
    def get_db_url(cls) -> str:
        return (
            f"postgresql+psycopg2://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )

    OLLAMA_BASE_URL: str  = os.getenv("OLLAMA_BASE_URL",  "http://localhost:11434")
    OLLAMA_CHAT_MODEL: str  = os.getenv("OLLAMA_CHAT_MODEL",  "gemma3:1b")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    SECRET_KEY: str         = os.getenv("SECRET_KEY",         "nexabank-secret-key")
    PIN_MAX_ATTEMPTS: int   = int(os.getenv("PIN_MAX_ATTEMPTS",   3))
    PIN_LOCKOUT_MINUTES: int = int(os.getenv("PIN_LOCKOUT_MINUTES", 15))
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", 30))
    CHUNK_SIZE: int         = int(os.getenv("CHUNK_SIZE",  512))
    CHUNK_OVERLAP: int      = int(os.getenv("CHUNK_OVERLAP", 64))
    VECTOR_TOP_K: int       = int(os.getenv("VECTOR_TOP_K",   5))
    UPLOAD_DIR: str         = os.getenv("UPLOAD_DIR",  "./uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", 10))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str  = os.getenv("LOG_FILE",  "./logs/nexabank.log")

config = Config()
