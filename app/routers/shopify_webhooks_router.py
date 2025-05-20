import logging
import json
from fastapi import APIRouter, Request, Header, HTTPException, Depends, Response, status # Added Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_ # Added delete, or_

from app.core.config import settings
from app.utils.webhook_utils import verify_shopify_webhook_hmac
from app.db.session import get_db
from app.models.shop_model import Shop
from app.models.event_model import Event
from app.models.extension_model import Extension # Added Extension model

logger = logging.getLogger(__name__)
router = APIRouter()


async def handle_customers_data_request(
    shop_domain: str, 
    payload: dict, 
    db: AsyncSession = Depends(get_db) # Added db session
):
    logger.info(f"CUSTOMERS_DATA_REQUEST for shop {shop_domain}. Payload: {json.dumps(payload, indent=2)}")

    customer_data = payload.get("customer", {})
    customer_id_from_payload = customer_data.get("id") # This is Shopify Customer GID, e.g., "gid://shopify/Customer/12345"
    
    # shop_id_from_payload = payload.get("shop_id") # Shopify's internal integer ID for the shop
    shop_domain_from_payload = payload.get("shop_domain")

    if not customer_id_from_payload:
        logger.error(f"CUSTOMERS_DATA_REQUEST: customer.id not found in payload for shop {shop_domain}.")
        # Shopify still expects a 200 OK.
        return

    if shop_domain_from_payload != shop_domain:
        logger.warning(
            f"CUSTOMERS_DATA_REQUEST: Mismatch between header shop_domain ('{shop_domain}') and payload shop_domain ('{shop_domain_from_payload}'). Using header domain."
        )
        # Proceed with shop_domain from header as it's verified by HMAC.

    # Query for the Shop to get our internal shop_id
    shop_stmt = select(Shop).where(Shop.shop_domain == shop_domain)
    shop_result = await db.execute(shop_stmt)
    db_shop = shop_result.scalar_one_or_none()

    if not db_shop:
        logger.error(f"CUSTOMERS_DATA_REQUEST: Shop not found in database for domain {shop_domain}.")
        # Shopify still expects a 200 OK.
        return

    # Query for events related to this customer_id within this shop_id
    # Assuming customer GID in event payload is at path 'customer.id'
    # The ->> operator extracts a JSON object field as text.
    # The path 'customer.id' implies payload is like {"customer": {"id": "gid_value"}}
    # If customer_id_from_payload is an integer, ensure it's cast to string for comparison if needed,
    # but Shopify GIDs are strings.
    
    # customer.id is a GID, so it's a string.
    # Event.payload['customer']['id'] should also be a string.
    # Example: payload={'customer': {'id': 'gid://shopify/Customer/123'}}
    
    # To query JSONB for payload['customer']['id'] == customer_id_from_payload:
    # Method 1: Casting to text (if customer_id_from_payload is a string GID)
    # query = select(Event).where(
    #     Event.shop_id == db_shop.id,
    #     Event.payload.op("->")("customer").op("->>")("id") == str(customer_id_from_payload)
    # )

    # Method 2: Using JSONB path existence and value check (more robust if types are certain)
    # This checks if payload has 'customer' which has 'id' equal to customer_id_from_payload
    # The @> operator means "contains", so we check if the 'customer' object contains {'id': customer_id_from_payload}
    # This requires customer_id_from_payload to be correctly typed (string for GID).
    # query = select(Event).where(
    #     Event.shop_id == db_shop.id,
    #     Event.payload.op("->")("customer").op("@>")({"id": str(customer_id_from_payload)}) # This is for JSON, not JSONB path
    # )
    # For JSONB, a common way to check a nested value:
    # (Event.payload['customer']['id'].astext == customer_id_from_payload)
    # However, this specific syntax might vary slightly or require specific dialect setups.
    # A more portable way for simple equality on a known path:
    query = select(Event).where(
        Event.shop_id == db_shop.id,
        Event.payload.op("->")("customer").op("->>")("id") == str(customer_id_from_payload)
    )
    # Alternative: Check buyerIdentity path as well, if applicable
    # query_alt = select(Event).where(
    #     Event.shop_id == db_shop.id,
    #     Event.payload.op("->")("cart").op("->")("buyerIdentity").op("->")("customer").op("->>")("id") == str(customer_id_from_payload)
    # )
    # For now, sticking to the primary customer.id path.

    logger.info(f"Executing event query for customer {customer_id_from_payload} in shop {db_shop.shop_domain} (ID: {db_shop.id})")
    results = await db.execute(query)
    customer_events = results.scalars().all()

    compiled_data = []
    if customer_events:
        for event in customer_events:
            compiled_data.append({
                "event_id": event.id,
                "event_name": event.event_name,
                "payload": event.payload, # Or specific parts of it
                "received_at": event.received_at.isoformat()
            })
        logger.info(f"CUSTOMERS_DATA_REQUEST: Found {len(compiled_data)} events for customer {customer_id_from_payload} in shop {shop_domain}.")
        # For GDPR, you'd typically provide this data through a secure channel, not log all of it in production.
        # For this task, logging is the specified action.
        logger.info(f"Customer data request for customer {customer_id_from_payload} in shop {shop_domain}: {json.dumps(compiled_data, indent=2)}")
    else:
        logger.info(f"CUSTOMERS_DATA_REQUEST: No events found for customer {customer_id_from_payload} in shop {shop_domain}.")
    
    # Shopify expects a 200 OK. The actual data delivery is out-of-band.
    # This function's purpose is to acknowledge the request and gather data.
    # The data would then be sent to Shopify, typically via an email to the customer or a secure portal.
    # For now, we've logged it.


