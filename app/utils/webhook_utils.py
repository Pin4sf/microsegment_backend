import hashlib
import hmac
import base64
import logging

logger = logging.getLogger(__name__)


def verify_shopify_webhook_hmac(data: bytes, secret: str, received_hmac: str) -> bool:
    """
    Verifies the HMAC signature of an incoming Shopify webhook request.

    Args:
        data: The raw request body (bytes).
        secret: The Shopify App's API secret key.
        received_hmac: The HMAC signature from the X-Shopify-Hmac-SHA256 header.

    Returns:
        True if the HMAC is valid, False otherwise.
    """
    if not data or not secret or not received_hmac:
        logger.warning(
            "HMAC verification attempted with missing data, secret, or received_hmac.")
        return False

    try:
        calculated_hmac_bytes = hmac.new(secret.encode(
            'utf-8'), data, hashlib.sha256).digest()
        calculated_hmac_b64 = base64.b64encode(
            calculated_hmac_bytes).decode('utf-8')

        logger.debug(
            f"Calculated HMAC: {calculated_hmac_b64}, Received HMAC: {received_hmac}")
        return hmac.compare_digest(calculated_hmac_b64, received_hmac)
    except Exception as e:
        logger.error(
            f"Error during HMAC calculation or comparison: {e}", exc_info=True)
        return False
