from app.core.celery_app import celery_app
from app.core.cache import redis_client
from app.services.shopify_service import ShopifyClient
from celery import states
import logging
from typing import Dict, Any, Optional
import requests
import json
import time
from celery import shared_task
from celery.utils.log import get_task_logger
from app.core.config import settings

logger = get_task_logger(__name__)

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

        url = f"https://{shop}/admin/api/2025-04/graphql.json"
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


@shared_task(bind=True, name="pull_customers")
def pull_customers(self, shop: str, access_token: str) -> Dict[str, Any]:
    """Pull customer data using bulk operations."""
    try:
        self.update_state(
            state=states.STARTED,
            meta={
                'current': 0,
                'total': 'unknown',
                'status': 'Starting customer data pull...'
            }
        )

        # Start bulk operation
        query = """
        {
            customers {
                edges {
                    node {
                        id
                        firstName
                        lastName
                        email
                        createdAt
                        tags
                        note
                        state
                        amountSpent {
                            amount
                            currencyCode
                        }
                    }
                }
            }
        }
        """

        result = start_bulk_operation(shop, access_token, "customers")
        if (
            not result or
            'data' not in result or
            'bulkOperationRunQuery' not in result['data'] or
            result['data']['bulkOperationRunQuery'].get('userErrors')
        ):
            raise Exception(
                f"Failed to start bulk operation: "
                f"{result['data']['bulkOperationRunQuery'].get('userErrors')}"
            )

        # Poll for completion
        op = poll_bulk_operation(shop, access_token)
        if op["status"] == "COMPLETED":
            data = download_bulk_data(op["url"])
            redis_key = f"shopify:customers:{shop}:{self.request.id}"
            redis_client.set(
                redis_key,
                json.dumps(data),
                ex=3600
            )
            return {
                'success': True,
                'count': len(data),
                'message': f'Successfully pulled {len(data)} customers'
            }
        else:
            raise Exception(
                f"Bulk operation for customers failed: {op.get('errorCode')}")

    except Exception as e:
        logger.error(f"Error pulling customers: {str(e)}", exc_info=True)
        self.update_state(
            state=states.FAILURE,
            meta={
                'error': str(e),
                'message': f'Failed to pull customers: {str(e)}'
            }
        )
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to pull customers: {str(e)}'
        }


@shared_task(bind=True, name="pull_products")
def pull_products(self, shop: str, access_token: str) -> Dict[str, Any]:
    """
    Pull product data from Shopify using bulk operations
    """
    try:
        self.update_state(
            state=states.STARTED,
            meta={
                'current': 0,
                'total': 'unknown',
                'status': 'Starting product data pull...'
            }
        )

        # Start bulk operation
        result = start_bulk_operation(shop, access_token, "products")
        if not result or 'data' not in result:
            raise Exception("Failed to start bulk operation for products")

        # Poll for completion
        op = poll_bulk_operation(shop, access_token)
        if op["status"] == "COMPLETED":
            data = download_bulk_data(op["url"])
            redis_key = f"shopify:products:{shop}:{self.request.id}"
            redis_client.set(
                redis_key,
                json.dumps(data),
                ex=3600
            )
            return {
                'success': True,
                'count': len(data),
                'message': f'Successfully pulled {len(data)} products'
            }
        else:
            raise Exception(
                f"Bulk operation for products failed: {op.get('errorCode')}")

    except Exception as e:
        logger.error(
            f"Error pulling products for shop {shop}: {str(e)}", exc_info=True)
        self.update_state(
            state=states.FAILURE,
            meta={
                'error': str(e),
                'message': f'Failed to pull products: {str(e)}'
            }
        )
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to pull products: {str(e)}'
        }


@shared_task(bind=True, name="pull_orders")
def pull_orders(self, shop: str, access_token: str) -> Dict[str, Any]:
    """
    Pull order data from Shopify using bulk operations
    """
    try:
        self.update_state(
            state=states.STARTED,
            meta={
                'current': 0,
                'total': 'unknown',
                'status': 'Starting order data pull...'
            }
        )

        # Start bulk operation
        result = start_bulk_operation(shop, access_token, "orders")
        if not result or 'data' not in result:
            raise Exception("Failed to start bulk operation for orders")

        # Poll for completion
        op = poll_bulk_operation(shop, access_token)
        if op["status"] == "COMPLETED":
            data = download_bulk_data(op["url"])
            redis_key = f"shopify:orders:{shop}:{self.request.id}"
            redis_client.set(
                redis_key,
                json.dumps(data),
                ex=3600
            )
            return {
                'success': True,
                'count': len(data),
                'message': f'Successfully pulled {len(data)} orders'
            }
        else:
            raise Exception(
                f"Bulk operation for orders failed: {op.get('errorCode')}")

    except Exception as e:
        logger.error(
            f"Error pulling orders for shop {shop}: {str(e)}", exc_info=True)
        self.update_state(
            state=states.FAILURE,
            meta={
                'error': str(e),
                'message': f'Failed to pull orders: {str(e)}'
            }
        )
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to pull orders: {str(e)}'
        }


