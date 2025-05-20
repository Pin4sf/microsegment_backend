import httpx
import hashlib
import hmac
import time
from urllib.parse import urlencode, parse_qs
import ssl
import certifi
import json
from app.core.config import settings
import logging
from app.utils.shopify_utils import generate_id

logger = logging.getLogger(__name__)


class ShopifyClient:
    """A client for interacting with the Shopify API, handling OAuth and data fetching."""

    def __init__(self, shop: str, access_token: str = None):
        """
        Initializes the ShopifyClient.

        Args:
            shop: The shop domain (e.g., your-store.myshopify.com).
            access_token: The Shopify access token for the shop (optional).
        """
        if not shop:
            raise ValueError("Shop domain cannot be empty.")
        self.shop = shop.strip()
        self.access_token = access_token
        self.api_version = settings.SHOPIFY_API_VERSION
        self.base_url = f"https://{self.shop}/admin/api/{self.api_version}"
        self.graphql_url = f"{self.base_url}/graphql.json"

    def _validate_hmac(self, params: dict) -> bool:
        """Validates the HMAC signature from Shopify callback."""
        if "hmac" not in params:
            return False

        received_hmac = params.pop("hmac")
        message = urlencode(sorted(params.items()))

        calculated_hmac = hmac.new(
            settings.SHOPIFY_API_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(calculated_hmac, received_hmac)

    def get_authorize_url(self, state: str = None) -> str:
        """
        Generates the Shopify authorization URL to initiate the OAuth flow.
        """
        if not state:
            state = str(int(time.time()))

        query_params = {
            "client_id": settings.SHOPIFY_API_KEY,
            "scope": settings.SHOPIFY_APP_SCOPES,
            "redirect_uri": settings.SHOPIFY_REDIRECT_URI,
            "state": state,
            "grant_options[]": "per-user",
        }
        return f"https://{self.shop}/admin/oauth/authorize?{urlencode(query_params)}"

    async def exchange_code_for_token(
        self, code: str, received_params: dict
    ) -> str | None:
        """
        Exchanges an authorization code for an access token.
        """
        if not self._validate_hmac(received_params.copy()):
            logger.error(f"HMAC validation failed for shop {self.shop}")
            return None

        if received_params.get("shop") != self.shop:
            logger.error(
                f"Shop domain mismatch during token exchange. Expected {self.shop}, got {received_params.get('shop')}"
            )
            return None

        token_url = f"https://{self.shop}/admin/oauth/access_token"
        payload = {
            "client_id": settings.SHOPIFY_API_KEY,
            "client_secret": settings.SHOPIFY_API_SECRET,
            "code": code,
        }

        # Create an SSL context that uses certifi's CA bundle
        # ssl_context = ssl.create_default_context(cafile=certifi.where())

        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.post(token_url, json=payload)
                response.raise_for_status()
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                logger.info(
                    f"Successfully obtained access token for shop: {self.shop}")
                return self.access_token
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error during token exchange for {self.shop}: {e.response.status_code} - {e.response.text}"
                )
            except httpx.RequestError as e:
                logger.error(
                    f"Request error during token exchange for {self.shop}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during token exchange for {self.shop}: {e}"
                )
        return None

    async def make_graphql_request(
        self, query: str, variables: dict = None
    ) -> dict | None:
        """
        Makes an authenticated GraphQL request to the Shopify API.
        """
        if not self.access_token:
            logger.error(
                f"Access token not available for shop {self.shop}. Cannot make GraphQL request."
            )
            # Consider raising an exception here
            return None

        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        # Create an SSL context that uses certifi's CA bundle
        # ssl_context = ssl.create_default_context(cafile=certifi.where())

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            try:
                logger.debug(
                    f"Making GraphQL request to {self.graphql_url} for shop {self.shop} with payload: {payload}"
                )
                response = await client.post(
                    self.graphql_url, headers=headers, json=payload
                )
                response.raise_for_status()
                response_data = response.json()
                if response_data.get("errors"):
                    logger.error(
                        f"GraphQL errors for shop {self.shop}: {response_data['errors']}"
                    )
                return response_data  # Return full response, let caller extract 'data'
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error during GraphQL request for {self.shop}: {e.response.status_code} - {e.response.text}"
                )
            except httpx.RequestError as e:
                logger.error(
                    f"Request error during GraphQL request for {self.shop}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during GraphQL request for {self.shop}: {e}",
                    exc_info=True,
                )
        return None

    async def get_products(
        self, first: int = 10, cursor: str = None, custom_query_filter: str = None
    ):
        """Fetches products from Shopify using GraphQL with pagination and custom query."""
        query_parts = []
        if cursor:
            query_parts.append(f'after: "{cursor}"')
        if custom_query_filter:
            # Ensure custom_query_filter is properly escaped if it contains special characters
            # For simplicity, assuming it's a simple string here.
            query_parts.append(f'query: "{custom_query_filter}"')

        product_params = f"first: {first}" + (
            ", " + ", ".join(query_parts) if query_parts else ""
        )

        query = f"""
        query {{
          products({product_params}) {{
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
        logger.info(
            f"Fetching products for shop {self.shop} with params: first={first}, cursor={cursor}, query_filter={custom_query_filter}"
        )
        return await self.make_graphql_request(query)

    async def get_orders(
        self, first: int = 10, cursor: str = None, custom_query_filter: str = None
    ):
        """Fetches orders from Shopify using GraphQL with pagination and custom query."""
        query_parts = []
        if cursor:
            query_parts.append(f'after: "{cursor}"')
        if custom_query_filter:
            query_parts.append(f'query: "{custom_query_filter}"')

        order_params = f"first: {first}" + (
            ", " + ", ".join(query_parts) if query_parts else ""
        )

        query = f"""
        query {{
          orders({order_params}) {{
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
        logger.info(
            f"Fetching orders for shop {self.shop} with params: first={first}, cursor={cursor}, query_filter={custom_query_filter}"
        )
        return await self.make_graphql_request(query)

    async def get_transactions(
        self, order_id: str, first: int = 10, cursor: str = None
    ):
        """
        Fetches transactions for a specific order from Shopify using GraphQL.
        The transactions field on Order returns a list, not a standard connection.
        The 'cursor' argument is kept in the method signature for potential future API changes
        or alternative pagination methods but is not used in the current GraphQL query for transactions.
        """
        # This is a common way to get transactions for an order:
        query = f"""
        query GetOrderTransactions($orderId: ID!, $first: Int!) {{
          node(id: $orderId) {{
            ... on Order {{
              id
              name
              transactions(first: $first) {{ # Removed 'after: $cursor'
                # Direct fields from OrderTransaction, no edges/node/cursor/pageInfo
                id
                kind
                status
                amountSet {{ shopMoney {{ amount currencyCode }} }}
                createdAt
                # Add more fields as needed from the Transaction object
                # e.g., gateway, test, fees, paymentDetails, etc.
              }}
            }}
          }}
        }}
        """
        variables = {"orderId": order_id, "first": first}
        # Cursor is not used in this specific query for transactions as it's a direct list.
        # logger.info(f"Fetching transactions for order {order_id} in shop {self.shop} with params: first={first}, cursor={cursor (if used)}")
        logger.info(
            f"Fetching transactions for order {order_id} in shop {self.shop} with params: first={first}"
        )
        # The result will be nested under node.transactions if the order is found.
        return await self.make_graphql_request(query, variables)

    async def get_customers(
        self, first: int = 10, cursor: str = None, custom_query_filter: str = None
    ):
        """Fetches customers from Shopify using GraphQL with pagination and custom query."""
        query_parts = []
        if cursor:
            query_parts.append(f'after: "{cursor}"')
        if custom_query_filter:
            # Ensure custom_query_filter is properly escaped if it contains special characters
            query_parts.append(f'query: "{custom_query_filter}"')

        customer_params = f"first: {first}" + (
            ", " + ", ".join(query_parts) if query_parts else ""
        )

        query = f"""
        query {{
          customers({customer_params}) {{
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
        logger.info(
            f"Fetching customers for shop {self.shop} with params: first={first}, cursor={cursor}, query_filter={custom_query_filter}"
        )
        return await self.make_graphql_request(query)

    async def activate_webpixel_extension(self):

        query = """
        mutation webPixelCreate($webPixel: WebPixelInput!) {
            webPixelCreate(webPixel: $webPixel) {
            userErrors {
                field
                message
                code
            }
            webPixel {
                id
                settings
            }
            }
        }
        """
        variables = {"webPixel": {
            "settings": json.dumps({"accountID": generate_id()})}}
        return await self.make_graphql_request(query, variables)

    async def update_extension(self, extension_id):
        query = """
        mutation webPixelUpdate($id: ID!, $webPixel: WebPixelInput!) {
        webPixelUpdate(id: $id, webPixel: $webPixel) {
            userErrors {
            field
            message
            code
            }
            webPixel {
            id
            settings
            }
        }
        }
        """

        variables = {
            "id": extension_id,
            "webPixel": {"settings": json.dumps({"accountID": generate_id()})},
        }
        return await self.make_graphql_request(query, variables)
