import logging
import json
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.utils.webhook_utils import verify_shopify_webhook_hmac

logger = logging.getLogger(__name__)
router = APIRouter()


async def handle_customers_data_request(shop_domain: str, payload: dict):
    logger.info(f"CUSTOMERS_DATA_REQUEST for shop {shop_domain}: {payload}")
    # TODO: Implement logic to retrieve and return customer data.
    # This might involve fetching data from Shopify using an access token for the shop
    # and then packaging it according to Shopify's requirements.
    # Ensure this process is quick or use background tasks.
    pass


async def handle_customers_redact(shop_domain: str, payload: dict):
    logger.info(f"CUSTOMERS_REDACT for shop {shop_domain}: {payload}")
    # TODO: Implement logic to redact customer data from your systems.
    # This means deleting any personally identifiable information (PII)
    # for the customer specified in the payload.
    pass


async def handle_shop_redact(shop_domain: str, payload: dict):
    logger.info(f"SHOP_REDACT for shop {shop_domain}: {payload}")
    # TODO: Implement logic to redact all data associated with the shop.
    # This includes deleting stored access tokens, shop-specific configurations,
    # and any other data related to this shop.
    pass


@router.post("", summary="Receive Shopify Webhooks", status_code=200)
async def receive_webhook(
    request: Request,
    x_shopify_topic: str = Header(None),
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None)
):
    """
    Receives, authenticates, and dispatches Shopify webhooks.
    Responds with HTTP 200 to all valid, authenticated webhooks to prevent retries.
    """
    if not x_shopify_topic or not x_shopify_hmac_sha256 or not x_shopify_shop_domain:
        logger.error("Webhook request missing required Shopify headers.")
        raise HTTPException(status_code=400, detail="Missing Shopify headers")

    raw_body = await request.body()

    is_hmac_valid = verify_shopify_webhook_hmac(
        data=raw_body,
        secret=settings.SHOPIFY_API_SECRET,
        received_hmac=x_shopify_hmac_sha256
    )

    if not is_hmac_valid:
        logger.error(
            f"Webhook HMAC validation failed for shop {x_shopify_shop_domain}, topic {x_shopify_topic}.")
        raise HTTPException(
            status_code=401, detail="HMAC validation failed. Request is not authentic.")

    try:
        payload = json.loads(raw_body.decode('utf-8')) if raw_body else {}
    except json.JSONDecodeError:
        logger.error(
            f"Failed to decode JSON payload for shop {x_shopify_shop_domain}, topic {x_shopify_topic}.")
        # Still return 200 as Shopify expects, but log the error.
        return JSONResponse(
            content={"status": "error", "message": "Invalid JSON payload"},
            status_code=200  # Shopify expects 200 to not retry, even on payload error
        )

    logger.info(
        f"Received webhook for shop {x_shopify_shop_domain}, topic: {x_shopify_topic}")
    # logger.debug(f"Webhook payload for {x_shopify_topic}: {payload}") # Log full payload if needed, can be verbose

    if x_shopify_topic == "customers/data_request":
        await handle_customers_data_request(x_shopify_shop_domain, payload)
    elif x_shopify_topic == "customers/redact":
        await handle_customers_redact(x_shopify_shop_domain, payload)
    elif x_shopify_topic == "shop/redact":
        await handle_shop_redact(x_shopify_shop_domain, payload)
    # Example for APP_UNINSTALLED if you add it later
    # elif x_shopify_topic == "app/uninstalled":
    #     logger.info(f"APP_UNINSTALLED for shop {x_shopify_shop_domain}: {payload}")
    #     # TODO: Handle app uninstallation, like cleaning up shop data, deactivating services.
    #     pass
    else:
        logger.warning(
            f"Received unhandled webhook topic: {x_shopify_topic} for shop {x_shopify_shop_domain}")
        # Still return 200 to acknowledge receipt and prevent Shopify retries

    return JSONResponse(content={"status": "webhook received"})
