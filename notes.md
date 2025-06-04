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
- Credential Secure Storage: Access tokens are not stored securely or persistently. Requires database storage with encryption.
- Shopify Webhook Handling: Essential for app lifecycle and privacy compliance. Foundation (routing, HMAC) is DONE. Specific handlers (CUSTOMERS_DATA_REQUEST, CUSTOMERS_REDACT, SHOP_REDACT) are PENDING.
- Server-side OAuth State Management: Current temporary dictionary is not suitable for production..

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
  - ✅ GraphQL queries updated with variable declarations
  - ✅ Bulk mode support added
  - ⚠️ SSL verification disabled (needs fix)

### 4. Webhook System
- **Infrastructure**
  - ✅ Basic webhook endpoint (`/webhooks`)
  - ✅ HMAC verification
  - ✅ Basic webhook task structure
  - ✅ Celery tasks for webhook processing
  - ✅ Background processing for webhooks
  - ⚠️ Missing GDPR handler implementations:
    - CUSTOMERS_DATA_REQUEST: Need to implement data fetching and packaging
    - CUSTOMERS_REDACT: Need to implement data deletion
    - SHOP_REDACT: Need to implement shop data cleanup
  - ⚠️ Missing app uninstallation handler
  - ⚠️ Need robust retry mechanism with exponential backoff

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
  - ✅ Task retry logic for data pulls
  - ✅ Task error handling for data pulls
  - ✅ Data pull tasks (customers, products, orders) logic implemented and fixed
  - ✅ `pull_all_data` task correctly schedules subtasks
  - ✅ API endpoint for triggering *full* data pulls (`/api/data/shopify/bulk-pull`) is working
  - ✅ API endpoint for checking task status (`/api/data-pull/status/{task_id}`) is working
  - ✅ API endpoint for retrieving results for a specific task/data type (`/api/data/shopify/results/{shop}/{task_id}`) is working correctly after fixing Redis key lookup
  - ✅ Bulk mode support added for task processing
  - ⚠️ Webhook retry mechanism needed
  - ⚠️ Task error handling for webhooks needed

### 7. Caching System
- **Redis Implementation**
  - ✅ Redis server setup
  - ✅ Basic caching decorator
  - ✅ Connection pooling
  - ✅ Redis used for storing data pull results (keyed by data type, shop, and task ID)
  - ✅ Data retrieval from Redis for the results endpoint is now working
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

#### Data Pulls
- `POST /api/data/shopify/bulk-pull`
  - **Unified endpoint to trigger a full data pull (Customers, Products, Orders) asynchronously via Celery.**
  - Accepts shop, access token, mode ('paginated' or 'bulk'), and batch size.
  - Returns the task ID of the main Celery task.
  - Supports bulk modes for data fetching.

- `GET /api/data-pull/status/{task_id}`
  - Gets the status of any Celery task ID (main bulk task or specific data type subtask).

- `GET /api/data/shopify/results/{shop}/{task_id}?data_type={type}`
  - **Retrieves results for a specific data type (customers, products, or orders) for a given task ID from Redis.**
  - Requires the shop domain, the specific subtask ID, and the data type query parameter.

#### Webhooks
- `POST /webhooks`
  - Handles all Shopify webhooks
  - Verifies HMAC signature
  - Routes to appropriate handlers
  - Processes in background using Celery
  - Currently handles:
    - CUSTOMERS_DATA_REQUEST (needs implementation)
    - CUSTOMERS_REDACT (needs implementation)
    - SHOP_REDACT (needs implementation)
  - Pending:
    - App uninstallation handler
    - Retry mechanism with exponential backoff

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

### 6. Webhooks
- App uninstallation webhook not handled
- GDPR webhook handlers need implementation
- No webhook registration on app installation
- Missing robust retry mechanism

### 7. Extension
- Event processing pipeline not implemented
- No rate limiting for event ingestion
- Extension status tracking incomplete
- Missing event validation

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

## Test Data

For testing the Shopify Data endpoints, use the following access token (this has all the permissions enabled):

```json
{
  "shop": "teststorshivansh.myshopify.com",
  "access_token": "shpat_YOUR_EXAMPLE_ACCESS_TOKEN_HERE"
}
```

### Example Requests

