from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Micro Segment Backend"
    API_V1_STR: str = "/api/"

    # Shopify API Credentials and Configuration
    SHOPIFY_API_KEY: str
    SHOPIFY_API_SECRET: str
    SHOPIFY_API_VERSION: str = "2025-04"
    SHOPIFY_APP_SCOPES: str = (
        "read_products,read_orders,read_customers,write_pixels,read_customer_events"
    )
    SHOPIFY_APP_URL: str
    SHOPIFY_REDIRECT_URI: str

    # For secure storage of credentials (e.g., a Fernet key for encrypting access tokens)
    # SECRET_KEY: str # For encrypting sensitive data, generate a strong key
    APP_SECRET_KEY: (
        str  # Used for general encryption purposes, like access tokens in DB
    )
    SESSION_SECRET_KEY: str  # Used specifically for signing session cookies

    # Database URL
    # Example, override in .env
    DATABASE_URL: str = (
        "postgresql+asyncpg://microsegment_user:1234@localhost:5432/microsegment_app_db"
    )

    #Redis and Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
