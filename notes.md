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

## Project Overview
This is a FastAPI-based backend service for Shopify integration, handling OAuth authentication, data fetching, webhook processing, and web pixel extension management.

## Core Components

### 1. Authentication & Authorization
- **OAuth Flow Implementation**
  - ✅ Store connection endpoint (`/api/auth/shopify/connect`)
  - ✅ OAuth callback handler (`/api/auth/shopify/callback`)
  - ✅ Basic session management with FastAPI's SessionMiddleware
  - ⚠️ Need to migrate to Redis for better scalability and security

### 2. Database Integration
- **Models**
  - ✅ Shop model with access token storage
  - ✅ Extension model for web pixel tracking
  - ✅ Event model for customer activity
  - ✅ Proper foreign key relationships

- **Migrations**
  - ✅ Initial schema setup
  - ✅ Extensions and events tables
  - ✅ Indexes for performance optimization

### 3. Data Fetching
- **ShopifyClient Implementation**
  - ✅ Product data fetcher
  - ✅ Order data fetcher
  - ✅ Transaction data fetcher
  - ✅ Customer data fetcher
  - ✅ Pagination support
  - ⚠️ SSL verification disabled (needs fix)

### 4. Webhook System
- **Infrastructure**
  - ✅ Basic webhook endpoint
  - ✅ HMAC verification
  - ✅ Basic webhook task structure
  - ⚠️ Missing GDPR handlers
  - ⚠️ Missing app uninstallation handler

### 5. Web Pixel Extension
- **Features**
  - ✅ Extension model
  - ✅ Event tracking structure
  - ✅ Basic extension activation
  - ⚠️ Event processing pipeline pending
  - ⚠️ Rate limiting needed

### 6. Asynchronous Processing
- **Celery Setup**
  - ✅ Basic Celery configuration
  - ✅ Redis as message broker
  - ✅ Windows-specific settings
  - ✅ Basic task structure
  - ✅ Flower monitoring setup
  - ⚠️ Task retry logic needed
  - ⚠️ Task error handling needed

### 7. Caching System
- **Redis Implementation**
  - ✅ Redis server setup
  - ✅ Basic caching decorator
  - ✅ Connection pooling
  - ✅ Redis connection for session management (pending implementation)
  - ⚠️ Cache invalidation needed
  - ⚠️ Performance monitoring needed

## Technical Details

