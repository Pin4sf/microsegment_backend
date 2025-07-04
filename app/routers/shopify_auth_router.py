import httpx  # Ensure httpx is imported if used for exceptions, though not directly in this snippet
import secrets
import certifi
from fastapi import APIRouter, Request, HTTPException, Query, Depends, status, Body
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
import logging
import hmac
import hashlib
from typing import Dict, Optional
from app.services.shopify_service import ShopifyClient

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select  # Required for select statement

# from app.services.shopify_service import ShopifyClient # ShopifyClient no longer used in this router
from app.core.config import settings
from app.utils.shopify_utils import generate_shopify_auth_url, verify_hmac
from app.db.session import get_db
from app.models.shop_model import Shop
from app.models.extension_model import Extension
from app.schemas.shopify_schemas import (
    ShopifyActivateExtensionRequest,
    ShopifyActivateExtensionResponse,
)
import json

logger = logging.getLogger(__name__)
router = APIRouter()

# Removed temporary in-memory storages as they are replaced by session and DB
# INSTALL_STATES: Dict[str, str] = {}
# ACTIVE_INSTALLS: Dict[str, str] = {}
# temp_state_storage = {} # This was the one explicitly identified for removal


@router.get("/connect", summary="Initiate Shopify OAuth Flow")
async def connect_to_shopify(shop: str, request: Request):
    """
    Redirects the user to the Shopify authorization URL.
    This is the first step in the OAuth process.
    """
    if not shop:
        raise HTTPException(status_code=400, detail="Shop domain is required.")

    state = secrets.token_hex(16)
    # INSTALL_STATES[state] = shop  # Store state with shop for verification later
    # For now, we will store the state in the session cookie itself as a temporary measure.
    # In a real app, you might use a server-side session store or a short-lived DB entry.
    request.session["shopify_oauth_state"] = state
    request.session["shopify_oauth_shop"] = shop

    redirect_url = generate_shopify_auth_url(
        shop_domain=shop,
        api_key=settings.SHOPIFY_API_KEY,
        scopes=settings.SHOPIFY_APP_SCOPES,
        redirect_uri=settings.SHOPIFY_REDIRECT_URI,
        state=state,
    )
    return RedirectResponse(redirect_url)


