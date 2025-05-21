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

4. **Asynchronous Task Processing**
   - [x] Set up Celery
   - [x] Configure message broker (Redis)
   - [x] Set up basic task structure
   - [x] Configure Windows-specific settings
   - [x] Set up Flower for task monitoring
   - [ ] Move webhook processing to background
   - [ ] Implement task retry logic
   - [ ] Add task error handling

5. **Caching Strategy**
   - [x] Set up Redis
   - [x] Implement basic caching decorator
   - [x] Configure Redis connection
   - [ ] Set up session management with Redis
   - [ ] Implement caching for frequently accessed data
   - [ ] Add cache invalidation strategies
   - [ ] Monitor cache performance

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
   - [ ] Implement Redis-based state storage
   - [ ] Implement token encryption
   - [ ] Add rate limiting
   - [ ] Configure CORS policies
   - [ ] Fix SSL verification
   - [ ] Add request validation
   - [ ] Implement API key authentication

## Current Status & Important Notes

### Recent Updates

1. **Authentication & Session Management**:
   - Currently using FastAPI's SessionMiddleware for session management
   - OAuth state stored in session cookies
   - Need to migrate to Redis for better scalability and security
   - Session TTL needs to be configured
   - Cross-tab communication for test UI implemented

2. **Test UI Improvements**:
   - Added automatic credential population
   - Implemented connection status tracking
   - Added error handling
   - Improved user feedback

3. **Asynchronous Processing**:
   - Celery worker successfully configured
   - Redis connection established
   - Basic task structure implemented
   - Windows-specific settings added
   - Flower monitoring set up

### Immediate Next Steps

1. **High Priority**:
   - Migrate session management to Redis
   - Implement GDPR webhook handlers
   - Add app uninstallation handler
   - Set up event processing pipeline
   - Implement token encryption
   - Add rate limiting for API endpoints

2. **Medium Priority**:
   - Configure proper CORS policies
   - Implement caching for Shopify API responses
   - Add task monitoring with Flower
   - Implement webhook retry mechanism
   - Add request validation

3. **Low Priority**:
   - Add comprehensive logging
   - Set up monitoring
   - Create deployment documentation
   - Add performance optimizations
   - Implement API key authentication

### Known Issues

1. **Security**:
   - Raw access tokens are being logged (temporary for testing)
   - SSL verification is disabled (needs to be fixed for production)
   - No rate limiting implemented yet
   - CORS policy needs refinement
   - Session management using cookies instead of Redis

2. **Webhooks**:
   - App uninstallation webhook not handled
   - GDPR webhooks not implemented
   - No webhook registration on app installation
   - Missing retry mechanism

3. **Extension**:
   - Event processing pipeline not implemented
   - No rate limiting for event ingestion
   - Extension status tracking incomplete
   - Missing event validation

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

3. **Documentation**:
   - Update API documentation
   - Document webhook handlers
   - Add setup instructions
   - Include troubleshooting guide
   - Document security measures

### Production Readiness Checklist

- [ ] Remove debug logging
- [ ] Implement proper error handling
- [ ] Set up monitoring
- [ ] Configure production logging
- [ ] Add backup procedures
- [ ] Document deployment process
- [ ] Configure SSL/TLS
- [ ] Set up rate limiting
- [ ] Implement token encryption
- [ ] Configure proper CORS
- [ ] Migrate session management to Redis