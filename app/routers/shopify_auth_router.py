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
from app.schemas.shopify_schemas import (
    ShopifyActivateExtensionRequest,
    ShopifyActivateExtensionResponse,
    ExtensionStatusResponse,
)
from app.models.extension_model import Extension
import json # Added for parsing settings string
from app.services.webhook_service import register_all_required_webhooks # Added

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

    # --- Register Webhooks ---
    if db_shop and db_shop.access_token: # Ensure we have a shop and token
        logger.info(f"Attempting to register webhooks for shop: {db_shop.shop_domain}")
        shop_client = ShopifyClient(shop=db_shop.shop_domain, access_token=db_shop.access_token)
        # The webhook_base_url is settings.SHOPIFY_APP_URL
        # The callback path is /webhooks (as defined in main.py for shopify_webhooks_router)
        await register_all_required_webhooks(
            shop_client=shop_client,
            webhook_base_url=settings.SHOPIFY_APP_URL,
            db_shop=db_shop,
            db=db # Pass the existing db session
        )
        logger.info(f"Webhook registration process completed for shop: {db_shop.shop_domain}")
    else:
        logger.error(f"Skipping webhook registration for shop {shop} due to missing db_shop instance or access token.")
    # --- End Register Webhooks ---


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


@router.post(
    "/activate-extension",
    summary="Activates webpixel extension and tracks its status",
    response_model=ShopifyActivateExtensionResponse,
)
async def activate_webpixel_extension(
    request_payload: ShopifyActivateExtensionRequest = Body(...),
    db: AsyncSession = Depends(get_db),
):
    # Ensure accountID is provided in settings for activation
    if not request_payload.extension_settings or "accountID" not in request_payload.extension_settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="accountID is required in extension_settings to activate an extension.",
        )
    account_id_from_settings = request_payload.extension_settings["accountID"]

    try:
        client = ShopifyClient(
            shop=request_payload.shop, access_token=request_payload.access_token
        )
        # Pass settings to the client method, assuming it stringifies them as needed by GraphQL
        # and that the Shopify service returns the Shopify GID and the accountID from settings.
        # The client.activate_webpixel_extension now takes the settings dictionary
        raw_response = await client.activate_webpixel_extension(settings=request_payload.extension_settings)

        if not raw_response or "data" not in raw_response or not raw_response["data"].get("webPixelCreate"):
            logger.error(f"Invalid response from Shopify activate_webpixel_extension for shop {request_payload.shop}: {raw_response}")
            raise HTTPException(status_code=500, detail="Failed to activate extension: Invalid response from Shopify.")

        web_pixel_create_data = raw_response["data"]["webPixelCreate"]
        if web_pixel_create_data.get("userErrors"):
            user_errors = web_pixel_create_data["userErrors"]
            if user_errors: # Check if list is not empty
                error_message = user_errors[0].get("message", "Unknown error during web pixel creation.")
                logger.error(f"Shopify userErrors during webPixelCreate for {request_payload.shop}: {user_errors}")
                raise HTTPException(status_code=400, detail=f"Shopify error: {error_message}")

        shopify_web_pixel_info = web_pixel_create_data.get("webPixel")
        if not shopify_web_pixel_info or "id" not in shopify_web_pixel_info or "settings" not in shopify_web_pixel_info:
            logger.error(f"Missing webPixel id or settings in Shopify response for {request_payload.shop}: {shopify_web_pixel_info}")
            raise HTTPException(status_code=500, detail="Failed to activate extension: Incomplete web pixel data from Shopify.")

        shopify_gid = shopify_web_pixel_info["id"]
        try:
            shopify_settings_json = json.loads(shopify_web_pixel_info["settings"])
            account_id = shopify_settings_json.get("accountID")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse settings JSON from Shopify response for {request_payload.shop}: {shopify_web_pixel_info['settings']}")
            raise HTTPException(status_code=500, detail="Failed to activate extension: Could not parse settings from Shopify.")

        if not shopify_gid or not account_id:
            logger.error(f"Extracted shopify_gid or account_id is missing. GID: {shopify_gid}, AccountID: {account_id} for shop {request_payload.shop}")
            raise HTTPException(status_code=500, detail="Failed to activate extension: Missing Shopify GID or Account ID after processing response.")

        # Ensure the accountID from settings matches the one from the response if it's critical
        if account_id != account_id_from_settings:
            logger.warning(f"AccountID mismatch for shop {request_payload.shop}: settings '{account_id_from_settings}', response '{account_id}'. Using response's.")
            # Decide on handling: error out or use the one from response. For now, use response's.

        # Query for existing Shop
        shop_stmt = select(Shop).where(Shop.shop_domain == request_payload.shop)
        shop_result = await db.execute(shop_stmt)
        db_shop = shop_result.scalar_one_or_none()

        if not db_shop:
            raise HTTPException(status_code=404, detail=f"Shop {request_payload.shop} not found.")

        # Query for existing Extension
        ext_stmt = select(Extension).where(
            Extension.shop_id == db_shop.id,
            Extension.account_id == account_id # Use account_id from Shopify response
        )
        ext_result = await db.execute(ext_stmt)
        db_extension = ext_result.scalar_one_or_none()

        extension_version = "1.0.0" # Default or from request_payload.extension_settings

        if db_extension:
            db_extension.shopify_extension_id = shopify_gid
            db_extension.status = "active"
            db_extension.version = extension_version # Update version if needed
            logger.info(f"Updated existing extension for account {account_id} on shop {db_shop.shop_domain}")
        else:
            db_extension = Extension(
                shop_id=db_shop.id,
                shopify_extension_id=shopify_gid,
                account_id=account_id,
                status="active",
                version=extension_version,
            )
            db.add(db_extension)
            logger.info(f"Created new extension for account {account_id} on shop {db_shop.shop_domain}")

        await db.commit()
        await db.refresh(db_extension)

        return ShopifyActivateExtensionResponse(
            success=True,
            webPixel={"id": db_extension.shopify_extension_id, "settings": {"accountID": db_extension.account_id}},
            account_id=db_extension.account_id,
            status=db_extension.status,
            version=db_extension.version,
            message="Extension activated successfully."
        )

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in activate extension for shop {request_payload.shop}: {e}",
            exc_info=True,
        )
        await db.rollback() # Rollback on general error
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected server error occurred while activating extension: {str(e)}",
        )


