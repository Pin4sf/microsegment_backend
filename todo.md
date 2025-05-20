# TODO

- [x] Set up FastAPI project structure
- [x] Implement environment variables management
- [x] Create logging system
- [x] Create ShopifyClient base class
- [x] Implement Shopify OAuth flow
  - [x] Add store connection endpoint
  - [x] Build OAuth callback handler
- [x] Implement Data Fetching Endpoints
  - [x] Create product data fetcher method & endpoint
  - [x] Create order data fetcher method & endpoint
  - [x] Create transaction data fetcher method & endpoint
  - [x] Implement Customer Data Fetching (ShopifyClient method and API endpoint)
  - [x] Add pagination for Shopify API calls

---

## Next Major Phase: Backend Infrastructure & Production Readiness

- [x] **1. Database Integration & Core Models:**
  - [x] Add DB dependencies to `requirements.txt`.
  - [x] Create directory structure: `app/db/`, `app/models/`.
  - [x] Configure `DATABASE_URL` in `app/core/config.py`.
  - [x] Create `app/db/session.py` & `app/db/base.py`.
  - [x] Create `Shop` model in `app/models/shop_model.py` (domain, access_token, timestamps, etc.).
    - [x] Consolidated `access_token` field (type `Text`), removed duplicate.
  - [x] Update `app/models/__init__.py` for Alembic autodiscovery.
  - [x] **Alembic Setup & Migrations:**
    - [x] User ran `alembic init alembic`.
    - [x] `alembic/env.py` configured for async and model autodiscovery.
    - [x] `alembic.ini` configured for `sqlalchemy.url`.
    - [x] Generated and applied initial `create_shops_table` migration.
    - [x] Generated and applied `add_access_token_and_timestamps_to_shops` migration.
    - [x] Generated and applied `modify_shop_access_token_field` migration.

- [x] **2. Secure Credential & Session Management - Initial Setup:**
  - [x] Access tokens (unencrypted) stored in DB via OAuth callback.
  - [x] OAuth callback in `shopify_auth_router.py` saves token to DB.
  - [x] `SessionMiddleware` added to `app/main.py` for OAuth state handling.
  - [x] `SESSION_SECRET_KEY` and `APP_SECRET_KEY` added to `app.core.config.settings` (user to set in `.env`).
  - [x] `itsdangerous` package added for session signing.
  - [x] Temporary `temp_state_storage` removed from `shopify_auth_router.py`.
  - [x] **Added temporary logging of raw access token in OAuth callback for testing.**

- [ ] **3. Web Pixel Extension Integration (NEW HIGH PRIORITY):**
  - [ ] **Database Schema Updates:**
    - [ ] Create `Extension` model to track extension status and settings
    - [ ] Add relationship between `Shop` and `Extension` models
    - [ ] Create Alembic migration for new extension-related tables
  - [ ] **Event Processing:**
    - [ ] Create `Event` model for storing customer activity data
    - [ ] Implement event validation and sanitization
    - [ ] Add rate limiting for event ingestion
    - [ ] Set up event processing pipeline
  - [ ] **Extension Management:**
    - [ ] Update `activate-extension` endpoint to store extension info in DB
    - [ ] Add endpoint to check extension status
    - [ ] Implement extension deactivation handling
    - [ ] Add version tracking for extension updates

- [ ] **4. Refactor Data Routers & Implement Token Encryption (CRITICAL):**
  - [ ] **Refactor `shopify_data_router.py`:**
    - [ ] Update to retrieve access tokens from the DB based on `shop_domain`
    - [ ] Remove `access_token` from request bodies
    - [ ] Add proper error handling for missing/invalid tokens
  - [ ] **Implement Access Token Encryption:**
    - [ ] Add encryption/decryption utilities
    - [ ] Encrypt tokens before DB storage
    - [ ] Decrypt tokens when retrieved
    - [ ] Create data migration for existing tokens

- [ ] **5. Shopify Webhook Enhancements:**
  - [~] Implement Shopify Webhook Handling (Mandatory for Shopify Apps) - IN PROGRESS
    - [x] Basic webhook endpoint setup (`/webhooks`) and HMAC verification
    - [ ] Implement handler logic for `CUSTOMERS_DATA_REQUEST`
    - [ ] Implement handler logic for `CUSTOMERS_REDACT`
    - [ ] Implement handler logic for `SHOP_REDACT`
    - [ ] Implement webhook registration logic
    - [ ] Add app uninstallation handling

- [ ] **6. Implement Robust Logging:**
  - [ ] Uncomment and enhance logging statements throughout the application
  - [ ] Add structured logging for better analysis
  - [ ] Implement log rotation and retention policies
  - [ ] Add monitoring and alerting setup

- [ ] **7. Asynchronous Task Processing:**
  - [ ] Set up Celery and message broker (Redis/RabbitMQ)
  - [ ] Move webhook processing to background tasks
  - [ ] Add event processing queue for Web Pixel events
  - [ ] Implement task monitoring and error handling

- [ ] **8. API Authentication & Security:**
  - [~] Set up API authentication (PARTIALLY DONE: Shopify OAuth implemented)
  - [ ] Implement JWT or session-based auth for own endpoints
  - [ ] Add rate limiting for all endpoints
  - [ ] Implement proper CORS policies
  - [ ] Remove `verify=False` from `ShopifyClient`

- [ ] **9. Caching Strategy:**
  - [ ] Set up Redis for caching
  - [ ] Implement caching for frequently accessed data
  - [ ] Add cache invalidation strategies
  - [ ] Monitor cache performance

---

## Production Readiness Checklist

- [ ] **Security:**
  - [ ] Remove `verify=False` from `ShopifyClient`
  - [ ] Implement access token encryption
  - [ ] Configure proper CORS policies
  - [ ] Set up rate limiting
  - [ ] Implement proper error handling and logging
- [ ] **Operations:**
  - [ ] Configure production logging
  - [ ] Set up monitoring and alerting
  - [ ] Pin dependency versions
  - [ ] Configure proper SSL/TLS
  - [ ] Set up backup and recovery procedures
- [ ] **Documentation:**
  - [ ] Complete API documentation
  - [ ] Add deployment guide
  - [ ] Create troubleshooting guide
  - [ ] Document extension setup process

## Current Status & Important Notes:

- Core Data APIs are functional but need refactoring for DB token retrieval
- Web Pixel Extension infrastructure is in place but needs DB integration
- Basic webhook receiver is functional but handlers need implementation
- Database foundation is laid but needs extension-related models
- Local SSL verification workaround needs to be addressed
- OAuth state storage is now using sessions but needs production hardening