#### Full Data Pull Endpoint
```json
POST /api/data/shopify/bulk-pull
{
  "shop": "teststorshivansh.myshopify.com",
  "access_token": "shpat_YOUR_EXAMPLE_ACCESS_TOKEN_HERE",
  "mode": "paginated", // or "bulk"
  "batch_size": 100,
  "custom_query": null // Only applicable to 'paginated' mode and specific resources if implemented in tasks
}
```

#### Get Task Status
```json
GET /api/data-pull/status/{task_id}
```

## AI Integration Updates

### 1. Core AI Components
- **MicroSegment Class**
  - ✅ Core AI processing class implemented
  - ✅ OpenRouter API integration
  - ✅ Product and order history analysis
  - ✅ Batch processing support
  - ✅ File operations for results
  - ✅ Bulk mode support added

### 2. Service Layer Integration
- **AIService**
  - ✅ Service wrapper for MicroSegment
  - ✅ Async methods for AI operations
  - ✅ Singleton pattern implementation
  - ✅ Clean interface for API layer
  - ✅ Bulk mode support added

### 3. Task Management
- **Celery Integration**
  - ✅ Migrated from Huey to Celery
  - ✅ Background task processing
  - ✅ Task status tracking
  - ✅ Result handling
  - ✅ Error management
  - ✅ Bulk mode support added

### 4. API Layer
- **AI Router**
  - ✅ Product processing endpoint
  - ✅ Order history processing endpoint
  - ✅ Batch processing endpoint
  - ✅ Task status endpoint
  - ✅ Pydantic schema validation
  - ✅ Bulk mode support added

### 5. Shopify Integration
- **Data Processing Pipeline**
  - ✅ New endpoint for processing Shopify data with AI
  - ✅ Integration with existing data pull system
  - ✅ Redis-based data caching
  - ✅ Batch processing support
  - ✅ Error handling and validation
  - ✅ Bulk mode support added

### 6. Configuration
- **Environment Variables**
  - ✅ OpenRouter API key
  - ✅ AI model settings
  - ✅ Task timeout configuration
  - ✅ Output directory settings
  - ✅ Bulk mode settings

### 7. Integration Points
- **Backend Integration**
  - ✅ FastAPI router integration
  - ✅ Celery task system
  - ✅ Redis for task results
  - ✅ Error handling middleware
  - ✅ Bulk mode support added

### 8. API Endpoints

#### Product Processing
```http
POST /api/ai/products/process
Content-Type: application/json

{
    "title": "Product Title",
    "description": "Product Description",
    "handle": "product-handle",
    "product_type": "Product Type",
    "tags": ["tag1", "tag2"],
    "options": [
        {
            "name": "Size",
            "values": ["S", "M", "L"]
        }
    ],
    "images": [
        {
            "src": "https://example.com/image.jpg"
        }
    ],
    "mode": "bulk" // or "paginated"
}
```

#### Order History Processing
```http
POST /api/ai/orders/process
Content-Type: application/json

{
    "customer_history": {
        // customer data
    },
    "order_history": {
        // order data
    },
    "mode": "bulk" // or "paginated"
}
```

#### Batch Processing
```http
POST /api/ai/products/batch
Content-Type: application/json

{
    "products": [
        // array of products
    ],
    "output_dir": "outputs",
    "mode": "bulk" // or "paginated"
}
```

#### Shopify Data Processing
```http
POST /process-with-ai/{shop}/{task_id}?data_type=products&mode=bulk
```
or
```http
POST /process-with-ai/{shop}/{task_id}?data_type=orders&mode=bulk
```

#### Task Status
```http
GET /api/ai/tasks/{task_id}
```

### 9. Next Steps

1. **High Priority**
   - Implement AI result caching
   - Add rate limiting for AI endpoints
   - Implement error recovery for AI tasks
   - Add monitoring for AI processing

2. **Medium Priority**
   - Add AI processing metrics
   - Implement result validation
   - Add retry mechanism for failed AI calls
   - Create AI processing dashboard

3. **Low Priority**
   - Add AI model versioning
   - Implement A/B testing
   - Add result comparison tools
   - Create AI processing documentation

### 10. Known Issues

1. **Performance**
   - Large batch processing might need optimization
   - AI model response time varies
   - Memory usage during batch processing

2. **Error Handling**
   - Need better error messages for AI failures
   - Retry mechanism for API timeouts
   - Better handling of malformed responses

3. **Security**
   - API key rotation mechanism needed
   - Rate limiting implementation pending
   - Input validation could be enhanced

### 11. Development Guidelines

