import hmac
import hashlib
import base64
from typing import List, Dict, Any
from urllib.parse import urlencode
import secrets
import string


def generate_shopify_auth_url(
    shop_domain: str,
    api_key: str,
    scopes: str,
    redirect_uri: str,
    state: str,
    grant_options: List[str] = None,
) -> str:
    """
    Generates the Shopify authorization URL.
    """
    query_params = {
        "client_id": api_key,
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if grant_options:
        # For online access mode if needed
        query_params["grant_options[]"] = grant_options

    return f"https://{shop_domain}/admin/oauth/authorize?{urlencode(query_params)}"


def verify_hmac(
    query_params_string: str, received_hmac: str, api_secret_key: str
) -> bool:
    """
    Verifies the HMAC signature from Shopify.
    Note: query_params_string should be the raw query string (e.g., from request.scope['query_string'])
    with the 'hmac' parameter REMOVED, and other parameters sorted alphabetically.
    The shopify_auth_router.py already prepares this string.
    """
    if not query_params_string or not received_hmac or not api_secret_key:
        return False

    calculated_hmac = hmac.new(
        api_secret_key.encode("utf-8"),
        query_params_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # logger.debug(f"Received HMAC: {received_hmac}")
    # logger.debug(f"Calculated HMAC: {calculated_hmac}")
    # logger.debug(f"Verifiable Query String: {query_params_string}")

    return hmac.compare_digest(calculated_hmac, received_hmac)


# Example of how HMAC was previously constructed in some Shopify examples (might not be needed directly if router handles it)
# def _calculate_hmac(data: Dict[str, Any], api_secret_key: str) -> str:
#     """
#     Helper to calculate HMAC for a dictionary of parameters.
#     This is typically used when you have parameters as a dict,
#     need to sort them, form a query string, and then HMAC it.
#     The verify_hmac function above expects the pre-sorted query string directly.
#     """
#     # Create the message string by joining sorted key-value pairs
#     message = "&".join([f"{key}={value}" for key, value in sorted(data.items())])
#     digest = hmac.new(
#         api_secret_key.encode('utf-8'),
#         message.encode('utf-8'),
#         hashlib.sha256
#     ).hexdigest()
#     return digest


def generate_id(length=8):
    characters = string.ascii_letters + string.digits  # a-zA-Z0-9
    return "".join(secrets.choice(characters) for _ in range(length))


async def register_webhooks(
    shop_domain: str, access_token: str, api_version: str, app_url: str
):
    """
    Registers necessary webhooks with Shopify for the given shop.
    """
    import httpx  # Import httpx locally within the async function
    import logging # Import logging

    logger = logging.getLogger(__name__)

    webhook_topics = [
        "customers/data_request",
        "customers/redact",
        "shop/redact",
        "app/uninstalled",
    ]
    webhook_base_url = f"https://{shop_domain}/admin/api/{api_version}/webhooks.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    # Ensure app_url ends with a slash if it doesn't, for proper joining with "webhooks"
    # However, Shopify webhook address should be a full URL.
    # Assuming app_url is the base (e.g., "https://myapp.com") and webhook endpoint is at "/webhooks"
    # So, the callback_url should be "https://myapp.com/webhooks"
    # If app_url might already include /webhooks or other paths, this needs care.
    # For this implementation, we assume app_url is the *base* and "/webhooks" is the fixed path.
    callback_url = f"{app_url.rstrip('/')}/webhooks"


    async with httpx.AsyncClient(verify=False) as client: # verify=False for simplicity, use SSL context in prod
        for topic in webhook_topics:
            payload = {
                "webhook": {"topic": topic, "address": callback_url, "format": "json"}
            }
            try:
                response = await client.post(webhook_base_url, headers=headers, json=payload)
                if response.status_code == 201:  # Created
                    logger.info(
                        f"Successfully registered webhook {topic} for shop {shop_domain} to {callback_url}."
                    )
                elif response.status_code == 422: # Unprocessable Entity
                    # This often means the webhook already exists for this topic and address.
                    # Shopify returns errors in a list, e.g., {"errors": {"address": ["has already been taken"]}}
                    error_details = response.json()
                    if "address" in error_details.get("errors", {}) and any("has already been taken" in e for e in error_details["errors"]["address"]):
                        logger.info(
                            f"Webhook {topic} for shop {shop_domain} to {callback_url} already exists. No action needed."
                        )
                    else:
                        logger.warning(
                            f"Failed to register webhook {topic} for shop {shop_domain}. Status: {response.status_code}, Response: {response.text}"
                        )
                else:
                    response.raise_for_status() # Raise an exception for other 4xx/5xx errors
                    logger.info(
                        f"Successfully registered webhook {topic} for shop {shop_domain}."
                    )
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error registering webhook {topic} for shop {shop_domain}: {e.response.status_code} - {e.response.text}"
                )
            except httpx.RequestError as e:
                logger.error(
                    f"Request error registering webhook {topic} for shop {shop_domain}: {e}"
                )
            except Exception as e:
                logger.exception(
                    f"An unexpected error occurred while registering webhook {topic} for shop {shop_domain}: {e}"
                )
