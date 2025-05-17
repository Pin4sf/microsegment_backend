# TODO

[X] Set up FastAPI project structure - DONE
[ ] Configure database connection and schema - NOT DONE (Placeholders for DATABASE_URL exist in config.py but no actual DB integration like SQLAlchemy, models, or Alembic migrations are present.)
[X] Implement environment variables management - DONE (via pydantic-settings and .env)
[X] Create logging system - DONE (Basic logging is in place)
[ ] Set up API authentication - PARTIALLY DONE/IN PROGRESS.
The Shopify OAuth flow (which is a form of authentication/authorization for accessing Shopify data) is implemented.
However, the term "API authentication" might also imply securing your API endpoints themselves (e.g., requiring a JWT or API key to call your /api/data/... endpoints, even if you have a Shopify access token). This part doesn't seem to be implemented yet. Your data endpoints currently rely on the client sending the correct Shopify shop and access_token in the request body.
[X] Create ShopifyClient base class - DONE
[X] Implement Shopify OAuth flow - DONE (Core logic is present)
[X] Add store connection endpoint - DONE (/api/auth/shopify/connect)
[X] Build OAuth callback handler - DONE (/api/auth/shopify/callback)
[ ] Implement credential secure storage - NOT DONE/MINIMALLY ADDRESSED.
The ShopifyClient stores the access_token in an instance variable if exchange_code_for_token is called.
However, there's no persistent, secure storage (like a database with encryption, or a secure vault) for these access tokens. If the app restarts, obtained tokens are lost. The SECRET_KEY in config.py is commented out, suggesting encryption features are not yet active.
[X] Create product data fetcher method - DONE
[X] Create order data fetcher method - DONE
[X] Create transaction data fetcher method - DONE
[X] Add pagination for Shopify API calls - DONE (Basic cursor-based pagination is implemented)
[X] Implement Customer Data Fetching (ShopifyClient method and API endpoint) - DONE
[~] Implement Shopify Webhook Handling - IN PROGRESS (Foundation laid, handlers pending)
    [X] Basic webhook endpoint setup (e.g., /webhooks) and HMAC verification - DONE
    [ ] Handler for CUSTOMERS_DATA_REQUEST webhook - PENDING
    [ ] Handler for CUSTOMERS_REDACT webhook - PENDING
    [ ] Handler for SHOP_REDACT webhook - PENDING
[ ] Integrate a robust database solution (e.g., PostgreSQL with SQLAlchemy and Alembic for migrations) - REFINES EXISTING
[ ] Implement server-side session management for OAuth state parameter (e.g., using Redis or database-backed sessions) - NEW (To replace insecure temp_state_storage)
[ ] Set up Celery for asynchronous background tasks (e.g., for long-running webhook processing) - NEW
[ ] Evaluate and implement caching strategy (e.g., using Redis) for frequently accessed data - NEW

## Summary of Completion:

### Completed Tasks:

- FastAPI project structure
- Environment variables management
- Basic logging system
- ShopifyClient base class
- Core Shopify OAuth flow (connect and callback logic)
- Product, order, and transaction data fetcher methods
- Basic pagination for Shopify API calls

### Partially Done/In Progress:

- API Authentication: Shopify OAuth is there, but authentication for your own API endpoints (if planned beyond just passing Shopify tokens) is not.

### Not Done/Pending:

- Database Connection and Schema: No database integration yet. Needs ORM (e.g., SQLAlchemy), models, and migrations (e.g., Alembic).
- Credential Secure Storage: Access tokens are not stored securely or persistently. Requires database storage with encryption.
- Shopify Webhook Handling: Essential for app lifecycle and privacy compliance. Foundation (routing, HMAC) is DONE. Specific handlers (CUSTOMERS_DATA_REQUEST, CUSTOMERS_REDACT, SHOP_REDACT) are PENDING.
- Server-side OAuth State Management: Current temporary dictionary is not suitable for production.
- Background Task Processing: No system like Celery for handling asynchronous tasks.
- Caching Strategy: No caching mechanism in place.

