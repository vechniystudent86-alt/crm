"""
Конфигурация приложения Zumba CRM
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    
    # Приложение
    APP_NAME: str = "Zumba CRM"
    DEBUG: bool = True
    
    # База данных
    DATABASE_URL: str = "sqlite+aiosqlite:///./crm.db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "your-jwt-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 часа
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    
    # Админ по умолчанию
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Кэшированный экземпляр настроек"""
    return Settings()


settings = get_settings()