@router.get("/callback", summary="Handle Shopify OAuth Callback")
async def shopify_callback(
    request: Request,
    shop: str,
    code: str,
    state: str,
    hmac_shopify: Optional[str] = Query(
        None, alias="hmac"
    ),  # HMAC is provided by Shopify
    timestamp: Optional[str] = Query(None),  # Timestamp is also provided
    db: AsyncSession = Depends(get_db),
):
    """
    Handles the callback from Shopify after the user authorizes the app.
    Verifies HMAC, exchanges the authorization code for an access token,
    and stores the token.
    """
    # 1. Verify HMAC (already have a utility for this, but it needs the raw query string)
    # We need to reconstruct the query string from the request for exact HMAC verification
    # as query parameters might be reordered by FastAPI/Starlette.
    # The raw query string is available via request.scope['query_string'].decode()
    raw_query_string = request.scope["query_string"].decode()

    # Remove hmac from query string for validation
    # query_params_list = [f"{k}={v}" for k, v in request.query_params.items() if k != 'hmac']
    # verifiable_query_string = "&".join(sorted(query_params_list)) # Ensure consistent order

    # More robust way to get verifiable query string without hmac
    query_params = dict(request.query_params)
    # remove hmac and get its value
    hmac_to_verify = query_params.pop("hmac", None)
    # The Shopify documentation states the parameters should be sorted alphabetically by key
    verifiable_query_string = "&".join(
        [f"{k}={v}" for k, v in sorted(query_params.items())]
    )

    if not verify_hmac(
        verifiable_query_string, hmac_to_verify, settings.SHOPIFY_API_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="HMAC validation failed."
        )

    # 2. Verify State
    # stored_state = INSTALL_STATES.pop(state, None)
    # stored_shop_for_state = request.session.get('shopify_oauth_shop')
    # if not stored_state or stored_state != shop:
    #     raise HTTPException(status_code=403, detail="State validation failed. Possible CSRF attack.")
    # More robust state verification directly using session
    session_state = request.session.pop("shopify_oauth_state", None)
    session_shop = request.session.pop("shopify_oauth_shop", None)

    if not session_state or session_state != state or session_shop != shop:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OAuth state validation failed. Possible CSRF attack or session issue.",
        )

    # 3. Exchange authorization code for an access token
    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": settings.SHOPIFY_API_KEY,
        "client_secret": settings.SHOPIFY_API_SECRET,
        "code": code,
    }

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.post(token_url, json=payload)
            response.raise_for_status()  # Raises an exception for 4XX/5XX responses
            token_data = response.json()
        except httpx.HTTPStatusError as e:
            # Log the error details from Shopify
            # logger.error(f"Shopify token exchange failed for {shop}: {e.response.status_code} - {e.response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to exchange authorization code for access token. Shopify responded with: {e.response.text}",
            )
        except httpx.RequestError as e:
            # logger.error(f"Request error during Shopify token exchange for {shop}: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not connect to Shopify to exchange token: {str(e)}",
            )

    access_token = token_data.get("access_token")
    if not access_token:
        logger.error(
            f"Access token not found in Shopify response for {shop}: {token_data}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Access token not found in Shopify response.",
        )

    # --- TEMPORARY LOGGING FOR DEVELOPMENT/TESTING ---
    logger.warning(
        f"Successfully obtained RAW access token for shop {shop} (FOR TESTING PURPOSES): {access_token}"
    )
    # --- END TEMPORARY LOGGING ---

    # 4. Store the access token securely (e.g., in a database)
    # ACTIVE_INSTALLS[shop] = access_token # Replaced by DB storage

    # --- Database Interaction ---
    try:
        # Check if the shop already exists
        stmt = select(Shop).where(Shop.shop_domain == shop)
        result = await db.execute(stmt)
        db_shop = result.scalar_one_or_none()

        if db_shop:
            # Shop exists, update the access token
            db_shop.access_token = access_token
            # db_shop.is_installed = True # Assuming re-install means it's active
            # updated_at will be handled by the model if onupdate=func.now() is set
        else:
            # Shop does not exist, create a new entry
            db_shop = Shop(
                shop_domain=shop,
                access_token=access_token,
                # is_installed=True,
                # shopify_scopes=settings.SHOPIFY_APP_SCOPES # Good to store the scopes granted
            )
            db.add(db_shop)

        await db.commit()
        await db.refresh(db_shop)
        logger.info(
            f"Successfully processed and stored token for shop: {shop}")

    except Exception as e:
        await db.rollback()
        logger.exception(
            f"Database error during token storage for {shop}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save access token to the database: {str(e)}",
        )
    # --- End Database Interaction ---

    # TODO: After successful installation & token storage:
    # 1. Register mandatory webhooks (GDPR).
    # 2. Perform any other post-installation setup (e.g., initial data sync).

    # For now, redirect to a success page or the app's embedded interface
    # This redirect URL will likely be to your app's frontend, possibly within Shopify admin
    # The shop domain and host (if needed for App Bridge) could be passed as query params
    # A common pattern is to redirect to the app's main page within the Shopify admin.
    # The exact URL structure depends on how your frontend is set up and if it's an embedded app.
    # For example: f"{settings.SHOPIFY_APP_URL}?shop={shop}&host={request.query_params.get('host')}"
    # If SHOPIFY_APP_URL is the base URL of your frontend app.

    # Redirect to our temporary app home page
    app_home_url = f"/api/auth/shopify/app-home?shop={shop}"
    # For embedded apps, Shopify provides a 'host' param
    if request.query_params.get("host"):
        app_home_url += f"&host={request.query_params.get('host')}"

    return RedirectResponse(app_home_url)


# Example of how you might retrieve a token later (e.g., for an API call)
# async def get_shop_token(shop_domain: str, db: AsyncSession = Depends(get_db)):
#     stmt = select(Shop).where(Shop.shop_domain == shop_domain)
#     result = await db.execute(stmt)
#     shop = result.scalar_one_or_none()
#     if shop and shop.is_installed: # Check if app is currently installed/active
#         # Here you would decrypt the token if it was encrypted
#         return shop.access_token
#     return None

# TODO:
# - Consider encrypting access tokens in the database.
# - Add more robust error handling and logging.
# - Implement webhook registration for mandatory webhooks.
# - Ensure `SHOPIFY_APP_URL` in `.env` points to your app's main page/dashboard.


