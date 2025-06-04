# TODO

## Completed Tasks ✅

1. **Project Structure & Core Setup**
- [x] Set up FastAPI project structure
- [x] Implement environment variables management
- [x] Create logging system
- [x] Create ShopifyClient base class
- [x] Implement Shopify OAuth flow
  - [x] Add store connection endpoint
  - [x] Build OAuth callback handler
     - [ ] Implement session management with Redis

2. **Database Integration & Core Models**
   - [x] Add DB dependencies to `requirements.txt`
   - [x] Create directory structure: `app/db/`, `app/models/`
   - [x] Configure `DATABASE_URL` in `app/core/config.py`
   - [x] Create `app/db/session.py` & `app/db/base.py`
   - [x] Create `Shop` model with all necessary fields
   - [x] Set up Alembic migrations
   - [x] Create and apply initial migrations
   - [x] Add extensions and events tables

3. **Data Fetching Endpoints**
  - [x] Create product data fetcher method & endpoint
  - [x] Create order data fetcher method & endpoint
  - [x] Create transaction data fetcher method & endpoint
   - [x] Implement Customer Data Fetching
  - [x] Add pagination for Shopify API calls
  - [x] Implement test UI for API endpoints
  - [x] Add bulk mode support for data fetching
  - [x] Implement unified bulk-pull endpoint

4. **Asynchronous Task Processing & Data Pulls**
   - [x] Set up Celery
   - [x] Configure message broker (Redis)
   - [x] Configure Windows-specific settings
   - [x] Set up Flower for task monitoring
   - [x] Create data pull tasks (customers, products, orders) - *Core logic and fixes implemented*
   - [x] Implement task retry logic for data pulls
   - [x] Add task error handling for data pulls
   - [x] Implement API endpoints for managing data pulls (start, status, results) - *Unified /bulk-pull start endpoint implemented, status/results endpoints fixed*
   - [x] Move webhook processing to background
   - [x] Implement synchronous task processing for instant preview
   - [x] Configure Celery worker with solo pool for Windows compatibility
   - [x] Add bulk mode support for data processing
   - [ ] Implement async task processing for production
   - [ ] Add task prioritization
   - [ ] Implement task timeout handling
   - [ ] Add task cancellation support
   - [ ] Set up task monitoring and metrics

5. **Caching Strategy**
   - [x] Set up Redis
   - [x] Implement basic caching decorator
   - [x] Configure Redis connection
   - [x] Use Redis for data pull results caching - *Data storage/retrieval issue identified and FIXED*
   - [ ] Set up session management with Redis
  - [ ] Implement caching for frequently accessed data
  - [ ] Add cache invalidation strategies
  - [ ] Monitor cache performance

6. **Test UI**
   - [x] Implement test UI for API endpoints
   - [x] Add automatic credential population and state management
   - [x] Refine test UI flow for data collection demo
   - [x] Add error handling and improved user feedback
   - [x] Add bulk mode support in UI

7. **Webhook Infrastructure**
   - [x] Basic webhook endpoint setup
   - [x] HMAC verification
   - [x] Basic webhook task structure
   - [x] Celery tasks for webhook processing
   - [x] Background processing for webhooks

8. **AI Integration**
   - [x] Set up AI service layer
   - [x] Create Celery tasks for AI processing
   - [x] Implement AI router with endpoints
   - [x] Add Pydantic schemas for AI requests/responses
   - [x] Configure AI environment variables
   - [x] Integrate with main FastAPI application
   - [x] Migrate from Huey to Celery for AI tasks
   - [x] Implement task status tracking
   - [x] Add error handling for AI processing
   - [x] Integrate with Shopify data pull system
   - [x] Add Redis-based data caching
   - [x] Implement batch processing support
   - [x] Add validation and error handling
   - [x] Add bulk mode support for AI processing

## In Progress 🚧

1. **Web Pixel Extension Integration**
   - [x] Create Extension model
   - [x] Create Event model
   - [x] Set up database schema
   - [x] Implement basic extension activation - *Confirmed working*
   - [ ] Implement event processing pipeline
   - [ ] Add rate limiting for event ingestion
   - [ ] Set up extension status tracking
   - [ ] Add extension version management
   - [ ] Implement event validation

2. **Webhook Handling**
   - [x] Basic webhook endpoint setup
   - [x] HMAC verification
   - [x] Basic webhook task structure
   - [x] Celery tasks for webhook processing
   - [ ] Implement CUSTOMERS_DATA_REQUEST handler logic
   - [ ] Implement CUSTOMERS_REDACT handler logic
   - [ ] Implement SHOP_REDACT handler logic
   - [ ] Implement app/uninstalled handler
   - [ ] Add webhook registration logic
   - [ ] Implement webhook retry mechanism with exponential backoff

