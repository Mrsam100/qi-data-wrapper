from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql+psycopg://qi:qi@localhost:5433/qi_data_wrapper"
    storage_path: Path = Path("data")
    allowed_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_prefix="QI_DATA_", env_file=".env", extra="ignore")


settings = Settings()

