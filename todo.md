# TODO

- [X] Set up FastAPI project structure
- [X] Implement environment variables management
- [X] Create logging system
- [X] Create ShopifyClient base class
- [X] Implement Shopify OAuth flow
    - [X] Add store connection endpoint
    - [X] Build OAuth callback handler
- [X] Implement Data Fetching Endpoints
    - [X] Create product data fetcher method & endpoint
    - [X] Create order data fetcher method & endpoint
    - [X] Create transaction data fetcher method & endpoint
    - [X] Implement Customer Data Fetching (ShopifyClient method and API endpoint)
    - [X] Add pagination for Shopify API calls

---
## Next Major Phase: Backend Infrastructure & Production Readiness

- [X] **1. Database Integration & Core Models:**
    - [X] Add DB dependencies to `requirements.txt`.
    - [X] Create directory structure: `app/db/`, `app/models/`.
    - [X] Configure `DATABASE_URL` in `app/core/config.py`.
    - [X] Create `app/db/session.py` & `app/db/base.py`.
    - [X] Create `Shop` model in `app/models/shop_model.py` (domain, access_token, timestamps, etc.).
        - [X] Consolidated `access_token` field (type `Text`), removed duplicate.
    - [X] Update `app/models/__init__.py` for Alembic autodiscovery.
    - [X] **Alembic Setup & Migrations:**
        - [X] User ran `alembic init alembic`.
        - [X] `alembic/env.py` configured for async and model autodiscovery.
        - [X] `alembic.ini` configured for `sqlalchemy.url`.
        - [X] Generated and applied initial `create_shops_table` migration.
        - [X] Generated and applied `add_access_token_and_timestamps_to_shops` migration.
        - [X] Generated and applied `modify_shop_access_token_field` migration.

- [X] **2. Secure Credential & Session Management - Initial Setup:**
    - [X] Access tokens (unencrypted) stored in DB via OAuth callback.
    - [X] OAuth callback in `shopify_auth_router.py` saves token to DB.
    - [X] `SessionMiddleware` added to `app/main.py` for OAuth state handling.
    - [X] `SESSION_SECRET_KEY` and `APP_SECRET_KEY` added to `app.core.config.settings` (user to set in `.env`).
    - [X] `itsdangerous` package added for session signing.
    - [X] Temporary `temp_state_storage` removed from `shopify_auth_router.py`.
    - [X] **Added temporary logging of raw access token in OAuth callback for testing.**

- [ ] **3. Refactor Data Routers & Implement Token Encryption (CRITICAL NEXT STEPS):**
    - [ ] **Refactor `shopify_data_router.py`:** Update to retrieve access tokens from the DB based on `shop_domain` instead of expecting them in request bodies. (HIGH PRIORITY)
    - [ ] **Implement Access Token Encryption:** Encrypt tokens in `Shop` model before DB save and decrypt after fetch using `APP_SECRET_KEY`. (HIGH PRIORITY)
        - This will likely require another Alembic migration if the field name/type changes, or a data migration to encrypt existing tokens.

- [ ] **4. Shopify Webhook Enhancements (Depends on 1, 2, 3):**
    - [~] Implement Shopify Webhook Handling (Mandatory for Shopify Apps) - IN PROGRESS
        - [X] Basic webhook endpoint setup (`/webhooks`) and HMAC verification.
        - [ ] Implement actual handler logic for `CUSTOMERS_DATA_REQUEST` (dependent on DB & token retrieval).
        - [ ] Implement actual handler logic for `CUSTOMERS_REDACT` (dependent on DB & token retrieval).
        - [ ] Implement actual handler logic for `SHOP_REDACT` (dependent on DB & token retrieval).
        - [ ] Implement webhook registration logic (e.g., after OAuth, using Admin API).

- [ ] **5. Implement Robust Logging:**
    - [ ] Uncomment and enhance logging statements throughout the application (e.g., in `ShopifyClient`, data routers, webhook handlers).

- [ ] **6. Asynchronous Task Processing (Depends on 1, useful for 4):**
    - [ ] Set up Celery and a message broker (e.g., Redis or RabbitMQ).
    - [ ] Refactor webhook handler logic to use Celery tasks for any long-running processing.

- [ ] **7. API Authentication (Self-Hosted Endpoints):**
    - [~] Set up API authentication # PARTIALLY DONE: Shopify OAuth implemented.
    - [ ] Review and implement API authentication for own API endpoints if needed (e.g., JWTs if frontend calls these directly).

- [ ] **8. Caching Strategy (Can use Redis from 6):**
    - [ ] Evaluate and implement caching (e.g., using Redis) for frequently accessed data.

---
## GitHub Preparation:
- [X] `.gitignore` file created/verified.
- [X] `.env.example` file created/verified (user to create manually if tool blocked).
- [X] `README.md` created.

---
## Production Readiness Checklist

- [ ] **Security:**
    - [ ] Remove `verify=False` from `ShopifyClient` (ensure proper SSL verification).
    - [X] Access tokens stored encrypted in DB (Pending implementation - see step 3).
    - [X] Strong `APP_SECRET_KEY` and `SESSION_SECRET_KEY` in use (User configured in `.env`).
    - [ ] Restrict CORS policy in `app/main.py` for production.
- [ ] **Operations:**
    - [ ] Ensure FastAPI debug mode is OFF in production.
    - [ ] Configure production-level logging (level, format, output).
    - [ ] Pin all dependency versions in `requirements.txt` before deploying to production.
    - [ ] Verify Shopify Partner App Configuration (App URL, Redirection URLs, Webhook URLs) for production environment.

## Current Status & Important Notes (as of 2025-05-16 - Refer to notes.md for more detail):

- Core Data APIs (Products, Orders, Transactions, Customers) are functional.
- Basic Webhook Receiver is functional.
- **Foundation for Database/ORM integration has been laid out in code (files created, initial models defined).**
- **Next steps require USER ACTION to set up local PostgreSQL, configure .env, and run Alembic commands.**
- Local SSL verification (`verify=False`) is a known workaround.
- OAuth state storage is temporary.