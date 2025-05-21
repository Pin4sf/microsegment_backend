import logging
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.shopify_service import ShopifyClient
from app.models.shop_model import Shop # For type hinting, not strictly needed for current logic
from app.core.config import settings # To build the full webhook URL if needed here, or pass full URL

logger = logging.getLogger(__name__)

# Define the topics for which webhooks are required
REQUIRED_TOPICS = [
    "CUSTOMERS_DATA_REQUEST",
    "CUSTOMERS_REDACT",
    "SHOP_REDACT",
    "APP_UNINSTALLED", # Added APP_UNINSTALLED as per subtask
]

async def register_all_required_webhooks(
    shop_client: ShopifyClient,
    webhook_base_url: str, # e.g., settings.SHOPIFY_APP_URL
    db_shop: Shop, # For context, like shop_id or domain, if needed for logging/storage
    db: AsyncSession # For potential future DB operations like storing webhook IDs
):
    """
    Registers all required webhooks for a given shop if they don't already exist
    with the correct callback URL.

    Args:
        shop_client: An instance of ShopifyClient initialized for the specific shop.
        webhook_base_url: The base URL for the application (e.g., from settings.SHOPIFY_APP_URL).
        db_shop: The Shop database model instance.
        db: The AsyncSession for database operations.
    """
    # The webhook router is mounted at /webhooks as per previous steps.
    # So, the callback URL needs to append this path.
    # If SHOPIFY_APP_URL is "https://myapp.com", callback is "https://myapp.com/webhooks"
    # If SHOPIFY_APP_URL is "https://myapp.com/app", callback is "https://myapp.com/app/webhooks"
    # Let's ensure no double slashes if webhook_base_url might end with one.
    if webhook_base_url.endswith('/'):
        webhook_base_url = webhook_base_url[:-1]
    
    # The main webhook router is mounted at /webhooks (from main.py)
    # The endpoint itself within that router is "" (empty path for POST)
    # So the full URL for Shopify to call is webhook_base_url + /webhooks
    full_callback_url = f"{webhook_base_url}/webhooks" 

    logger.info(f"Starting webhook registration process for shop: {db_shop.shop_domain}. Target callback URL: {full_callback_url}")

    try:
        # Fetch existing webhooks
        # The get_existing_webhooks method returns a list of dicts: {'id': ..., 'topic': ..., 'callbackUrl': ...}
        existing_webhooks = await shop_client.get_existing_webhooks()
        
        # Create a set of (topic, callbackUrl) for quick lookup of existing, correctly configured webhooks
        # Only consider webhooks that point to our current, correct callback URL
        active_correct_webhooks = set()
        for wh in existing_webhooks:
            if wh['callbackUrl'] == full_callback_url:
                active_correct_webhooks.add(wh['topic'])
            # Optionally, log or delete webhooks that point to outdated callback URLs for the same topic

        logger.info(f"Found {len(existing_webhooks)} existing webhooks for shop {db_shop.shop_domain}. Active and correct: {active_correct_webhooks}")

        for topic in REQUIRED_TOPICS:
            if topic in active_correct_webhooks:
                logger.info(f"Webhook for topic '{topic}' already exists and is correctly configured for shop {db_shop.shop_domain}.")
            else:
                logger.info(f"Webhook for topic '{topic}' not found or misconfigured for shop {db_shop.shop_domain}. Attempting to register...")
                registration_result = await shop_client.register_webhook(topic, full_callback_url)
                
                if "id" in registration_result and registration_result.get("id"):
                    logger.info(f"Successfully registered webhook for topic '{topic}' for shop {db_shop.shop_domain}. ID: {registration_result['id']}")
                    # Optional: Store registration_result['id'] in DB associated with db_shop.id and topic
                elif "error" in registration_result:
                    error_details = registration_result.get("details", "No details provided.")
                    # Check for specific userErrors, e.g., if callback URL is not whitelisted or other issues
                    if "UserErrors reported by Shopify" in registration_result["error"] and error_details:
                        for err in error_details: # error_details is expected to be a list of error dicts
                             if "callbackUrl has already been taken" in err.get("message", ""):
                                logger.warning(f"Webhook for topic '{topic}' at {full_callback_url} likely already exists but wasn't matched (possibly due to Shopify propagation delay or slight URL variation if any). Error: {err.get('message')}")
                                break # Break from error loop, assume it's okay.
                        else: # If no break from loop (no specific known error message)
                            logger.error(f"Failed to register webhook for topic '{topic}' for shop {db_shop.shop_domain}. Error: {registration_result['error']}, Details: {error_details}")
                    else:
                         logger.error(f"Failed to register webhook for topic '{topic}' for shop {db_shop.shop_domain}. Error: {registration_result['error']}, Details: {error_details}")
                else:
                    logger.error(f"Failed to register webhook for topic '{topic}' for shop {db_shop.shop_domain}. Unexpected response: {registration_result}")

    except Exception as e:
        logger.error(f"An unexpected error occurred during webhook registration for shop {db_shop.shop_domain}: {e}", exc_info=True)

    logger.info(f"Webhook registration process completed for shop: {db_shop.shop_domain}.")