async def handle_customers_redact(
    shop_domain: str, 
    payload: dict, 
    db: AsyncSession # db session will be passed from receive_webhook
):
    customer_data = payload.get("customer", {})
    customer_id_to_redact = customer_data.get("id") # This is Shopify Customer GID
    
    shop_id_from_payload = payload.get("shop_id") # Shopify's internal integer ID for the shop
    shop_domain_from_payload = payload.get("shop_domain")
    orders_to_redact = payload.get("orders_to_redact", [])

    logger.info(f"CUSTOMERS_REDACT request for shop {shop_domain} (payload shop_id: {shop_id_from_payload}, payload_shop_domain: {shop_domain_from_payload}), customer GID: {customer_id_to_redact}.")
    if orders_to_redact:
        logger.info(f"Customer {customer_id_to_redact} in shop {shop_domain} also requested redaction for orders: {orders_to_redact}")

    if not customer_id_to_redact:
        logger.error(f"CUSTOMERS_REDACT: customer.id not found in payload for shop {shop_domain}.")
        # Shopify still expects a 200 OK.
        return

    if shop_domain_from_payload != shop_domain:
        logger.warning(
            f"CUSTOMERS_REDACT: Mismatch between header shop_domain ('{shop_domain}') and payload shop_domain ('{shop_domain_from_payload}'). Using header domain."
        )
        # Proceed with shop_domain from header as it's verified by HMAC.

    # Query for the Shop to get our internal shop_id
    shop_stmt = select(Shop).where(Shop.shop_domain == shop_domain)
    shop_result = await db.execute(shop_stmt)
    db_shop = shop_result.scalar_one_or_none()

    if not db_shop:
        logger.error(f"CUSTOMERS_REDACT: Shop not found in database for domain {shop_domain}.")
        # Shopify still expects a 200 OK.
        return

    # Redaction Strategy: Delete matching events
    customer_gid = str(customer_id_to_redact)
    
    # Define conditions for matching customer GID in various potential payload locations
    # Using op("->>") for direct text comparison. Using op("->") then op("->>") for nested objects.
    conditions = [
        Event.payload.op("->")("customer").op("->>")("id") == customer_gid,
        Event.payload.op("->")("cart").op("->")("buyerIdentity").op("->")("customer").op("->>")("id") == customer_gid,
        # Add other relevant paths based on your Web Pixel event structure if necessary
        # Example: Event.payload.op("->>")("customerId") == customer_gid (if customerId is a top-level key)
    ]

    # If orders_to_redact is provided, add conditions for these order IDs
    # Assuming order_id might be stored at payload['order']['id'] or payload['order_id']
    # This part is additive; events matching EITHER customer OR these orders (for this customer)
    # However, Shopify's intent is typically to redact data for specific orders *belonging to this customer*.
    # So, the primary filter should usually remain customer_id, and then within those events,
    # if order_id is a relevant PII field, it might be nulled.
    # For simple deletion of events, if an event has one of these order_ids AND the customer_id, it would be deleted.
    # The current condition `or_(*conditions)` already covers events linked to the customer.
    # If events might be linked *only* by order_id without customer_id directly in payload (less common for GDPR customer redaction),
    # then the query would need to be more complex.
    # For now, we focus on events identified by customer_gid.
    # If orders_to_redact implies redacting events that *only* match order_id and *not* customer_gid,
    # that's a different scope. The current interpretation is: redact data for *this customer*,
    # and Shopify informs us which orders are also involved. The primary key for redaction is the customer.
    
    # The task states: "If your Event payloads contain order_id, you should also find and redact events
    # associated with these orders for the given customer."
    # This means we should look for events matching the customer_gid that ALSO match one of the orders_to_redact.
    # However, the example query deletes based on customer ID OR other customer ID paths.
    # Let's stick to the provided query logic which focuses on customer GID.
    # If order-specific redaction within customer's events is needed, payload modification would be better.
    # Since we are deleting the whole event, finding by customer GID is sufficient.
    # The orders_to_redact list is more for if we were to *also* query an Orders table or similar.

    select_query = select(Event.id).where(Event.shop_id == db_shop.id, or_(*conditions))
    
    try:
        event_ids_to_delete_result = await db.execute(select_query)
        event_ids_to_delete = event_ids_to_delete_result.scalars().all()

        if event_ids_to_delete:
            logger.info(f"Found {len(event_ids_to_delete)} events to redact for customer {customer_id_to_redact} in shop {shop_domain}.")
            
            delete_stmt = delete(Event).where(Event.id.in_(event_ids_to_delete))
            await db.execute(delete_stmt)
            await db.commit()
            
            logger.info(f"Successfully redacted (deleted) {len(event_ids_to_delete)} events for customer {customer_id_to_redact} in shop {shop_domain}.")
        else:
            logger.info(f"No events found to redact for customer {customer_id_to_redact} in shop {shop_domain}.")
            
    except Exception as e:
        await db.rollback()
        logger.error(f"CUSTOMERS_REDACT: Error during database operation for customer {customer_id_to_redact}, shop {shop_domain}: {e}", exc_info=True)
        # Even on DB error, Shopify expects a 200 OK to prevent retries.
        # The error is logged for internal review.

    # Shopify expects a 200 OK to acknowledge receipt.
    return # Implicitly returns 200 OK with no content if not using Response explicitly.


