from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    postgres_host: str = "127.0.0.1"
    postgres_db: str
    postgres_port: int
    postgres_password: SecretStr
    postgres_user: str

    model_config = SettingsConfigDict(
    env_file=BASE_DIR / ".env",
    env_file_encoding="utf-8",
    extra="ignore",
)
    
settings = Settings()

