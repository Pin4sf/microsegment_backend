from app.core.celery_app import celery_app
from app.core.cache import redis_client
from app.services.shopify_service import ShopifyClient
from celery import states
import logging
from typing import Dict, Any, Optional
import requests
import json
import time

logger = logging.getLogger(__name__)

# Add this line to ensure tasks are registered
__all__ = ['pull_customers', 'pull_products', 'pull_orders', 'pull_all_data']


def make_sync_graphql_request(shop: str, access_token: str, query: str, variables: dict = None) -> dict:
    """Make a synchronous GraphQL request to Shopify API."""
    try:
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        # Ensure shop URL is properly formatted
        if not shop.endswith('.myshopify.com'):
            shop = f"{shop}.myshopify.com"

        url = f"https://{shop}/admin/api/2024-01/graphql.json"
        logger.info(f"Making request to Shopify API: {url}")

        # Add retry mechanism for network issues
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    verify=False,
                    timeout=30
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get(
                        'Retry-After', retry_delay))
                    logger.warning(
                        f"Rate limited by Shopify API. Retrying after {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                else:
                    logger.error(
                        f"Shopify API error: {response.status_code} - {response.text}")
                    raise Exception(
                        f"Shopify API returned status code {response.status_code}: {response.text}")

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    # Exponential backoff
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                raise

        raise Exception("Max retries exceeded")

    except Exception as e:
        logger.error(f"Error in make_sync_graphql_request: {str(e)}")
        raise


@celery_app.task(bind=True, max_retries=3)
def pull_customers(self, shop: str, access_token: str, batch_size: int = 100):
    """
    Pull all customers from a Shopify store in batches.
    """
    try:
        self.update_state(state=states.STARTED, meta={
            'status': 'Starting customer pull',
            'shop': shop
        })

        all_customers = []
        cursor = None
        total_pulled = 0

        while True:
            try:
                # Update progress
                self.update_state(
                    state=states.STARTED,
                    meta={
                        'status': 'Pulling customers',
                        'total_pulled': total_pulled,
                        'current_cursor': cursor,
                        'shop': shop
                    }
                )

                # Build query
                query_parts = [f"first: {batch_size}"]
                if cursor:
                    query_parts.append(f'after: "{cursor}"')

                query = f"""
                query {{
                  customers({', '.join(query_parts)}) {{
                    edges {{
                      node {{
                        id
                        firstName
                        lastName
                        email
                        createdAt
                        tags
                        note
                        state
                        amountSpent {{
                          amount
                          currencyCode
                        }}
                      }}
                      cursor
                    }}
                    pageInfo {{
                      hasNextPage
                      endCursor
                    }}
                  }}
                }}
                """

                # Make request
                response = make_sync_graphql_request(shop, access_token, query)

                if not response or 'data' not in response:
                    raise Exception("Invalid response from Shopify API")

                customers_data = response['data'].get('customers', {})
                edges = customers_data.get('edges', [])

                if not edges:
                    break

                # Extract customer data
                batch_customers = [edge['node'] for edge in edges]
                all_customers.extend(batch_customers)

                # Update progress
                total_pulled += len(batch_customers)

                # Check if there are more pages
                page_info = customers_data.get('pageInfo', {})
                if not page_info.get('hasNextPage'):
                    break

                cursor = page_info.get('endCursor')

            except Exception as e:
                logger.error(f"Error in customer pull batch: {str(e)}")
                raise

        # Store results in Redis
        redis_key = f"customer_pull:{shop}:{self.request.id}"
        redis_client.set(redis_key, json.dumps(all_customers))
        redis_client.expire(redis_key, 3600)  # Expire after 1 hour

        return {
            'status': 'completed',
            'total_customers': len(all_customers),
            'shop': shop
        }

    except Exception as exc:
        logger.error(f"Error pulling customers for shop {shop}: {str(exc)}")
        self.update_state(
            state=states.FAILURE,
            meta={
                'status': 'Failed',
                'error': str(exc),
                'shop': shop,
                'exc_type': type(exc).__name__
            }
        )
        raise  # Re-raise the exception for Celery to handle


@celery_app.task(bind=True, max_retries=3)
def pull_products(self, shop: str, access_token: str, batch_size: int = 100):
    """
    Pull all products from a Shopify store in batches.
    """
    try:
        self.update_state(state=states.STARTED, meta={
                          'status': 'Starting product pull'})

        all_products = []
        cursor = None
        total_pulled = 0

        while True:
            # Update progress
            self.update_state(
                state=states.STARTED,
                meta={
                    'status': 'Pulling products',
                    'total_pulled': total_pulled,
                    'current_cursor': cursor
                }
            )

            # Build query
            query_parts = [f"first: {batch_size}"]
            if cursor:
                query_parts.append(f'after: "{cursor}"')

            query = f"""
            query {{
              products({', '.join(query_parts)}) {{
                edges {{
                  node {{
                    id
                    title
                    handle
                    description
                    descriptionHtml
                    productType
                    vendor
                    tags
                    status
                    createdAt
                    priceRangeV2 {{
                      maxVariantPrice {{ amount }}
                      minVariantPrice {{ amount }}
                    }}
                    variants(first: 10) {{
                      edges {{
                        node {{
                          id
                          title
                          price
                          inventoryQuantity
                        }}
                      }}
                    }}
                  }}
                  cursor
                }}
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
              }}
            }}
            """

            # Make request
            response = make_sync_graphql_request(shop, access_token, query)

            if not response or 'data' not in response:
                break

            products_data = response['data'].get('products', {})
            edges = products_data.get('edges', [])

            if not edges:
                break

            # Extract product data
            batch_products = [edge['node'] for edge in edges]
            all_products.extend(batch_products)

            # Update progress
            total_pulled += len(batch_products)

            # Check if there are more pages
            page_info = products_data.get('pageInfo', {})
            if not page_info.get('hasNextPage'):
                break

            cursor = page_info.get('endCursor')

        # Store results in Redis
        redis_key = f"product_pull:{shop}:{self.request.id}"
        redis_client.set(redis_key, json.dumps(all_products))
        redis_client.expire(redis_key, 3600)  # Expire after 1 hour

        return {
            'status': 'completed',
            'total_products': len(all_products),
            'shop': shop
        }

    except Exception as exc:
        logger.error(f"Error pulling products for shop {shop}: {exc}")
        self.update_state(state=states.FAILURE, meta={
                          'status': 'Failed', 'error': str(exc)})
        self.retry(exc=exc, countdown=60)  # Retry after 1 minute


@celery_app.task(bind=True, max_retries=3)
def pull_orders(self, shop: str, access_token: str, batch_size: int = 100):
    """
    Pull all orders from a Shopify store in batches.
    """
    try:
        self.update_state(state=states.STARTED, meta={
                          'status': 'Starting order pull'})

        all_orders = []
        cursor = None
        total_pulled = 0

        while True:
            # Update progress
            self.update_state(
                state=states.STARTED,
                meta={
                    'status': 'Pulling orders',
                    'total_pulled': total_pulled,
                    'current_cursor': cursor
                }
            )

            # Build query
            query_parts = [f"first: {batch_size}"]
            if cursor:
                query_parts.append(f'after: "{cursor}"')

            query = f"""
            query {{
              orders({', '.join(query_parts)}) {{
                edges {{
                  node {{
                    id
                    name
                    email
                    createdAt
                    displayFinancialStatus
                    totalDiscountsSet {{ shopMoney {{ amount currencyCode }} }}
                    totalPriceSet {{ shopMoney {{ amount currencyCode }} }}
                    lineItems(first: 5) {{
                      edges {{
                        node {{
                          title
                          quantity
                          discountedTotalSet {{ shopMoney {{ amount currencyCode }} }}
                          originalTotalSet {{ shopMoney {{ amount currencyCode }} }}
                        }}
                      }}
                    }}
                    customer {{
                      firstName
                      lastName
                      email
                    }}
                  }}
                  cursor
                }}
                pageInfo {{
                  hasNextPage
                  endCursor
                }}
              }}
            }}
            """

            # Make request
            response = make_sync_graphql_request(shop, access_token, query)

            if not response or 'data' not in response:
                break

            orders_data = response['data'].get('orders', {})
            edges = orders_data.get('edges', [])

            if not edges:
                break

            # Extract order data
            batch_orders = [edge['node'] for edge in edges]
            all_orders.extend(batch_orders)

            # Update progress
            total_pulled += len(batch_orders)

            # Check if there are more pages
            page_info = orders_data.get('pageInfo', {})
            if not page_info.get('hasNextPage'):
                break

            cursor = page_info.get('endCursor')

        # Store results in Redis
        redis_key = f"order_pull:{shop}:{self.request.id}"
        redis_client.set(redis_key, json.dumps(all_orders))
        redis_client.expire(redis_key, 3600)  # Expire after 1 hour

        return {
            'status': 'completed',
            'total_orders': len(all_orders),
            'shop': shop
        }

    except Exception as exc:
        logger.error(f"Error pulling orders for shop {shop}: {exc}")
        self.update_state(state=states.FAILURE, meta={
                          'status': 'Failed', 'error': str(exc)})
        self.retry(exc=exc, countdown=60)  # Retry after 1 minute


@celery_app.task(bind=True, max_retries=3)
def pull_all_data(self, shop: str, access_token: str):
    """
    Pull all data (customers, products, orders) from a Shopify store.
    """
    try:
        self.update_state(state=states.STARTED, meta={
                          'status': 'Starting full data pull'})

        # Start all pull tasks
        customer_task = pull_customers.delay(shop, access_token)
        product_task = pull_products.delay(shop, access_token)
        order_task = pull_orders.delay(shop, access_token)

        return {
            'status': 'started',
            'tasks': {
                'customers': customer_task.id,
                'products': product_task.id,
                'orders': order_task.id
            },
            'shop': shop
        }

    except Exception as exc:
        logger.error(f"Error starting data pull for shop {shop}: {exc}")
        self.update_state(state=states.FAILURE, meta={
                          'status': 'Failed', 'error': str(exc)})
        self.retry(exc=exc, countdown=60)  # Retry after 1 minute