def start_bulk_operation(shop: str, access_token: str, resource: str) -> dict:
    """Start a bulk operation for the specified resource."""
    resource_queries = {
        "customers": """
            {
              customers {
                edges {
                  node {
                    id
                    firstName
                    lastName
                    email
                    createdAt
                    tags
                    note
                    state
                    amountSpent {
                      amount
                      currencyCode
                    }
                  }
                }
              }
            }
        """,
        "products": """
            {
              products {
                edges {
                  node {
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
                    priceRangeV2 {
                      maxVariantPrice { amount }
                      minVariantPrice { amount }
                    }
                    variants(first: 10) {
                      edges {
                        node {
                          id
                          title
                          price
                          inventoryQuantity
                        }
                      }
                    }
                  }
                }
              }
            }
        """,
        "orders": """
            {
              orders {
                edges {
                  node {
                    id
                    name
                    email
                    createdAt
                    displayFinancialStatus
                    totalDiscountsSet { shopMoney { amount currencyCode } }
                    totalPriceSet { shopMoney { amount currencyCode } }
                    lineItems(first: 5) {
                      edges {
                        node {
                          title
                          quantity
                          discountedTotalSet { shopMoney { amount currencyCode } }
                          originalTotalSet { shopMoney { amount currencyCode } }
                        }
                      }
                    }
                    customer {
                      firstName
                      lastName
                      email
                    }
                  }
                }
              }
            }
        """
    }

    mutation = f"""
    mutation {{
      bulkOperationRunQuery(
        query: "{resource_queries[resource]}"
      ) {{
        bulkOperation {{
          id
          status
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    return make_sync_graphql_request(shop, access_token, mutation)


def poll_bulk_operation(shop: str, access_token: str) -> dict:
    """Poll the status of a bulk operation."""
    max_attempts = 200  # ~10 minutes with 3-second intervals
    attempts = 0
    query = """
     {
       currentBulkOperation(type: QUERY) {
         id
         status
         url
         errorCode
         objectCount
         createdAt
         completedAt
       }
     }
     """
    while True:
        if attempts >= max_attempts:
            raise TimeoutError("Bulk operation polling timed out")
        attempts += 1

        result = make_sync_graphql_request(shop, access_token, query)
        if not result or "data" not in result or "currentBulkOperation" not in result["data"]:
            raise ValueError(
                f"Invalid response from bulk operation query: {result}")

        op = result["data"]["currentBulkOperation"]
        if op["status"] in ["COMPLETED", "FAILED", "CANCELED"]:
            return op
        time.sleep(3)


def download_bulk_data(url: str) -> list:
    """Download and parse bulk operation results."""
    response = requests.get(url)
    response.raise_for_status()
    return [json.loads(line) for line in response.text.strip().split("\n") if line]


@shared_task(bind=True, name="pull_all_data")
def pull_all_data(self, shop: str, access_token: str) -> Dict[str, Any]:
    """
    Pull all data (customers, products, orders) from Shopify using bulk operations
    """
    try:
        self.update_state(
            state=states.STARTED,
            meta={
                'current': 0,
                'total': 3,
                'status': 'Starting data pull...'
            }
        )

        # Schedule all subtasks
        customers_task = pull_customers.apply_async(
            args=[shop, access_token], task_id=f"{self.request.id}-customers")
        products_task = pull_products.apply_async(
            args=[shop, access_token], task_id=f"{self.request.id}-products")
        orders_task = pull_orders.apply_async(
            args=[shop, access_token], task_id=f"{self.request.id}-orders")

        # Update state with task IDs
        self.update_state(
            state=states.STARTED,
            meta={
                'current': 0,
                'total': 3,
                'status': 'Tasks scheduled',
                'parent_task_id': self.request.id,
                'subtasks': {
                    'customers': customers_task.id,
                    'products': products_task.id,
                    'orders': orders_task.id
                }
            }
        )

        return {
            'success': True,
            'message': 'Data pull tasks scheduled successfully',
            'task_id': self.request.id,
            'subtasks': {
                'customers': customers_task.id,
                'products': products_task.id,
                'orders': orders_task.id
            }
        }

    except Exception as e:
        logger.error(
            f"Error pulling data for shop {shop}: {str(e)}", exc_info=True)
        self.update_state(
            state=states.FAILURE,
            meta={
                'error': str(e),
                'message': f'Failed to pull data: {str(e)}'
            }
        )
        return {
            'success': False,
            'error': str(e),
            'message': f'Failed to pull data: {str(e)}'
        }
