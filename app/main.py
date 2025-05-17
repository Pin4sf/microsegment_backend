from app.routers import shopify_auth_router, shopify_data_router, shopify_webhooks_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
# Import the setup_logging function
from app.core.logging_config import setup_logging
# Import settings to ensure .env is loaded early
from app.core.config import settings

# Call setup_logging to configure logging as soon as the app starts
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for Micro Segment project, integrating with Shopify.",
    version="0.1.0",
    # Define openapi url if using API_V1_STR
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Add SessionMiddleware - Make sure SESSION_SECRET_KEY is set in your .env file!
# This middleware enables session support, which is used by shopify_auth_router for OAuth state.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY
)

# Set all CORS enabled origins
if settings.SHOPIFY_APP_URL:  # TODO: Refine this for production
    origins = [
        str(settings.SHOPIFY_APP_URL),  # Your app's frontend URL
        "https://admin.shopify.com",  # For embedded apps
        # Add other origins if necessary, e.g., localhost for local dev frontend
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",  # Common local dev ports
    ]
else:
    origins = ["*"]  # Fallback, less secure

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers

# Include routers with prefixes
app.include_router(shopify_auth_router.router,
                   prefix="/api/auth/shopify", tags=["Shopify Auth"])
app.include_router(shopify_data_router.router,
                   prefix="/api/data/shopify", tags=["Shopify Data"])

# Include the new webhook router
app.include_router(shopify_webhooks_router.router,
                   prefix="/webhooks",
                   tags=["Shopify Webhooks"])


@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME}
