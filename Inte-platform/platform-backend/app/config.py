from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://openpoint:openpoint123@postgres:5432/openpoint")
    jwt_secret: str = os.getenv("JWT_SECRET", "openpoint-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    class Config:
        env_file = ".env"

settings = Settings()