1. **AI Processing**
   - Use async/await for API calls
   - Implement proper error handling
   - Add comprehensive logging
   - Validate all inputs and outputs

2. **Task Management**
   - Monitor task queue size
   - Implement task prioritization
   - Add task timeout handling
   - Implement task cancellation

3. **Testing**
   - Add unit tests for AI processing
   - Implement integration tests
   - Add performance benchmarks
   - Test error scenarios

## Task Processing Updates

### Current Implementation
1. **Synchronous Processing**
   - Using Celery with solo pool for Windows compatibility
   - Basic task status tracking and result retrieval
   - Simple error handling
   - Redis for task results storage
   - Flower for task monitoring
   - Bulk mode support added

2. **Task Types**
   - Data pull tasks (customers, products, orders)
   - Webhook processing tasks
   - AI processing tasks
   - Instant preview tasks
   - Bulk processing tasks

3. **Task Management**
   - Task status tracking via Redis
   - Basic error handling and retries
   - Task result caching
   - Task queue management
   - Bulk mode support added

### Production Requirements
1. **Async Processing**
   - Migrate to gevent pool
   - Update task functions to use async/await
   - Implement proper async error handling
   - Add task prioritization
   - Set up task monitoring

2. **Task Optimization**
   - Add task timeout handling
   - Implement task cancellation
   - Set up task metrics
   - Add task rate limiting
   - Implement task error recovery

3. **Monitoring & Logging**
   - Add comprehensive task logging
   - Set up task monitoring dashboard
   - Create task processing documentation
   - Add performance optimizations
   - Implement task queue management

### Development Guidelines

1. **Task Implementation**
   - Use async/await for production tasks
   - Implement proper error handling
   - Add comprehensive logging
   - Validate all inputs and outputs
   - Monitor task queue size

2. **Task Management**
   - Implement task prioritization
   - Add task timeout handling
   - Implement task cancellation
   - Add unit tests for task processing
   - Implement integration tests

3. **Performance**
   - Add performance benchmarks
   - Test error scenarios
   - Monitor task execution time
   - Track resource usage
   - Optimize task scheduling

### Known Issues

1. **Task Processing**
   - Currently using synchronous processing with solo pool
   - Need to migrate to async processing for production
   - Task prioritization not implemented
   - No task timeout handling
   - Missing task cancellation support

2. **Monitoring**
   - Limited task monitoring
   - No task metrics
   - Basic error handling only
   - No task rate limiting
   - Missing task error recovery

3. **Logging**
   - Limited task logging
   - Basic task status tracking
   - No task result caching
   - Missing performance metrics
   - Incomplete error tracking

### Next Steps

1. **High Priority**
   - Implement async task processing
   - Add task prioritization
   - Set up task monitoring
   - Implement task timeout handling
   - Add task cancellation support

2. **Medium Priority**
   - Add task metrics
   - Implement task rate limiting
   - Add task error recovery
   - Set up task logging
   - Implement task status tracking

3. **Low Priority**
   - Add task result caching
   - Create task monitoring dashboard
   - Add performance optimizations
   - Implement task queue management
   - Create task processing documentation

### Production Checklist

1. **Task Processing**
   - [ ] Migrate to async processing
   - [ ] Implement task prioritization
   - [ ] Add task timeout handling
   - [ ] Set up task monitoring
   - [ ] Add performance metrics

2. **Task Management**
   - [ ] Implement task cancellation
   - [ ] Add task retry mechanisms
   - [ ] Set up task queue management
   - [ ] Implement task rate limiting
   - [ ] Add task error recovery

3. **Monitoring & Logging**
   - [ ] Set up task logging
   - [ ] Implement task status tracking
   - [ ] Add task result caching
   - [ ] Create monitoring dashboard
   - [ ] Add performance tracking

### Example Task Implementation

```python
@celery_app.task(bind=True)
async def example_task(self, *args, **kwargs):
    try:
        # Task implementation
        result = await process_data(*args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise
```

### Task Configuration

```python
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_queues=(
        Queue('default', routing_key='default'),
        Queue('high_priority', routing_key='high_priority'),
    ),
    task_routes={
        'app.tasks.ai_tasks.*': {'queue': 'high_priority'},
    }
)
```

### Worker Command

```bash
# Development (Windows)
celery -A app.core.celery_app worker --pool=solo --loglevel=info

# Production
celery -A app.core.celery_app worker --pool=gevent --concurrency=10 --loglevel=info
```
