from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/text-embedding-004"
    chroma_persist_dir: str = "./chroma_db"
    hr_policies_dir: str = "./data/hr_policies"
    retrieval_k: int = 4
    temperature: float = 0.2

settings = Settings()