### Other Important Notes:

- SSL Verification (verify=False): You're currently using verify=False in ShopifyClient to bypass SSL certificate verification issues. This is acceptable for local development to get unblocked but is a security risk for production. The underlying CA certificate issue in your Windows environment should be addressed eventually to allow secure SSL verification.

- Error Handling in ShopifyClient: The make_graphql_request and exchange_code_for_token methods have try-except blocks that log errors but often return None. The calling code in the routers (e.g., _handle_shopify_request) then tries to interpret this, sometimes raising an HTTPException. This is okay, but ensure the error propagation and client responses are robust and informative for all failure cases.

- Shopify Partner App Configuration: You still need to configure the "App URL" and "Allowed redirection URL(s)" in your Shopify Partner Dashboard using your ngrok URL to fully test the OAuth flow end-to-end (i.e., having Shopify redirect back to your /callback handler).

- State Parameter (CSRF Protection): The get_authorize_url generates a state parameter. Your /callback endpoint validates this state. However, the storage mechanism for the state (`temp_state_storage` in `shopify_auth_router.py`) is temporary and insecure, suitable only for local testing.

### Local Development Workarounds vs. Production Readiness:

- **SSL Verification (`verify=False` in `ShopifyClient`):**
    - **Local:** Currently used to bypass local Windows CA certificate issues when `httpx` calls Shopify.
    - **Production:** MUST be removed. Implement proper SSL certificate verification. Options include:
        - Using `certifi` to provide a reliable CA bundle (as hinted by commented-out code in `ShopifyClient`).
        - Resolving the underlying CA certificate issue in the deployment environment.
        - Secure communication with Shopify is non-negotiable.

- **OAuth State Storage (`temp_state_storage` in `shopify_auth_router.py`):**
    - **Local:** An in-memory dictionary is used to store the `state` parameter for CSRF protection during OAuth.
    - **Production:** This is insecure and will not work with multiple server instances. Replace with a robust server-side session management solution:
        - **Redis:** Fast, distributed cache suitable for session data.
        - **Database-backed sessions:** Store session data in your primary database.

- **Access Token Storage & Handling:**
    - **Local:** Access tokens obtained via OAuth are stored in the `ShopifyClient` instance's memory (lost on app restart) and returned in the callback response for immediate use by a test client.
    - **Production:**
        - Tokens MUST be stored securely and persistently on the server-side (e.g., in the database, encrypted at rest).
        - Do NOT routinely expose the raw access token to the client-side after the OAuth flow. Manage sessions or use secure, httpOnly cookies if frontend needs to make authenticated calls *through your backend*.
        - Your API endpoints (`/api/data/shopify/*`) currently expect the access token in the request body. This might be acceptable if calls are from a trusted backend client, but for browser-based clients, this is risky if the token was exposed. Consider if these endpoints need their own auth layer (JWT, session-based) if they are to be called directly by end-users' browsers.

- **`SECRET_KEY` (in `app/core/config.py`):**
    - **Local:** Currently commented out.
    - **Production:** Generate a strong, unique `SECRET_KEY` (e.g., using `openssl rand -hex 32`). This key is vital for:
        - Encrypting sensitive data (like stored access tokens).
        - Signing session cookies or JWTs if you implement such authentication.
        - FastAPI/Starlette uses it for signing cookies.

- **CORS Policy (`app/main.py`):**
    - **Local:** `allow_origins=["*"]` (allows all origins) is used for ease of development.
    - **Production:** Restrict `allow_origins` to the specific domain(s) of your frontend application. Do not use `"*"` in production.

- **Error Handling & Debugging:**
    - **Local:** Detailed error messages can be helpful.
    - **Production:** Ensure FastAPI's debug mode is OFF. Avoid leaking sensitive error details to the client. Configure robust logging for production to capture necessary information for troubleshooting.

