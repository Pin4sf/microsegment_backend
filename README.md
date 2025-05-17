# Micro Segment Shopify App Backend

This project is the FastAPI backend for a Shopify application designed for micro-segmentation tasks. It handles Shopify OAuth, data fetching via GraphQL, webhook processing, and database interactions.

## Project Status

- **Core Functionality:** Shopify OAuth flow, database integration (PostgreSQL with SQLAlchemy & Alembic), and basic data fetching endpoints (Products, Orders, Transactions, Customers) are implemented.
- **Webhook Handling:** Basic infrastructure for receiving and verifying webhooks is in place. Handler logic for `CUSTOMERS_DATA_REQUEST`, `CUSTOMERS_REDACT`, and `SHOP_REDACT` GDPR webhooks are currently placeholders and need to be implemented.
- **Authentication:** Shopify OAuth is implemented for app installation. Access tokens are stored in the database.
- **Next Steps:** Key priorities include refactoring data fetching to use database-stored tokens, implementing access token encryption, and completing webhook handler logic.

Refer to `todo.md` and `notes.md` for a detailed breakdown of completed tasks, pending items, and project architecture notes.

## Features

- Shopify OAuth 2.0 for app installation and authentication.
- Secure HMAC validation for OAuth and Webhooks.
- Session-based state management for CSRF protection during OAuth.
- PostgreSQL database integration using SQLAlchemy (async) and Alembic for migrations.
- Storage of shop information and access tokens.
- API endpoints to fetch Shopify data (Products, Orders, Transactions, Customers) using GraphQL.
- Basic webhook receiver for GDPR and other Shopify events.
- Structured logging.
- Environment-based configuration using Pydantic.

## Prerequisites

- Python 3.11+
- PostgreSQL server
- Ngrok (or similar tunneling service) for local development and Shopify webhook/callback testing.

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd bend # Or your project directory name
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up PostgreSQL Database:**
    - Ensure your PostgreSQL server is running.
    - Create a dedicated database and user for this application.
      For example, using `psql` or pgAdmin:
      ```sql
      CREATE DATABASE microsegment_app_db;
      CREATE USER microsegment_user WITH PASSWORD 'your_strong_password';
      GRANT ALL PRIVILEGES ON DATABASE microsegment_app_db TO microsegment_user;
      ```

5.  **Configure Environment Variables:**
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Edit the `.env` file and fill in your actual values for:
        - `SHOPIFY_API_KEY`
        - `SHOPIFY_API_SECRET`
        - `SHOPIFY_APP_SCOPES` (e.g., `read_products,read_orders,read_customers`)
        - `SHOPIFY_APP_URL` (your ngrok HTTPS URL for local dev, e.g., `https://your-id.ngrok.io`)
        - `SHOPIFY_REDIRECT_URI` (your ngrok HTTPS URL + `/api/v1/auth/callback`, e.g., `https://your-id.ngrok.io/api/v1/auth/callback`)
        - `APP_SECRET_KEY` (generate a strong random string, e.g., `openssl rand -hex 32`)
        - `SESSION_SECRET_KEY` (generate a strong random string, e.g., `openssl rand -hex 32`)
        - `DATABASE_URL` (e.g., `postgresql+asyncpg://microsegment_user:your_strong_password@localhost:5432/microsegment_app_db`)

6.  **Run Database Migrations:**
    - Ensure your `.env` file is configured with the correct `DATABASE_URL`.
    - `alembic.ini` should be configured to use this URL (typically `sqlalchemy.url` for synchronous operations, while `env.py` uses the async URL from settings for online mode).
    ```bash
    alembic upgrade head
    ```

7.  **Shopify Partner Dashboard Setup:**
    - Go to your app's settings in your Shopify Partner Dashboard.
    - Set **App URL** to your `SHOPIFY_APP_URL` from the `.env` file.
    - Add your `SHOPIFY_REDIRECT_URI` from the `.env` file to the **Allowed redirection URL(s)** list.
    - Configure webhook subscriptions as needed (e.g., for GDPR topics, pointing to `SHOPIFY_APP_URL/webhooks`).

8.  **Run the Application (Local Development):**
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
    The application will be available at `http://127.0.0.1:8000`.
    Your Shopify app will interact with it via the ngrok URL.

## Project Structure

```
.env.example        # Example environment variables
.gitignore          # Specifies intentionally untracked files that Git should ignore
alembic/            # Alembic migration scripts and configuration
alembic.ini         # Alembic configuration file
app/
├── __init__.py
├── core/             # Core application settings, logging
│   ├── __init__.py
│   ├── config.py
│   └── logging_config.py
├── db/               # Database session management, base model
│   ├── __init__.py
│   ├── base.py
│   └── session.py
├── models/           # SQLAlchemy ORM models
│   ├── __init__.py
│   └── shop_model.py
├── routers/          # API endpoint definitions (FastAPI routers)
│   ├── __init__.py
│   ├── shopify_auth_router.py
│   ├── shopify_data_router.py
│   └── shopify_webhooks_router.py
├── schemas/          # Pydantic schemas for data validation and serialization
│   ├── __init__.py
│   └── shopify_schemas.py
├── services/         # Business logic, external service clients
│   ├── __init__.py
│   └── shopify_service.py
├── utils/            # Utility functions
│   ├── __init__.py
│   ├── shopify_utils.py
│   └── webhook_utils.py
└── main.py           # FastAPI application entry point
notes.md            # Project notes, architecture decisions, etc.
requirements.txt    # Python package dependencies
todo.md             # Task tracking for project development
```

## Key Technologies

- FastAPI
- SQLAlchemy (with asyncpg for async PostgreSQL)
- Alembic (for database migrations)
- Pydantic (for data validation and settings management)
- Uvicorn (ASGI server)
- HTTPretty (for testing external HTTP calls - if implemented)
- Pytest (for testing - if implemented)

## Next Steps / Contribution Areas

- **Refactor Data Routers:** Update `shopify_data_router.py` to fetch access tokens from the database instead of expecting them in request bodies.
- **Implement Access Token Encryption:** Encrypt access tokens before storing them in the `Shop` model and decrypt when retrieved.
- **Complete Webhook Handlers:** Implement the logic for the placeholder `CUSTOMERS_DATA_REQUEST`, `CUSTOMERS_REDACT`, and `SHOP_REDACT` webhook handlers in `app/routers/shopify_webhooks_router.py`.
- **Implement Webhook Registration:** Add logic to register necessary webhooks with Shopify after app installation.
- **Resolve SSL Verification:** Remove `verify=False` from `ShopifyClient` and ensure proper SSL verification for production.
- **Implement Robust Logging:** Uncomment and enhance logging statements throughout the application.

Refer to `todo.md` and `notes.md` for more details. 