@router.post(
    "/update-extension",
    summary="Updates webpixel extension settings and tracks its status",
    response_model=ShopifyActivateExtensionResponse, # Can reuse or make a specific one
)
async def update_webpixel_extension(
    request_payload: ShopifyActivateExtensionRequest = Body(...), # Reuses request model
    db: AsyncSession = Depends(get_db),
):
    if not request_payload.extension_id:
        raise HTTPException(status_code=400, detail="extension_id (Shopify GID) is required for updates.")
    if not request_payload.extension_settings or "accountID" not in request_payload.extension_settings:
        raise HTTPException(status_code=400, detail="accountID is required in extension_settings for updates.")

    account_id_from_settings = request_payload.extension_settings["accountID"]
    # Assuming a new version might be passed in settings, or we increment it
    new_version = request_payload.extension_settings.get("version", "1.0.1") # Example version handling

    try:
        client = ShopifyClient(
            shop=request_payload.shop, access_token=request_payload.access_token
        )
        # The service method needs extension_id (Shopify GID) and the settings to update.
        # The client.update_extension now takes extension_id and the settings dictionary
        raw_response = await client.update_extension(
            extension_id=request_payload.extension_id,
            settings=request_payload.extension_settings
        )

        if not raw_response or "data" not in raw_response or not raw_response["data"].get("webPixelUpdate"):
            logger.error(f"Invalid response from Shopify update_extension for shop {request_payload.shop}: {raw_response}")
            raise HTTPException(status_code=500, detail="Failed to update extension: Invalid response from Shopify.")

        web_pixel_update_data = raw_response["data"]["webPixelUpdate"]
        if web_pixel_update_data.get("userErrors"):
            user_errors = web_pixel_update_data["userErrors"]
            if user_errors:
                error_message = user_errors[0].get("message", "Unknown error during web pixel update.")
                logger.error(f"Shopify userErrors during webPixelUpdate for {request_payload.shop}: {user_errors}")
                raise HTTPException(status_code=400, detail=f"Shopify error: {error_message}")
        
        shopify_web_pixel_info = web_pixel_update_data.get("webPixel")
        if not shopify_web_pixel_info or "id" not in shopify_web_pixel_info or "settings" not in shopify_web_pixel_info:
            logger.error(f"Missing webPixel id or settings in Shopify update response for {request_payload.shop}: {shopify_web_pixel_info}")
            raise HTTPException(status_code=500, detail="Failed to update extension: Incomplete web pixel data from Shopify.")

        updated_shopify_gid = shopify_web_pixel_info["id"]
        try:
            shopify_settings_json = json.loads(shopify_web_pixel_info["settings"])
            updated_account_id = shopify_settings_json.get("accountID") # This is accountID from Shopify's perspective
        except json.JSONDecodeError:
            logger.error(f"Failed to parse settings JSON from Shopify update response for {request_payload.shop}: {shopify_web_pixel_info['settings']}")
            raise HTTPException(status_code=500, detail="Failed to update extension: Could not parse settings from Shopify.")
        
        if not updated_shopify_gid or not updated_account_id:
            logger.error(f"Extracted updated_shopify_gid or updated_account_id is missing. GID: {updated_shopify_gid}, AccountID: {updated_account_id} for shop {request_payload.shop}")
            raise HTTPException(status_code=500, detail="Failed to update extension: Missing Shopify GID or Account ID after processing response.")

        if updated_account_id != account_id_from_settings:
             logger.warning(f"AccountID mismatch during update for shop {request_payload.shop}: settings '{account_id_from_settings}', response '{updated_account_id}'. Using settings one for DB lookup.")
        # For update, we trust the account_id from settings to find our DB record.

        # Query for existing Shop to get shop_id
        shop_stmt = select(Shop).where(Shop.shop_domain == request_payload.shop)
        shop_result = await db.execute(shop_stmt)
        db_shop = shop_result.scalar_one_or_none()
        if not db_shop:
            raise HTTPException(status_code=404, detail=f"Shop {request_payload.shop} not found.")

        # Query the Extension table using account_id (from settings) and shop_id
        ext_stmt = select(Extension).where(
            Extension.account_id == account_id_from_settings,
            Extension.shop_id == db_shop.id
        )
        ext_result = await db.execute(ext_stmt)
        db_extension = ext_result.scalar_one_or_none()

        if not db_extension:
            # This case is problematic: trying to update an extension we don't know about.
            # For now, raise an error. Could also consider creating it if business logic allows.
            logger.error(f"Extension with account_id {account_id_from_settings} not found in DB for shop {request_payload.shop} during update.")
            raise HTTPException(
                status_code=404,
                detail=f"Extension with account_id '{account_id_from_settings}' not found for shop {request_payload.shop}. Cannot update.",
            )

        # Update found extension
        db_extension.shopify_extension_id = updated_shopify_gid # Shopify GID might change if recreated
        db_extension.status = "active" # Assume update implies active
        db_extension.version = new_version # Update version
        # Potentially update other fields if they are part of extension_settings

        await db.commit()
        await db.refresh(db_extension)
        logger.info(f"Successfully updated extension for account {db_extension.account_id} on shop {db_shop.shop_domain}")

        return ShopifyActivateExtensionResponse( # Reusing response model
            success=True,
            webPixel={"id": db_extension.shopify_extension_id, "settings": request_payload.extension_settings}, # Return settings passed
            account_id=db_extension.account_id,
            status=db_extension.status,
            version=db_extension.version,
            message="Extension updated successfully."
        )

    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in update extension for shop {request_payload.shop}: {e}",
            exc_info=True,
        )
        await db.rollback() # Rollback on general error
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected server error occurred while updating extension: {str(e)}",
        )