### Environment Configuration
```env
# Required Environment Variables
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_SECRET=your_api_secret
SHOPIFY_APP_URL=your_app_url
SHOPIFY_REDIRECT_URI=your_redirect_uri
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
SESSION_SECRET_KEY=your_session_key
APP_SECRET_KEY=your_app_key
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### API Endpoints

#### Authentication
- `POST /api/auth/shopify/connect`
  - Initiates OAuth flow
  - Generates state parameter
  - Stores state in session cookie (to be migrated to Redis)
  - Redirects to Shopify

- `GET /api/auth/shopify/callback`
  - Handles OAuth callback
  - Verifies state from session cookie (to be migrated to Redis)
  - Exchanges code for token
  - Stores access token in database
  - Creates/updates shop record

#### Data Fetching
- `POST /api/data/shopify/products`
  - Fetches product data
  - Supports pagination
  - Accepts custom queries

- `POST /api/data/shopify/orders`
  - Fetches order data
  - Supports filtering
  - Includes pagination

- `POST /api/data/shopify/customers`
  - Fetches customer data
  - Supports pagination

- `POST /api/data/shopify/transactions`
  - Fetches transaction data
  - Requires order ID
  - Supports pagination

#### Webhooks
- `POST /webhooks`
  - Handles all Shopify webhooks
  - Verifies HMAC signature
  - Routes to appropriate handlers
  - Processes in background using Celery

#### Extension Management
- `POST /api/auth/shopify/activate-extension`
  - Creates web pixel extension
  - Generates unique account ID

- `POST /api/auth/shopify/update-extension`
  - Updates existing extension
  - Manages version control

## Known Issues & Workarounds

### 1. Session Management
- **Current State**: Using FastAPI's SessionMiddleware with cookies
- **Issue**: Not scalable for multiple server instances
- **Workaround**: Using session cookies for development
- **Fix Required**: Migrate to Redis-based session management

### 2. SSL Verification
- **Issue**: SSL verification disabled in `ShopifyClient`
- **Workaround**: Using `verify=False` in development
- **Fix Required**: Implement proper SSL certificate verification

### 3. Access Token Storage
- **Issue**: Raw tokens stored in database
- **Workaround**: Temporary logging for testing
- **Fix Required**: Implement encryption using `APP_SECRET_KEY`

### 4. CORS Configuration
- **Issue**: All origins allowed in development
- **Workaround**: Using `allow_origins=["*"]`
- **Fix Required**: Restrict to specific domains in production

### 5. Windows-specific Celery Issues
- **Issue**: Permission errors with default pool
- **Workaround**: Using `--pool=solo` and `FORKED_BY_MULTIPROCESSING=1`
- **Fix Required**: Consider using Docker for production

## Development Guidelines

### 1. Code Style
- Use type hints consistently
- Follow FastAPI best practices
- Add comprehensive docstrings
- Include error handling

### 2. Testing
- Test all webhook handlers
- Verify extension functionality
- Check security measures
- Validate data integrity

### 3. Security
- Never log sensitive data
- Use environment variables
- Implement proper encryption
- Follow OWASP guidelines

### 4. Performance
- Use async/await properly
- Implement caching where needed
- Monitor database queries
- Optimize API calls

## Production Readiness Checklist

### Security
- [ ] Enable SSL verification
- [ ] Implement token encryption
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Migrate session management to Redis

### Monitoring
- [ ] Configure production logging
- [ ] Set up error tracking
- [ ] Implement performance monitoring
- [ ] Add health checks

### Infrastructure
- [ ] Set up backup procedures
- [ ] Configure load balancing
- [ ] Implement caching
- [ ] Set up CI/CD

### Documentation
- [ ] Complete API documentation
- [ ] Add deployment guide
- [ ] Create troubleshooting guide
- [ ] Document security measures

## Next Steps

### High Priority
1. Migrate session management to Redis
2. Implement webhook handlers for GDPR compliance
3. Add app uninstallation handler
4. Set up event processing pipeline
5. Implement token encryption

### Medium Priority
1. Add rate limiting using Redis
2. Configure CORS policies
3. Implement caching for Shopify API responses
4. Add task monitoring with Flower
5. Implement webhook retry mechanism

### Low Priority
1. Add comprehensive logging
2. Set up monitoring
3. Create deployment documentation
4. Add performance optimizations
5. Implement API key authentication

Todo as per (20th may 2025 23:00pm)

# TODO

## High Priority

1. **Web Pixel Extension Integration**
   - [ ] Create Extension model
   - [ ] Add Extension-Shop relationship
   - [ ] Create event processing pipeline
   - [ ] Implement rate limiting
   - [ ] Add extension status tracking

2. **Security Enhancements**
   - [ ] Implement token encryption
   - [ ] Add rate limiting
   - [ ] Configure CORS policies
   - [ ] Fix SSL verification

3. **Webhook Handlers**
   - [ ] Implement CUSTOMERS_DATA_REQUEST handler
   - [ ] Implement CUSTOMERS_REDACT handler
   - [ ] Implement SHOP_REDACT handler
   - [ ] Add webhook registration logic

## Medium Priority

1. **Asynchronous Processing**
   - [ ] Set up Celery
   - [ ] Configure message broker
   - [ ] Move webhook processing to background
   - [ ] Add task monitoring

2. **Caching Implementation**
   - [ ] Set up Redis
   - [ ] Implement caching strategy
   - [ ] Add cache invalidation
   - [ ] Monitor cache performance

## Low Priority

1. **Documentation & Monitoring**
   - [ ] Complete API documentation
   - [ ] Add deployment guide
   - [ ] Create troubleshooting guide
   - [ ] Set up monitoring and alerting

2. **Production Readiness**
   - [ ] Configure production logging
   - [ ] Set up backup procedures
   - [ ] Pin dependency versions
   - [ ] Configure SSL/TLS