- **Logging Configuration (`app/core/logging_config.py`):**
    - **Local:** Basic console logging is in place.
    - **Production:** Configure appropriate logging levels (e.g., INFO or WARNING). Consider structured logging and sending logs to a file or a centralized logging service (e.g., ELK stack, Datadog, Sentry for errors).

- **Dependencies (`requirements.txt`):**
    - **Local:** May have flexible versions.
    - **Production:** Pin all dependency versions in `requirements.txt` (e.g., `package==1.2.3`) to ensure reproducible builds and avoid unexpected updates.

To check the Shopify Data endpoints use the following access_token because this have all the permissions enabled our requested callback access_token is temperory so it will not work for all the endpoints.


For products endpoint
{
  "shop": "teststorshivansh.myshopify.com",
  "access_token": "shpat_YOUR_EXAMPLE_ACCESS_TOKEN_HERE",
  "custom_query": "snowboard",
  "cursor": null,
  "first": 10
}

For orders endpoint
    {
      "shop": "teststorshivansh.myshopify.com",
      "access_token": "shpat_YOUR_EXAMPLE_ACCESS_TOKEN_HERE",
      "first": 10,
      "cursor": null,
      "custom_query": null
    }
    {
      "shop": "teststorshivansh.myshopify.com",
      "access_token": "shpat_YOUR_EXAMPLE_ACCESS_TOKEN_HERE",
      "first": 10,
      "cursor": null,
      "custom_query": "financial_status:paid"
    }

For customers endpoint
      {
      "shop": "teststorshivansh.myshopify.com",
      "access_token": "shpat_YOUR_EXAMPLE_ACCESS_TOKEN_HERE",
      "first": 10,
      "cursor": null
    }

    For transactions endpoint

  {
  "shop": "teststorshivansh.myshopify.com",
  "access_token": "shpat_YOUR_EXAMPLE_ACCESS_TOKEN_HERE",
  "custom_query": null,
  "cursor": null,
  "first": 5,
  "order_id": "gid://shopify/Order/6460998287582"
    }

# Project Notes & Status

## Recent Developments (as of latest update)

- **Database Integration & OAuth Flow:**
    - `Shop` model updated: `access_token` field consolidated (now `Text`), `encrypted_access_token` removed, `is_installed` defaults to `True`, `updated_at` has `server_default`.
    - Alembic migration `modify_shop_access_token_field` generated and applied.
    - OAuth callback in `shopify_auth_router.py` now stores the (currently raw) `access_token` in the DB.
    - **Temporary logging of raw access token added to OAuth callback for easier testing (`logger.warning`).**
- **Session Management:**
    - `SessionMiddleware` configured in `app/main.py`.
    - `SESSION_SECRET_KEY` and `APP_SECRET_KEY` added to `app.core.config.settings` (user must set in `.env`).
    - `itsdangerous` package added to `requirements.txt` for secure session signing.
    - Old `temp_state_storage` dictionary removed from `shopify_auth_router.py`.
