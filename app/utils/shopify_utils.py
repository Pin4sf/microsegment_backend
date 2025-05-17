import hmac
import hashlib
import base64
from typing import List, Dict, Any
from urllib.parse import urlencode


def generate_shopify_auth_url(
    shop_domain: str,
    api_key: str,
    scopes: List[str],
    redirect_uri: str,
    state: str,
    grant_options: List[str] = None
) -> str:
    """
    Generates the Shopify authorization URL.
    """
    query_params = {
        "client_id": api_key,
        "scope": ",".join(scopes),
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if grant_options:
        # For online access mode if needed
        query_params["grant_options[]"] = grant_options

    return f"https://{shop_domain}/admin/oauth/authorize?{urlencode(query_params)}"


def verify_hmac(query_params_string: str, received_hmac: str, api_secret_key: str) -> bool:
    """
    Verifies the HMAC signature from Shopify.
    Note: query_params_string should be the raw query string (e.g., from request.scope['query_string'])
    with the 'hmac' parameter REMOVED, and other parameters sorted alphabetically.
    The shopify_auth_router.py already prepares this string.
    """
    if not query_params_string or not received_hmac or not api_secret_key:
        return False

    calculated_hmac = hmac.new(
        api_secret_key.encode('utf-8'),
        query_params_string.encode('utf-8'),
        hashlib.sha256
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
