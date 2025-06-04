# app/tasks/webhook_tasks.py
from app.core.celery_app import celery_app
from app.core.cache import redis_client
from celery import states
import logging
import httpx
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


async def shopify_graphql_query(shop_domain: str, access_token: str, query: str, variables: Optional[Dict] = None) -> Dict:
    """Make an authenticated request to Shopify's Admin GraphQL API."""
    url = f"https://{shop_domain}/admin/api/2025-04/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


@celery_app.task(bind=True, max_retries=3)
def process_customer_data_request(self, shop_domain: str, payload: dict):
    """Process a customer data request webhook."""
    try:
        self.update_state(state=states.STARTED, meta={
                          'status': 'Processing customer data request'})

        customer_id = payload["customer"]["id"]
        order_ids = payload.get("orders_requested", [])

        # Get shop access token from your secure storage
        access_token = get_shop_access_token(shop_domain)

        # Fetch customer data from Shopify
        customer_gid = f"gid://shopify/Customer/{customer_id}"
        query = """
        query GetCustomerAndOrders($customerId: ID!) {
          customer(id: $customerId) {
            id
            email
            firstName
            lastName
            orders(first: 100) {
              edges {
                node {
                  id
                  name
                  totalPriceSet {
                    shopMoney {
                      amount
                      currencyCode
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"customerId": customer_gid}
        # Execute query
        customer_data = shopify_graphql_query(
            shop_domain, access_token, query, variables)

        # Store the data request in your database
        store_data_request(shop_domain, customer_id, customer_data)

        self.update_state(state=states.SUCCESS, meta={
                          'status': 'Customer data request processed'})

    except Exception as exc:
        logger.error(f"Error processing customer data request: {exc}")
        self.update_state(state=states.FAILURE, meta={
                          'status': 'Failed', 'error': str(exc)})
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def process_customer_redact(self, shop_domain: str, payload: dict):
    """Process a customer redact webhook."""
    try:
        self.update_state(state=states.STARTED, meta={
                          'status': 'Processing customer redact request'})

        customer_id = payload["customer"]["id"]
        order_ids = payload.get("orders_to_redact", [])

        # Get shop access token
        access_token = get_shop_access_token(shop_domain)

        # 1. Delete customer data from your database
        delete_customer_data(shop_domain, customer_id)

        # 2. Delete customer metafields from Shopify
        customer_gid = f"gid://shopify/Customer/{customer_id}"
        metafields_query = """
        query GetCustomerMetafields($customerId: ID!) {
          customer(id: $customerId) {
            metafields(first: 50) {
              edges {
                node {
                  id
                }
              }
            }
          }
        }
        """
        variables = {"customerId": customer_gid}
        metafields_data = shopify_graphql_query(
            shop_domain, access_token, metafields_query, variables)

        # Delete each metafield
        for edge in metafields_data.get("data", {}).get("customer", {}).get("metafields", {}).get("edges", []):
            metafield_id = edge["node"]["id"]
            delete_mutation = """
            mutation DeleteMetafield($id: ID!) {
              metafieldDelete(input: { id: $id }) {
                deletedId
                userErrors {
                  field
                  message
                }
              }
            }
            """
            variables = {"id": metafield_id}
            shopify_graphql_query(shop_domain, access_token,
                                  delete_mutation, variables)

        self.update_state(state=states.SUCCESS, meta={
                          'status': 'Customer data redacted'})

    except Exception as exc:
        logger.error(f"Error processing customer redact request: {exc}")
        self.update_state(state=states.FAILURE, meta={
                          'status': 'Failed', 'error': str(exc)})
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def process_shop_redact(self, shop_domain: str, payload: dict):
    """Process a shop redact webhook."""
    try:
        self.update_state(state=states.STARTED, meta={
                          'status': 'Processing shop redact request'})

        # Delete all shop data from your database
        delete_shop_data(shop_domain)

        self.update_state(state=states.SUCCESS, meta={
                          'status': 'Shop data redacted'})

    except Exception as exc:
        logger.error(f"Error processing shop redact request: {exc}")
        self.update_state(state=states.FAILURE, meta={
                          'status': 'Failed', 'error': str(exc)})
        self.retry(exc=exc, countdown=60)

# Helper functions (implement these based on your database structure)


def get_shop_access_token(shop_domain: str) -> str:
    """Get the access token for a shop from your secure storage."""
    # Implement this based on your token storage solution
    pass


def store_data_request(shop_domain: str, customer_id: int, data: dict):
    """Store the data request in your database."""
    # Implement this based on your database structure
    pass


def delete_customer_data(shop_domain: str, customer_id: int):
    """Delete customer data from your database."""
    # Implement this based on your database structure
    pass


def delete_shop_data(shop_domain: str):
    """Delete all shop data from your database."""
    # Implement this based on your database structure
    pass
