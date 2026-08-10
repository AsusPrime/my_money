from dotenv import find_dotenv
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_NAME: str = "my_money"

    ALLOWED_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=find_dotenv(filename=".env", usecwd=True),
        env_file_encoding="utf-8",
        extra="allow",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
        )

    @property
    def allowed_origins_list(self) -> list[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
