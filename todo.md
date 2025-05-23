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

4. **Asynchronous Task Processing & Data Pulls**
   - [x] Set up Celery
   - [x] Configure message broker (Redis)
   - [x] Configure Windows-specific settings
   - [x] Set up Flower for task monitoring
   - [x] Create data pull tasks (customers, products, orders)
   - [x] Implement task retry logic for data pulls
   - [x] Add task error handling for data pulls
   - [x] Implement API endpoints for managing data pulls (start, status, results)
   - [ ] Move webhook processing to background

5. **Caching Strategy**
   - [x] Set up Redis
   - [x] Implement basic caching decorator
   - [x] Configure Redis connection
   - [x] Use Redis for data pull results caching
   - [ ] Set up session management with Redis
  - [ ] Implement caching for frequently accessed data
  - [ ] Add cache invalidation strategies
  - [ ] Monitor cache performance

6. **Test UI**
   - [x] Implement test UI for API endpoints
   - [x] Add automatic credential population and state management
   - [x] Refine test UI flow for data collection demo

## In Progress 🚧

1. **Web Pixel Extension Integration**
   - [x] Create Extension model
   - [x] Create Event model
   - [x] Set up database schema
   - [x] Implement basic extension activation
   - [ ] Implement event processing pipeline
   - [ ] Add rate limiting for event ingestion
   - [ ] Set up extension status tracking
   - [ ] Add extension version management
   - [ ] Implement event validation

2. **Webhook Handling**
   - [x] Basic webhook endpoint setup
   - [x] HMAC verification
   - [x] Basic webhook task structure
   - [ ] Implement CUSTOMERS_DATA_REQUEST handler
   - [ ] Implement CUSTOMERS_REDACT handler
   - [ ] Implement SHOP_REDACT handler
   - [ ] Implement app/uninstalled handler
   - [ ] Add webhook registration logic
   - [ ] Implement webhook retry mechanism

3. **Security Enhancements**
   - [x] Basic session management (using FastAPI SessionMiddleware)
   - [ ] Implement Redis-based session management
   - [ ] Implement token encryption
   - [ ] Add rate limiting
   - [ ] Configure proper CORS policies
   - [ ] Fix SSL verification
   - [ ] Add request validation
   - [ ] Implement API key authentication

## Current Status & Important Notes

### Recent Updates

1. **Authentication & Session Management**:
   - Currently using FastAPI's SessionMiddleware for session management
   - OAuth state stored in session cookies
   - **Need to migrate to Redis for better scalability and security** (High Priority)
   - Session TTL needs to be configured
   - Cross-tab communication for test UI implemented

2. **Test UI Improvements**:
   - Added automatic credential population and state management
   - Refined data collection flow
   - Addressed previous 500/404 errors by fixing backend results endpoint and frontend polling logic (although data display might still need refinement)
   - Added error handling and improved user feedback

3. **Asynchronous Processing & Data Pulls**:
   - Celery worker successfully configured with Windows workarounds
   - Redis connection established and used for task results
   - **Data pull tasks for customers, products, and orders are implemented and working**
   - API endpoints for starting, checking status, and retrieving results are implemented
   - Task retry and basic error handling for data pulls are in place
   - Flower monitoring set up

4. **Caching**:
   - Redis is set up and used for caching data pull results.

### Immediate Next Steps

1. **High Priority**:
   - Migrate session management to Redis
   - Implement webhook handlers for GDPR compliance (CUSTOMERS_DATA_REQUEST, CUSTOMERS_REDACT, SHOP_REDACT)
   - Add app uninstallation handler
   - Set up event processing pipeline for Web Pixel Extension
   - Implement token encryption for stored access tokens

2. **Medium Priority**:
   - Add rate limiting for API endpoints (using Redis)
   - Configure proper CORS policies (restrict origins for production)
   - Implement additional caching for frequently accessed data (beyond data pull results)
   - Implement webhook retry mechanism
   - Add request validation for API endpoints

3. **Low Priority**:
   - Add comprehensive logging (review existing logging)
   - Set up monitoring and alerting (beyond Flower)
   - Create deployment documentation
   - Add performance optimizations
   - Implement API key authentication
   - **Refine data display in the test UI**

### Known Issues

1. **Security**:
   - Raw access tokens are being logged (temporary for testing) - **Needs to be removed/secured**
   - SSL verification is disabled in `ShopifyClient` - **Needs to be fixed for production**
   - No rate limiting implemented yet
   - CORS policy needs refinement (too permissive in development)
   - Session management using cookies instead of Redis

2. **Webhooks**:
   - App uninstallation webhook not handled
   - GDPR webhooks not implemented
   - No webhook registration on app installation (manual setup needed)
   - Missing retry mechanism (beyond basic task retry)

3. **Extension**:
   - Event processing pipeline not implemented
   - No rate limiting for event ingestion
   - Extension status tracking incomplete
   - Missing event validation

4. **Frontend (Test UI Data Display)**:
   - Frontend polling logic for data results is working (handling 404s), but actual data display might still have issues (as noted in our last debugging session).

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
   - **Test data pull functionality thoroughly**

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

## Next Steps (Prioritized)

### High Priority
1.  Migrate session management to Redis
2.  Implement webhook handlers for GDPR compliance (CUSTOMERS_DATA_REQUEST, CUSTOMERS_REDACT, SHOP_REDACT)
3.  Add app uninstallation handler
4.  Set up event processing pipeline for Web Pixel Extension
5.  Implement token encryption for stored access tokens

### Medium Priority
1.  Add rate limiting for API endpoints (using Redis)
2.  Configure proper CORS policies (restrict origins for production)
3.  Implement additional caching for frequently accessed data (beyond data pull results)
4.  Implement webhook retry mechanism
5.  Add request validation for API endpoints

### Low Priority
1.  Add comprehensive logging (review existing logging)
2.  Set up monitoring and alerting (beyond Flower)
3.  Create deployment documentation
4.  Add performance optimizations
5.  Implement API key authentication
6.  **Refine data display in the test UI**