# New endpoint for extension status
@router.get(
    "/extension-status",
    summary="Get current status of the webpixel extension for a shop",
    response_model=ExtensionStatusResponse,
)
async def get_extension_status(
    shop_domain: str = Query(..., description="The Shopify domain of the shop (e.g., your-store.myshopify.com)"),
    db: AsyncSession = Depends(get_db),
):
    # Query for the Shop
    shop_stmt = select(Shop).where(Shop.shop_domain == shop_domain)
    shop_result = await db.execute(shop_stmt)
    db_shop = shop_result.scalar_one_or_none()

    if not db_shop:
        # Return a specific response or raise 404 if shop itself not found
        # For this endpoint, we return the model with a message.
        return ExtensionStatusResponse(
            shop_domain=shop_domain,
            message=f"Shop {shop_domain} not found or not yet registered with the app."
        )

    # Query for an active Extension for this shop.
    # Assuming one shop can have one active extension of this type.
    # If multiple are possible, logic might need to be more specific (e.g., filter by a type or primary status)
    ext_stmt = select(Extension).where(
        Extension.shop_id == db_shop.id,
        # Extension.status == "active" # Optionally, only fetch active ones
    ).order_by(Extension.updated_at.desc()) # Get the most recently updated one if multiple
    
    ext_result = await db.execute(ext_stmt)
    db_extension = ext_result.first() # .first() returns a Row or None

    if not db_extension:
        return ExtensionStatusResponse(
            shop_domain=shop_domain,
            message="No web pixel extension configuration found for this shop."
        )
    
    # If db_extension is a Row object, access elements by index or key
    extension_data = db_extension[0] if db_extension else None # Get the Extension object from the Row

    if not extension_data: # Should not happen if db_extension was not None, but good practice
        return ExtensionStatusResponse(
            shop_domain=shop_domain,
            message="Error retrieving extension data." # Should be more specific if possible
        )

    return ExtensionStatusResponse(
        shop_domain=shop_domain,
        account_id=extension_data.account_id,
        shopify_extension_id=extension_data.shopify_extension_id,
        status=extension_data.status,
        version=extension_data.version,
        message="Extension status retrieved successfully."
    )


@router.get("/app-home", summary="Temporary App Home Page", include_in_schema=False) # Hiding from OpenAPI for now
async def app_home(
    shop: str, # This comes from query param e.g. /app-home?shop=...
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
