# Jules - Feature Implementation Summary

This document summarizes the key features implemented by the AI assistant, Jules, for the Micro Segment Shopify App.

## Part 1: Web Pixel Extension Integration

This part covers the backend setup for handling a Shopify Web Pixel extension, enabling event tracking and management.

### 1. Database Schema
The following SQLAlchemy models were defined to store extension-related data:

-   **`Extension` Model (`app/models/extension_model.py`):**
    *   Tracks web pixel extensions installed by shops.
    *   Key fields: `id` (PK), `shop_id` (FK to `shops.id`), `shopify_extension_id` (Shopify's GID for the web pixel, unique), `account_id` (app-generated unique ID to link events, unique), `status` (e.g., 'active', 'inactive'), `version`, `created_at`, `updated_at`.
    *   Relationship: Back-populates `Shop.extensions`.

-   **`Event` Model (`app/models/event_model.py`):**
    *   Stores individual events received from the web pixel extension.
    *   Key fields: `id` (PK), `shop_id` (FK to `shops.id`), `account_id` (FK to `extensions.account_id`), `event_name` (e.g., 'product_viewed'), `payload` (JSONB for flexible event data storage), `received_at`.
    *   Relationships: Linked to `Shop` and `Extension`.

-   **Alembic Migrations:**
    *   A migration script (`404df1d05331_create_extensions_and_events_tables.py`) was generated and manually populated to create the `extensions` and `events` tables in the database, including appropriate indexes and foreign key constraints.

### 2. Event Ingestion
-   **Endpoint:** `POST /api/v1/data/shopify/event` (defined in `app/routers/shopify_data_router.py`)
-   **Request Schema:** `WebPixelEventPayload` (defined in `app/schemas/shopify_schemas.py`), which expects `account_id`, `event_name`, and `payload`.
-   **Functionality:**
    *   Receives event data from the Shopify Web Pixel extension.
    *   Validates the incoming `account_id` by checking for a corresponding active `Extension` in the database.
    *   If a valid `Extension` is found, the event is stored in the `Event` table, linking it to the shop (via `Extension.shop_id`) and the specific `Extension` instance (via `account_id`).
-   **Rate Limiting:**
    *   Implemented using `app.utils.rate_limiter.InMemoryRateLimiter`.
    *   Applied per `account_id` at the event ingestion endpoint.
    *   Current limit: 100 requests per 60 seconds. Raises an HTTP 429 error if exceeded.

### 3. Extension Management
Endpoints are defined in `app/routers/shopify_auth_router.py`.

-   **Activate Extension:** `POST /api/v1/auth/shopify/activate-extension`
    *   **Request Schema:** `ShopifyActivateExtensionRequest` (expects `shop` domain, `access_token`, and `extension_settings` containing an `accountID`).
    *   **Functionality:**
        *   Called when a shop activates the web pixel within the app.
        *   Uses `ShopifyClient.activate_webpixel_extension(settings=...)` method (in `app/services/shopify_service.py`) to register/create the web pixel with Shopify, passing the `accountID` within the settings.
        *   Shopify returns a unique Shopify GID for the web pixel and confirms the settings.
        *   The Shopify GID and the `accountID` (from Shopify's response, parsed from a JSON string) are stored in the app's `Extension` table, associating it with the shop. The extension is marked with 'active' status and a default version (e.g., "1.0.0").
    *   **Response Schema:** `ShopifyActivateExtensionResponse` (includes `success`, `webPixel` details, `account_id`, `status`, `version`, `message`).

-   **Update Extension:** `POST /api/v1/auth/shopify/update-extension`
    *   **Request Schema:** `ShopifyActivateExtensionRequest` (expects `shop` domain, `access_token`, `extension_id` (Shopify GID of the pixel to update), and `extension_settings` containing `accountID` and other settings to update).
    *   **Functionality:**
        *   Allows updating an existing web pixel's settings via Shopify.
        *   Uses `ShopifyClient.update_extension(extension_id=..., settings=...)`.
        *   Updates the corresponding record in the `Extension` table (e.g., `version`, `shopify_extension_id` if it changes, and `status`).
    *   **Response Schema:** `ShopifyActivateExtensionResponse`.

-   **Extension Status:** `GET /api/v1/auth/shopify/extension-status?shop_domain=<shop_domain>`
    *   **Functionality:** Queries the database for the `Shop` and then the most recently updated `Extension` associated with that shop.
    *   **Response Schema:** `ExtensionStatusResponse` (returns `shop_domain`, `account_id`, `shopify_extension_id`, `status`, `version`, and a message).

### Linking Mechanism
-   The `account_id` is a crucial unique identifier.
    -   For new activations, if an `accountID` is provided in `extension_settings` by the client, it's proposed to Shopify. Shopify's response confirms the `accountID` used (which might be the one provided or one it generates if the input was missing/invalid). This confirmed `accountID` is then stored in our `Extension` model.
    -   If no `accountID` is provided during activation, `ShopifyClient.activate_webpixel_extension` generates one, passes it to Shopify, and this is then stored.
-   This `account_id` is embedded in the web pixel's settings and is expected to be included in every event payload sent from the pixel.
-   This allows events recorded in the `Event` table to be reliably tied back to a specific `Extension` instance and, consequently, to the shop that installed it.

## Part 2: Webhook Handlers

Mandatory GDPR webhooks are handled to ensure compliance. All handlers are located in `app/routers/shopify_webhooks_router.py` and are dispatched from the main `POST /webhooks` endpoint. These handlers acknowledge receipt with a 200 OK response to Shopify, with the actual data processing performed server-side.

### 1. `CUSTOMERS_DATA_REQUEST`
-   **Topic:** `customers/data_request`
-   **Handler:** `handle_customers_data_request`
-   **Logic:**
    *   Receives `customer_id` (Shopify Customer GID) and `shop_domain` from the webhook payload.
    *   Identifies the app's internal `shop_id` using the `shop_domain`.
    *   Queries the `Event` table for all events associated with that `shop_id` where the `payload` (JSONB field) contains the customer's Shopify GID. The query checks paths like `payload.customer.id`.
    *   Currently, the compiled event data (event ID, name, payload, timestamp) for the specified customer is logged. (Note: Actual data delivery to the customer/shop is an out-of-band process not directly handled by this function's immediate HTTP response).

### 2. `CUSTOMERS_REDACT`
-   **Topic:** `customers/redact`
-   **Handler:** `handle_customers_redact`
-   **Logic:**
    *   Receives `customer_id` (Shopify Customer GID), `shop_domain`, and a list of `orders_to_redact` from the payload.
    *   Identifies the app's internal `shop_id`.
    *   **Deletes all `Event` records** from the database that are associated with the `shop_id` and where the `payload` contains the specified customer's Shopify GID (checking paths like `payload.customer.id` and `payload.cart.buyerIdentity.customer.id`). The `orders_to_redact` list is logged but not currently used in the event deletion logic, as events are deleted based on customer association.
    *   Logs the redaction action, including the number of events deleted.

### 3. `SHOP_REDACT`
-   **Topic:** `shop/redact`
-   **Handler:** `handle_shop_redact`
-   **Logic:**
    *   Receives `shop_domain` from the payload.
    *   Identifies the app's internal `shop_id`.
    *   **Hard Deletes Associated Data:**
        *   Deletes all `Event` records associated with the `shop_id`.
        *   Deletes all `Extension` records associated with the `shop_id`.
    *   **Soft-Handles the `Shop` Record:**
        *   Sets the `access_token` field on the `Shop` record to `None`.
        *   Sets the `is_installed` field on the `Shop` record to `False`.
    *   Logs the shop redaction action and the counts of deleted records.

## Part 3: Webhook Registration

-   **Service Layer:**
    *   `app/services/shopify_service.py` (`ShopifyClient`):
        *   `register_webhook(topic, callback_url)`: Registers a single webhook.
        *   `get_existing_webhooks()`: Fetches currently registered webhooks for the shop, returning their ID, topic, and callback URL.
    *   `app/services/webhook_service.py`:
        *   `register_all_required_webhooks(shop_client, webhook_base_url, db_shop, db)`: Orchestrates the registration process.
-   **Required Topics:** `CUSTOMERS_DATA_REQUEST`, `CUSTOMERS_REDACT`, `SHOP_REDACT`, `APP_UNINSTALLED`.
-   **Trigger:** This registration process is automatically triggered during the OAuth callback sequence (`shopify_callback` function in `app/routers/shopify_auth_router.py`) after a shop successfully installs the app and an access token has been obtained and stored.
-   **Functionality:**
    *   The `full_callback_url` is constructed using `settings.SHOPIFY_APP_URL` and the `/webhooks` path defined in `app/main.py`.
    *   It fetches existing webhooks for the shop.
    *   For each of the `REQUIRED_TOPICS`, it checks if a webhook is already registered with the *exact* `full_callback_url`.
    *   If a required webhook is missing or misconfigured (e.g., wrong callback URL), it attempts to register it using `shop_client.register_webhook()`.
    *   The process includes logging for successful registrations, failures, and existing configurations. It specifically checks for "callbackUrl has already been taken" errors to avoid redundant error logging.
-   **`APP_UNINSTALLED` Webhook:** Added to the `REQUIRED_TOPICS` list to ensure the app is notified when a shop uninstalls it, allowing for potential cleanup if `SHOP_REDACT` is not triggered or for other administrative tasks. (Note: The handler logic for `APP_UNINSTALLED` itself was not part of this specific implementation phase but the registration is.)