3. **Security Enhancements**
   - [x] Basic session management (using FastAPI SessionMiddleware)
   - [ ] Implement Redis-based session management
   - [ ] Implement token encryption
   - [ ] Add rate limiting
   - [ ] Configure proper CORS policies
   - [ ] Fix SSL verification
   - [ ] Add request validation
   - [ ] Implement API key authentication

4. **AI System Enhancements**
   - [ ] Implement AI result caching
   - [ ] Add rate limiting for AI endpoints
   - [ ] Implement error recovery for AI tasks
   - [ ] Add monitoring for AI processing
   - [ ] Create AI processing dashboard
   - [ ] Add AI model versioning
   - [ ] Implement A/B testing for different models
   - [ ] Add result comparison tools
   - [ ] Create AI processing documentation
   - [ ] Add performance optimizations for batch processing
   - [ ] Implement retry mechanism for API timeouts
   - [ ] Add comprehensive error messages
   - [ ] Implement API key rotation
   - [ ] Add input validation enhancements

5. **Task Processing Optimization**
   - [x] Implement synchronous task processing for instant preview
   - [x] Configure Celery worker with solo pool
   - [x] Add bulk mode support for task processing
   - [ ] Migrate to async task processing for production
   - [ ] Implement task prioritization
   - [ ] Add task timeout handling
   - [ ] Set up task monitoring
   - [ ] Add performance metrics
   - [ ] Implement task cancellation
   - [ ] Add task retry mechanisms
   - [ ] Set up task queue management
   - [ ] Implement task rate limiting
   - [ ] Add task error recovery
   - [ ] Set up task logging
   - [ ] Implement task status tracking
   - [ ] Add task result caching

## Current Status & Important Notes

### Recent Updates

1. **Webhook Handling**:
   - ✅ Basic webhook infrastructure is in place
   - ✅ Celery tasks for processing webhooks are defined
   - ✅ Background processing is implemented
   - ❌ Need to implement actual handler logic for GDPR compliance
   - ❌ Need to add app uninstallation handler
   - ❌ Need to implement robust retry mechanism

2. **Authentication & Session Management**:
   - Currently using FastAPI's SessionMiddleware for session management
   - OAuth state stored in session cookies
   - **Need to migrate to Redis for better scalability and security** (High Priority)
   - Session TTL needs to be configured
   - Cross-tab communication for test UI implemented

3. **Test UI Improvements**:
   - Added automatic credential population and state management
   - Refined data collection flow
   - Addressed previous 500/404 errors by fixing backend results endpoint and frontend polling logic
   - Added error handling and improved user feedback

4. **Asynchronous Processing & Data Pulls**:
   - Celery worker successfully configured with Windows workarounds
   - Redis connection established and used for task results
   - Data pull tasks for customers, products, and orders are implemented and working
   - API endpoints for starting, checking status, and retrieving results are implemented **and functioning correctly after fixing Redis key lookup.**
   - Task retry and basic error handling for data pulls are in place
   - Flower monitoring set up
   - **Data pull endpoint consolidated to a single trigger.**
   - **Schemas updated for data pull requests.**
   - **API documentation for data pull flow improved.**

5. **Caching**:
   - Redis is set up and used for caching data pull results
   - **The issue with retrieving data from Redis for the results endpoint has been identified and fixed.**

6. **Web Pixel Extension Integration**:
     - ✅ Create Extension model
     - ✅ Create Event model
     - ✅ Set up database schema
     - ✅ Implement basic extension activation - **Confirmed working based on logs and database interaction**
     - ❌ Implement event processing pipeline (Pending)
     - ❌ Add rate limiting for event ingestion (Pending)
     - ❌ Set up extension status tracking (Pending)

7. **AI Integration**:
   - ✅ Basic AI infrastructure is in place
   - ✅ Celery tasks for AI processing are defined
   - ✅ Background processing is implemented
   - ✅ API endpoints are working
   - ✅ Shopify data integration is complete
   - ✅ Redis-based caching is implemented
   - ✅ Batch processing is supported
   - ✅ Error handling is in place
   - ❌ Need to implement result caching
   - ❌ Need to add rate limiting
   - ❌ Need to implement error recovery
   - ❌ Need to add monitoring
   - ❌ Need to optimize batch processing
   - ❌ Need to implement API key rotation
   - ❌ Need to enhance input validation

8. **Task Processing**:
   - ✅ Synchronous task processing implemented for instant preview
   - ✅ Celery worker configured with solo pool for Windows compatibility
   - ✅ Task status tracking and result retrieval working
   - ✅ Basic error handling in place
   - ❌ Need to implement async processing for production
   - ❌ Need to add task prioritization
   - ❌ Need to implement task timeout handling
   - ❌ Need to add task cancellation support
   - ❌ Need to set up task monitoring and metrics

### Immediate Next Steps

