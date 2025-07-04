from app.routers import (
    shopify_auth_router,
    shopify_data_router,
    shopify_webhooks_router,
    data_pull_router,
    ai_router,
    instant_preview_router
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from contextlib import asynccontextmanager

# Import the setup_logging function
from app.core.logging_config import setup_logging

# Import settings to ensure .env is loaded early
from app.core.config import settings
from app.core.cache import redis_client
from app.core.celery_app import celery_app

# Call setup_logging to configure logging as soon as the app starts
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    redis_client.ping()
    celery_app.control.ping()
    yield
    # Shutdown
    # Add any cleanup code here if needed

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Micro Segment project, integrating with Shopify.",
    version="0.1.0",
    # Define openapi url if using API_V1_STR
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Add SessionMiddleware - Make sure SESSION_SECRET_KEY is set in your .env file!
# This middleware enables session support, which is used by shopify_auth_router for OAuth state.
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

# Set all CORS enabled origins
if settings.SHOPIFY_APP_URL:  # TODO: Refine this for production
    origins = [
        str(settings.SHOPIFY_APP_URL),  # Your app's frontend URL
        "https://admin.shopify.com",  # For embedded apps
        "https://alien-adapted-gecko.ngrok-free.app",  # Your ngrok URL
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",  # Common local dev ports
        "http://127.0.0.1:5500",  # VS Code Live Server
        "http://localhost:5500",  # VS Code Live Server alternative
    ]
else:
    origins = ["*"]  # Fallback, less secure

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]  # Expose all headers
)

# Import routers

# Include routers with prefixes
app.include_router(
    shopify_auth_router.router, prefix="/api/auth/shopify", tags=["Shopify Auth"]
)
app.include_router(
    shopify_data_router.router, prefix="/api/data/shopify", tags=["Shopify Data"]
)

# Include the new webhook router
app.include_router(
    shopify_webhooks_router.router, prefix="/webhooks", tags=["Shopify Webhooks"]
)

# Add AI router
app.include_router(
    ai_router.router, prefix="/api/ai", tags=["AI Processing"]
)

# Add data pull router
app.include_router(data_pull_router.router)

# Add instant preview router
app.include_router(instant_preview_router.router)


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME}


@app.get("/debug-env")
async def debug_env():
    return {
        "app_url": settings.SHOPIFY_APP_URL,
        "redirect_uri": settings.SHOPIFY_REDIRECT_URI,
        # Only show first 5 chars for security
        "api_key": settings.SHOPIFY_API_KEY[::] + "...",
        "scopes": settings.SHOPIFY_APP_SCOPES
    }
