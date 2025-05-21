import logging
import json
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.utils.webhook_utils import verify_shopify_webhook_hmac

logger = logging.getLogger(__name__)
router = APIRouter()


async def handle_customers_data_request(shop_domain: str, payload: dict):
    logger.info(f"Received CUSTOMERS_DATA_REQUEST for shop {shop_domain} with payload: {json.dumps(payload, indent=2)}")

    shop_id = payload.get("shop_id")
    customer_payload = payload.get("customer", {})
    customer_id = customer_payload.get("id")
    customer_email = customer_payload.get("email")
    customer_phone = customer_payload.get("phone")
    orders_requested = payload.get("orders_requested", [])
    data_request_payload = payload.get("data_request", {})
    data_request_id = data_request_payload.get("id")

    logger.info(f"Shop ID: {shop_id}")
    logger.info(f"Shop Domain (from payload): {payload.get('shop_domain')}") # Also available as shop_domain param
    logger.info(f"Customer ID: {customer_id}")
    logger.info(f"Customer Email: {customer_email}")
    logger.info(f"Customer Phone: {customer_phone}")
    logger.info(f"Orders Requested: {orders_requested}")
    logger.info(f"Data Request ID: {data_request_id}")

    # Placeholder for actual data retrieval logic
    logger.info(f"Data retrieval for shop {shop_domain} (ID: {shop_id}) and customer {customer_id} would happen here.")

    # In a real scenario:
    # 1. Fetch shop's access token from DB.
    # 2. Use Shopify API to get customer data (orders, profile, etc.).
    # 3. Package data for Shopify (this webhook doesn't send data back directly, but prepares it for Shopify's system to fetch).
    # This webhook's purpose is to acknowledge the request and prepare data.
    # Shopify will then make a separate request to an endpoint you provide (if applicable for this specific GDPR flow)
    # or expect you to use their APIs to fulfill the data subject request.
    # For CUSTOMERS_DATA_REQUEST, you typically prepare data and Shopify's system fetches it or you notify them.
    # The immediate response to the webhook should be a 200 OK.
    pass


async def handle_customers_redact(shop_domain: str, payload: dict):
    logger.info(f"Received CUSTOMERS_REDACT for shop {shop_domain} with payload: {json.dumps(payload, indent=2)}")

    shop_id = payload.get("shop_id")
    payload_shop_domain = payload.get("shop_domain") # shop_domain is also passed as a parameter
    customer_payload = payload.get("customer", {})
    customer_id = customer_payload.get("id")
    # Customer email and phone are PII and are part of the payload, but we don't need to log them explicitly again here
    # as the full payload is already logged. The key is to use customer_id for redaction.
    orders_to_redact = payload.get("orders_to_redact", [])

    logger.info(f"Shop ID: {shop_id}")
    logger.info(f"Shop Domain (from payload): {payload_shop_domain}")
    logger.info(f"Customer ID to redact: {customer_id}")
    logger.info(f"Order IDs to redact: {orders_to_redact}")

    # Placeholder for actual data redaction logic
    logger.info(f"Data redaction for shop {shop_domain} (ID: {shop_id}) and customer {customer_id} would happen here in the application's database.")
    # In a real scenario:
    # 1. Identify all records in your database associated with this customer_id and shop_id.
    #    This might include customer profile data, event logs, order copies, etc.
    # 2. For each identified record, anonymize or delete PII fields.
    #    - Example: customer.name = "REDACTED", customer.email = "REDACTED", event.user_ip = "0.0.0.0"
    #    - Be thorough and consider all locations where PII might be stored.
    # 3. If `orders_to_redact` contains order IDs, ensure any PII specific to those orders
    #    (that isn't directly on the customer record but stored in your system for those orders) is also redacted.
    # This process must be irreversible for the PII.
    # The immediate response to the webhook should be a 200 OK.
    pass


async def handle_shop_redact(shop_domain: str, payload: dict):
    logger.info(f"Received SHOP_REDACT for shop {shop_domain} with payload: {json.dumps(payload, indent=2)}")

    shop_id = payload.get("shop_id")
    payload_shop_domain = payload.get("shop_domain") # shop_domain is also passed as a parameter

    logger.info(f"Shop ID: {shop_id}")
    logger.info(f"Shop Domain (from payload): {payload_shop_domain}") # Should match shop_domain param

    # Placeholder for actual data redaction logic
    logger.info(f"Full data redaction for shop {shop_domain} (ID: {shop_id}) would happen here. This involves deleting all shop-related data from the application's database (Shop record, access tokens, events, extension data, etc.).")
    # In a real scenario:
    # 1. Connect to your database.
    # 2. Cascade delete all records related to this shop_id or shop_domain.
    #    - This includes the main Shop record (which should also delete its access token).
    #    - Any associated event data, customer data copies, configuration settings, etc.
    #    - This is a critical and destructive operation. Ensure it's what you need.
    # 3. For example, using SQLAlchemy, you might find the Shop object and delete it,
    #    relying on cascade rules in your DB or ORM to clean up related data.
    #    Or, you might need to delete from multiple tables explicitly if cascades are not set up.
    # The immediate response to the webhook should be a 200 OK.
    pass


async def handle_app_uninstalled(shop_domain: str, payload: dict):
    logger.info(f"APP_UNINSTALLED webhook received for shop {shop_domain} with payload: {json.dumps(payload, indent=2)}")

    # Shopify's payload for app/uninstalled is typically simple, mainly containing shop domain.
    # 'id' in the payload usually refers to the shop's numeric ID.
    # 'domain' in the payload is the shop's myshopify.com domain.
    shop_id_from_payload = payload.get("id") # This is usually the shop's numeric ID
    shop_domain_from_payload = payload.get("domain") # This is usually the shop's myshopify.com domain

    logger.info(f"Shop ID (from payload, if available): {shop_id_from_payload}")
    logger.info(f"Shop Domain (from payload, if available): {shop_domain_from_payload}") # Should match shop_domain param

    # Placeholder for actual data deletion logic
    # This is often the same as SHOP_REDACT: all data for the shop should be removed.
    logger.info(f"App uninstallation for shop {shop_domain}. All data for this shop will be deleted from the application's database (Shop record, access tokens, events, extension data, etc.).")
    # In a real scenario:
    # 1. Connect to your database.
    # 2. Perform the same data deletion operations as for SHOP_REDACT.
    #    This means deleting all records associated with this shop_domain (or shop_id if you use that as primary key).
    #    - Main Shop record (which includes access token).
    #    - Associated event data, user data, configurations, etc.
    # 3. Ensure this is a thorough cleanup.
    # The immediate response to the webhook should be a 200 OK.
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
    elif x_shopify_topic == "app/uninstalled":
        await handle_app_uninstalled(x_shopify_shop_domain, payload)
    else:
        logger.warning(
            f"Received unhandled webhook topic: {x_shopify_topic} for shop {x_shopify_shop_domain}")
        # Still return 200 to acknowledge receipt and prevent Shopify retries

    return JSONResponse(content={"status": "webhook received"})