1. **High Priority**:
   - Implement GDPR webhook handler logic:
     - CUSTOMERS_DATA_REQUEST: Fetch and package customer data
     - CUSTOMERS_REDACT: Delete customer data and metafields
     - SHOP_REDACT: Delete all shop data
   - Add app uninstallation handler
   - Implement robust webhook retry mechanism with exponential backoff
   - Migrate session management to Redis
   - Implement token encryption for stored access tokens
   - Fix SSL verification in `ShopifyClient`.
   - Implement AI result caching
   - Add rate limiting for AI endpoints
   - Implement error recovery for AI tasks
   - Add monitoring for AI processing
   - Optimize batch processing performance
   - Implement async task processing for production:
     - Migrate to gevent pool
     - Update task functions to use async/await
     - Implement proper async error handling
     - Add task prioritization
     - Set up task monitoring

2. **Medium Priority**:
   - Add rate limiting for API endpoints
   - Configure proper CORS policies
   - Implement additional caching
   - Add request validation
   - Add AI processing metrics
   - Implement result validation
   - Add retry mechanism for failed AI calls
   - Create AI processing dashboard
   - Implement API key rotation
   - Enhance input validation
   - Add task timeout handling
   - Implement task cancellation
   - Set up task metrics
   - Add task rate limiting
   - Implement task error recovery

3. **Low Priority**:
   - Add comprehensive logging
   - Set up monitoring and alerting
   - Create deployment documentation
   - Add performance optimizations
   - Implement API key authentication
   - Refine data display in the test UI
   - Add AI model versioning
   - Implement A/B testing
   - Add result comparison tools
   - Create AI processing documentation
   - Add comprehensive task logging
   - Set up task monitoring dashboard
   - Create task processing documentation
   - Add performance optimizations
   - Implement task queue management

### Known Issues

1. **Security**:
   - Raw access tokens are being logged (temporary for testing) - **Needs to be removed/secured**
   - SSL verification is disabled in `ShopifyClient` - **Needs to be fixed for production**
   - No rate limiting implemented yet
   - CORS policy needs refinement (too permissive in development)
   - Session management using cookies instead of Redis

2. **Webhooks**:
   - App uninstallation webhook not handled
   - GDPR webhook handlers need implementation
   - No webhook registration on app installation (manual setup needed)
   - Missing robust retry mechanism

3. **Extension**:
   - Event processing pipeline not implemented
   - No rate limiting for event ingestion
   - Extension status tracking incomplete
   - Missing event validation

4. **AI Processing**:
   - Large batch processing might need optimization
   - AI model response time varies
   - Memory usage during batch processing
   - Need better error messages for AI failures
   - Retry mechanism for API timeouts needed
   - Better handling of malformed responses required
   - API key rotation mechanism needed
   - Rate limiting implementation pending
   - Input validation could be enhanced
   - Result caching not implemented
   - Monitoring system not in place
   - Error recovery mechanism needed

5. **Task Processing**:
   - Currently using synchronous processing with solo pool
   - Need to migrate to async processing for production
   - Task prioritization not implemented
   - No task timeout handling
   - Missing task cancellation support
   - Limited task monitoring
   - No task metrics
   - Basic error handling only
   - No task rate limiting
   - Missing task error recovery
   - Limited task logging
   - Basic task status tracking
   - No task result caching

### Development Guidelines

1. **Code Style**:
   - Follow existing project structure
   - Use type hints
   - Add proper docstrings
   - Include error handling
   - Add logging statements

2. **Testing**:
   - Test all webhook handlers
   - Verify extension functionality
   - Check security measures
   - Validate data integrity
   - Test rate limiting
   - Test data pull functionality thoroughly

3. **Security**:
   - Never log sensitive data in production
   - Use environment variables
   - Implement proper encryption
   - Follow OWASP guidelines

4. **Performance**:
   - Use async/await properly
   - Implement caching where needed
   - Monitor database queries
   - Optimize API calls

5. **Task Processing**:
   - Use async/await for production tasks
   - Implement proper error handling
   - Add comprehensive logging
   - Validate all inputs and outputs
   - Monitor task queue size
   - Implement task prioritization
   - Add task timeout handling
   - Implement task cancellation
   - Add unit tests for task processing
   - Implement integration tests
   - Add performance benchmarks
   - Test error scenarios

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

### Task Processing
- [ ] Migrate to async processing
- [ ] Implement task prioritization
- [ ] Add task timeout handling
- [ ] Set up task monitoring
- [ ] Add performance metrics
- [ ] Implement task cancellation
- [ ] Add task retry mechanisms
- [ ] Set up task queue management
- [ ] Implement task rate limiting
- [ ] Add task error recovery
- [ ] Set up task logging
- [ ] Implement task status tracking
- [ ] Add task result caching