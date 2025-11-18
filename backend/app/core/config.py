import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AIKcal v3.0"
    API_V1_STR: str = "/api/v1"
    
    # Konfiguracja bezpieczeństwa
    GOOGLE_API_KEY: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Baza wektorowa (ChromaDB)
    CHROMA_DB_DIR: str = "/app/chroma_db"

    # === TUTAJ BRAKOWAŁO TYCH PÓL ===
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # E-mail (opcjonalne, ale warto mieć przygotowane)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = ""

    # Konfiguracja wczytywania pliku .env
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True,
        extra="ignore"
    )

settings = Settings()