@router.post("/activate-extension", summary="Activates webpixel extension")
async def activate_webpixel_extension(
    request_data: ShopifyActivateExtensionRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Get shop from database
        shop_query = select(Shop).where(Shop.shop_domain == request_data.shop)
        result = await db.execute(shop_query)
        shop = result.scalar_one_or_none()

        if not shop:
            logger.error(f"Shop not found: {request_data.shop}")
            raise HTTPException(status_code=404, detail="Shop not found")

        # Check if extension already exists
        extension_query = select(Extension).where(Extension.shop_id == shop.id)
        result = await db.execute(extension_query)
        existing_extension = result.scalar_one_or_none()

        if existing_extension:
            # Update existing extension
            client = ShopifyClient(
                shop=request_data.shop, access_token=request_data.access_token
            )
            raw_response = await client.update_extension(existing_extension.shopify_extension_id)

            if raw_response and "data" in raw_response:
                data_content = raw_response["data"]["webPixelUpdate"]
                if len(data_content["userErrors"]) > 0:
                    logger.error(
                        f"Error updating extension: {data_content['userErrors'][0]['message']}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"An unexpected error occurred while updating webpixel extension.",
                    )

                # Update extension in database
                existing_extension.status = 'active'
                existing_extension.version = '1.0.0'  # Update version as needed
                await db.commit()

                return ShopifyActivateExtensionResponse(
                    success=True, webPixel=data_content["webPixel"]
                )
        else:
            # Create new extension
            client = ShopifyClient(
                shop=request_data.shop, access_token=request_data.access_token
            )
            raw_response = await client.activate_webpixel_extension()

            if raw_response and "data" in raw_response:
                data_content = raw_response["data"]["webPixelCreate"]
                if len(data_content["userErrors"]) > 0:
                    logger.error(
                        f"Error creating extension: {data_content['userErrors'][0]['message']}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"An unexpected error occurred while activating webpixel extension.",
                    )

                # Create extension in database
                try:
                    settings_data = json.loads(
                        data_content["webPixel"]["settings"])
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse webPixel settings: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to parse webPixel settings from Shopify response"
                    )
                extension = Extension(
                    shop_id=shop.id,
                    shopify_extension_id=data_content["webPixel"]["id"],
                    account_id=settings_data["accountID"],
                    status='active',
                    version='1.0.0'
                )

                db.add(extension)
                await db.commit()

                return ShopifyActivateExtensionResponse(
                    success=True, webPixel=data_content["webPixel"]
                )

    except Exception as e:
        logger.error(
            f"Unexpected error in activate extension method for shop {request_data.shop}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while activating extension.",
        )


@router.post("/update-extension", summary="Updates webpixel extension")
async def update_webpixel_extension(
    request_data: ShopifyActivateExtensionRequest = Body(...),
):
    try:
        client = ShopifyClient(
            shop=request_data.shop, access_token=request_data.access_token
        )
        raw_response = await client.update_extension(request_data.extension_id)
        if raw_response and "data" in raw_response:
            data_content = raw_response["data"]["webPixelUpdate"]
            if len(data_content["userErrors"]) > 0:
                print(data_content["userErrors"][0]["message"])
                raise HTTPException(
                    status_code=500,
                    detail=f"An unexpected error occurred while updating webpixel extension.",
                )

            return ShopifyActivateExtensionResponse(
                success=True, webPixel=data_content["webPixel"]
            )

    except Exception as e:
        logger.error(
            f"Unexpected error in update extension method for shop {request_data.shop}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while updating extension.",
        )


@router.get("/app-home", summary="Temporary App Home Page")
async def app_home(
    shop: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Temporary app home page that displays the shop's connection details.
    This will be replaced by a proper frontend in the future.
    """
    try:
        # Query the shop details from the database
        stmt = select(Shop).where(Shop.shop_domain == shop)
        result = await db.execute(stmt)
        shop_data = result.scalar_one_or_none()

        if not shop_data:
            raise HTTPException(
                status_code=404,
                detail=f"Shop {shop} not found in database"
            )

        # Create a response with the shop details
        response = {
            "status": "success",
            "message": "Shopify App Connection Details",
            "data": {
                "shop_domain": shop_data.shop_domain,
                # Note: In production, never expose raw tokens
                "access_token": shop_data.access_token,
                "is_installed": shop_data.is_installed,
                "shopify_scopes": shop_data.shopify_scopes,
                "created_at": shop_data.created_at.isoformat() if shop_data.created_at else None,
                "updated_at": shop_data.updated_at.isoformat() if shop_data.updated_at else None
            }
        }

        # Return HTML response for better readability
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Shopify App Home</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .header {{ background: #5c6ac4; color: white; padding: 20px; border-radius: 5px; }}
                .content {{ background: #f9fafb; padding: 20px; border-radius: 5px; margin-top: 20px; }}
                .detail {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #4a5568; }}
                .value {{ color: #2d3748; }}
                .warning {{ color: #e53e3e; font-style: italic; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Shopify App Connection Details</h1>
                </div>
                <div class="content">
                    <div class="detail">
                        <span class="label">Shop Domain:</span>
                        <span class="value">{shop_data.shop_domain}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Access Token:</span>
                        <span class="value">{shop_data.access_token}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Installation Status:</span>
                        <span class="value">{'Installed' if shop_data.is_installed else 'Not Installed'}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Shopify Scopes:</span>
                        <span class="value">{', '.join(shop_data.shopify_scopes) if shop_data.shopify_scopes else 'None'}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Created At:</span>
                        <span class="value">{shop_data.created_at.strftime('%Y-%m-%d %H:%M:%S') if shop_data.created_at else 'N/A'}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Last Updated:</span>
                        <span class="value">{shop_data.updated_at.strftime('%Y-%m-%d %H:%M:%S') if shop_data.updated_at else 'N/A'}</span>
                    </div>
                    <p class="warning">Note: This is a temporary page. In production, never expose access tokens in the UI.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(
            f"Error in app home page for shop {shop}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving shop details: {str(e)}"
        )
