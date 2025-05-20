from fastapi import APIRouter, HTTPException, Body
import logging
import httpx

from app.services.shopify_service import ShopifyClient
from app.schemas.shopify_schemas import (
    ShopifyDataRequest,
    ShopifyProductResponse,
    ShopifyOrderResponse,
    ShopifyTransactionRequest,
    ShopifyTransactionResponse,
    ShopifyCustomerResponse,
    GenericResponse,  # For more structured error/success messages
    ShopifyEventRequest,
)

# For potential future use, not directly needed here now
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def _handle_shopify_request(
    request_data: ShopifyDataRequest, fetch_method_name: str, response_model, **kwargs
):
    """Helper function to handle Shopify data requests to reduce boilerplate."""
    try:
        client = ShopifyClient(
            shop=request_data.shop, access_token=request_data.access_token
        )
        fetch_method = getattr(client, fetch_method_name)

        # Prepare arguments for the fetch method
        method_args = {
            "first": request_data.first,
            "cursor": request_data.cursor,
        }
        # Only add custom_query_filter if it's not for transactions or other specific methods
        if fetch_method_name not in ["get_transactions"]:
            method_args["custom_query_filter"] = request_data.custom_query

        # Add specific args like order_id if present in kwargs
        method_args.update(kwargs)

        raw_response = await fetch_method(**method_args)

        if raw_response and "data" in raw_response:
            # The response models expect the data to be under a specific key like "products" or "orders"
            # The actual key in raw_response["data"] will be, e.g., "products" or "orders" or "node" for transactions
            # We need to map this correctly to the Pydantic response model.

            data_content = raw_response["data"]

            if fetch_method_name == "get_products" and "products" in data_content:
                return ShopifyProductResponse(
                    products=data_content["products"],
                    success=True,
                    message="Products fetched successfully.",
                )
            elif fetch_method_name == "get_orders" and "orders" in data_content:
                return ShopifyOrderResponse(
                    orders=data_content["orders"],
                    success=True,
                    message="Orders fetched successfully.",
                )
            elif fetch_method_name == "get_customers" and "customers" in data_content:
                return ShopifyCustomerResponse(
                    customers=data_content["customers"],
                    success=True,
                    message="Customers fetched successfully.",
                )
            elif (
                fetch_method_name == "get_transactions"
                and "node" in data_content
                and data_content["node"]
                and "transactions" in data_content["node"]
            ):
                # Transactions are now a direct list
                return ShopifyTransactionResponse(
                    transactions=data_content["node"]["transactions"],
                    success=True,
                    message="Transactions fetched successfully.",
                )
            elif (
                fetch_method_name == "get_transactions"
                and "node" in data_content
                and data_content["node"] is None
            ):
                logger.warning(
                    f"Order node not found for ID {kwargs.get('order_id')} when fetching transactions."
                )
                return response_model(
                    success=False,
                    message=f"Order with ID {kwargs.get('order_id')} not found or has no transactions.",
                    data=None,
                )
            else:
                # Fallback or if the structure is unexpected
                logger.warning(
                    f"Unexpected data structure from {fetch_method_name} for shop {request_data.shop}: {data_content}"
                )
                return response_model(
                    success=False,
                    message="Data fetched but structure was unexpected.",
                    data=data_content,
                )

        elif raw_response and "errors" in raw_response:
            logger.error(
                f"GraphQL errors for {fetch_method_name} for shop {request_data.shop}: {raw_response['errors']}"
            )
            return response_model(
                success=False,
                message=f"GraphQL error: {raw_response['errors'][0]['message']}",
                data=raw_response,
            )
        else:
            logger.error(
                f"No data or unexpected response from {fetch_method_name} for shop {request_data.shop}"
            )
            return response_model(
                success=False,
                message="Failed to fetch data from Shopify or empty response.",
                data=raw_response,
            )

    except ValueError as ve:
        logger.error(
            f"ValueError in {fetch_method_name} for shop {request_data.shop}: {ve}"
        )
        raise HTTPException(status_code=400, detail=str(ve))
    except httpx.HTTPStatusError as hse:
        logger.error(
            f"HTTPStatusError in {fetch_method_name} for shop {request_data.shop}: {hse.response.text}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=hse.response.status_code,
            detail=f"Shopify API error: {hse.response.text}",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in {fetch_method_name} for shop {request_data.shop}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching {fetch_method_name.split('_')[-1]}.",
        )


@router.post(
    "/products", response_model=ShopifyProductResponse, summary="Fetch Shopify Products"
)
async def get_shopify_products(request_data: ShopifyDataRequest = Body(...)):
    """
    Fetches a list of products from the specified Shopify store.
    Requires shop domain, access token, and supports pagination (cursor, first) and custom query filters.
    """
    return await _handle_shopify_request(
        request_data, "get_products", ShopifyProductResponse
    )


@router.post(
    "/orders", response_model=ShopifyOrderResponse, summary="Fetch Shopify Orders"
)
async def get_shopify_orders(request_data: ShopifyDataRequest = Body(...)):
    """
    Fetches a list of orders from the specified Shopify store.
    Requires shop domain, access token, and supports pagination (cursor, first) and custom query filters.
    """
    return await _handle_shopify_request(
        request_data, "get_orders", ShopifyOrderResponse
    )


@router.post(
    "/transactions",
    response_model=ShopifyTransactionResponse,
    summary="Fetch Shopify Transactions for an Order",
)
async def get_shopify_transactions(request_data: ShopifyTransactionRequest = Body(...)):
    """
    Fetches a list of transactions for a specific order from the Shopify store.
    Requires shop domain, access token, order ID, and supports pagination (cursor, first).
    """
    return await _handle_shopify_request(
        request_data,
        "get_transactions",
        ShopifyTransactionResponse,
        order_id=request_data.order_id,
    )


@router.post(
    "/customers",
    response_model=ShopifyCustomerResponse,
    summary="Fetch Shopify Customers",
)
async def get_shopify_customers(request_data: ShopifyDataRequest = Body(...)):
    """
    Fetches a list of customers from the specified Shopify store.
    Requires shop domain, access token, and supports pagination (cursor, first) and custom query filters.
    """
    return await _handle_shopify_request(
        request_data, "get_customers", ShopifyCustomerResponse
    )


@router.post("/event", summary="Handle Shopify Events")
async def handle_shopify_events(request_data: ShopifyEventRequest = Body(...)):
    print(f"Event {request_data.event_name} Triggered on", request_data.shop["name"])
    print("Account ID", request_data.account_id)
    print("Event Payload", request_data.payload)
    # TODO: process and store event payload in DB
    return GenericResponse(success=True, message="Event handled from fastapi!")