async def handle_shop_redact(
    shop_domain: str, 
    payload: dict, 
    db: AsyncSession # db session will be passed from receive_webhook
):
    shop_domain_from_payload = payload.get("shop_domain")
    logger.info(f"SHOP_REDACT request for shop {shop_domain} (payload shop_domain: {shop_domain_from_payload})")

    if shop_domain_from_payload != shop_domain:
        logger.warning(
            f"SHOP_REDACT: Mismatch between header shop_domain ('{shop_domain}') and payload shop_domain ('{shop_domain_from_payload}'). Using header domain."
        )
        # Proceed with shop_domain from header as it's verified by HMAC.

    # Query for the Shop
    shop_stmt = select(Shop).where(Shop.shop_domain == shop_domain)
    shop_result = await db.execute(shop_stmt)
    db_shop = shop_result.scalar_one_or_none()

    if not db_shop:
        logger.error(f"SHOP_REDACT: Shop not found in database for domain {shop_domain}.")
        # Shopify still expects a 200 OK.
        return Response(status_code=status.HTTP_200_OK)


    try:
        # Delete Events associated with the shop
        delete_events_query = delete(Event).where(Event.shop_id == db_shop.id)
        event_delete_result = await db.execute(delete_events_query)
        logger.info(f"SHOP_REDACT: Deleted {event_delete_result.rowcount} events for shop {shop_domain} (ID: {db_shop.id}).")

        # Delete Extensions associated with the shop
        # Note: If Shop.extensions relationship has cascade="all, delete-orphan", this is technically redundant
        # if we were deleting the shop. But since we are soft-handling the shop, explicit deletion is correct.
        delete_extensions_query = delete(Extension).where(Extension.shop_id == db_shop.id)
        extension_delete_result = await db.execute(delete_extensions_query)
        logger.info(f"SHOP_REDACT: Deleted {extension_delete_result.rowcount} extensions for shop {shop_domain} (ID: {db_shop.id}).")

        # Soft-handle the Shop record
        db_shop.access_token = None  # Redact access token
        db_shop.is_installed = False # Mark as uninstalled
        # Potentially nullify or anonymize other PII fields on the Shop model if necessary
        # For example: db_shop.shopify_scopes = None
        
        db.add(db_shop) # Add the modified shop object to the session
        logger.info(f"SHOP_REDACT: Shop record for {shop_domain} (ID: {db_shop.id}) marked as uninstalled and access token redacted.")
        
        await db.commit()
        logger.info(f"SHOP_REDACT: Successfully processed for shop {shop_domain} (ID: {db_shop.id}). All associated data redacted/marked.")

    except Exception as e:
        await db.rollback()
        logger.error(f"SHOP_REDACT: Error during database operations for shop {shop_domain} (ID: {db_shop.id if db_shop else 'N/A'}): {e}", exc_info=True)
        # Even on DB error, Shopify expects a 200 OK to prevent retries.
    
    # Ensure 200 OK is returned to Shopify
    return Response(status_code=status.HTTP_200_OK)


@router.post("", summary="Receive Shopify Webhooks", status_code=200)
async def receive_webhook(
    request: Request,
    x_shopify_topic: str = Header(None),
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: AsyncSession = Depends(get_db) # Added db session
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
        await handle_customers_data_request(x_shopify_shop_domain, payload, db) # Pass db
    elif x_shopify_topic == "customers/redact":
        await handle_customers_redact(x_shopify_shop_domain, payload, db) # Pass db
    elif x_shopify_topic == "shop/redact":
        await handle_shop_redact(x_shopify_shop_domain, payload, db) # Pass db, ensure this handler also takes it
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
