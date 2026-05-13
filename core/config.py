from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # AI
    GROQ_API_KEY: str = ""

    # Weather
    OPENWEATHER_API_KEY: str = ""

    # Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Supabase (legacy)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # MongoDB Atlas
    MONGODB_URI: str = ""
    MONGODB_DB_NAME: str = "kisansathi"

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"

    # JWT
    JWT_SECRET_KEY: str = "change_this_to_a_long_random_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Server
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