- **GitHub Preparation:**
    - `.gitignore` file created/verified (user to ensure it's present and correct).
    - `.env.example` file content provided (user to create manually if tool blocked).
    - Comprehensive `README.md` created.

## Current Status & Important Notes

- **Core Data APIs (Products, Orders, etc.):** Functional but still expect `access_token` in request body. **Needs URGENT refactor.**
- **Webhook Receiver:** Basic HMAC verification and dispatch in place. Handlers are placeholders.
- **Database:** PostgreSQL with `Shop` model is live. Migrations are up-to-date with current model structure.
- **Shopify OAuth Flow:** Functional, using DB for token storage and sessions for state. Raw token is logged for testing.
- **SSL Verification:** `verify=False` in `ShopifyClient` is a known local dev workaround. **MUST be fixed for production.**
- **Logging:** Basic logging infrastructure is present. More specific logging statements (especially for errors and info) need to be uncommented/added throughout the codebase.

## Detailed Next Steps & Priorities for Development Team:

1.  **Refactor `shopify_data_router.py` (HIGH PRIORITY):**
    *   **Goal:** Modify all data fetching endpoints (and the `_handle_shopify_request` helper) to retrieve the `access_token` from the `shops` database table based on the `shop_domain` provided in the request.
    *   **Action:**
        1.  Inject `db: AsyncSession = Depends(get_db)` into `_handle_shopify_request` (or directly into endpoints if not using the helper for everything).
        2.  Remove `access_token` from the `ShopifyDataRequest` Pydantic model in `app/schemas/shopify_schemas.py`.
        3.  In `_handle_shopify_request`, query the `Shop` table for the given `shop_domain` to get the `access_token`.
        4.  Handle cases where the shop is not found or has no token (raise `HTTPException`).
        5.  Instantiate `ShopifyClient` using the fetched token.
        6.  (Later) When token encryption is implemented, this logic will also decrypt the token.

2.  **Implement Access Token Encryption (HIGH PRIORITY):**
    *   **Goal:** Securely store access tokens in the database.
    *   **Action:**
        1.  Ensure `APP_SECRET_KEY` is set in `.env` (from `app/core/config.py`).
        2.  Choose and implement an encryption/decryption utility (e.g., using the `cryptography` library with Fernet).
        3.  In `app/routers/shopify_auth_router.py` (OAuth callback), **encrypt** the `access_token` *before* saving it to `db_shop.access_token`.
        4.  In `app/routers/shopify_data_router.py` (once refactored), **decrypt** the `access_token` after fetching it from the database and *before* passing it to `ShopifyClient`.
        5.  **Note:** Since the `access_token` column in `Shop` model is already `Text`, no schema change (and thus no Alembic migration for the column type itself) might be immediately needed if you encrypt existing raw tokens. However, if you have existing raw tokens, you'll need a strategy (e.g., a data migration script or re-installations) to encrypt them.

3.  **Implement Robust Logging:**
    *   Go through `shopify_auth_router.py`, `shopify_data_router.py`, `shopify_service.py`, and `shopify_webhooks_router.py`.
    *   Uncomment existing `logger.info`, `logger.error`, `logger.debug` statements.
    *   Use `logger.exception()` in `except` blocks where full tracebacks are useful.
    *   Add more informative log messages where appropriate to trace execution flow and errors.

4.  **Complete Webhook Handlers (`shopify_webhooks_router.py`):**
    *   Implement the actual logic for `handle_customers_data_request`, `handle_customers_redact`, and `handle_shop_redact`.
    *   This will involve database interaction (fetching/deleting data) and potentially using the `ShopifyClient` (which first needs the data router refactor to easily get tokens).

5.  **Implement Webhook Registration:**
    *   After successful OAuth, use the obtained access token to make an API call to Shopify to register the necessary webhooks (GDPR, app uninstalled, etc.). This could be a new function in `ShopifyClient` or `shopify_utils.py` and called at the end of the OAuth callback.

6.  **Address SSL Verification for Production:**
    *   In `app/services/shopify_service.py`, remove `verify=False` from `httpx.AsyncClient` calls.
    *   Ensure `certifi` is used (e.g., `ssl_context = ssl.create_default_context(cafile=certifi.where())` and pass `verify=ssl_context`). Add `certifi` to `requirements.txt` if not already a sub-dependency.

## For Team Members Getting Started:

*   Follow the `README.md` for initial project setup.
*   **Manually create your `.gitignore` and `.env.example` files if they were not created by the AI assistant, using the content previously provided.** Ensure your actual `.env` is configured and **not committed.**
*   The `SHOPIFY_APP_URL` and `SHOPIFY_REDIRECT_URI` in your `.env` will need to point to your ngrok instance for local OAuth testing.
*   The raw access token from Shopify is currently logged with `logger.warning` in the OAuth callback for testing. This is temporary.
*   Focus on tasks 1 & 2 above (Data Router Refactor & Token Encryption) as they are critical for security and proper functioning of other parts of the app.

--- (Older notes sections can be reviewed for historical context if needed)
