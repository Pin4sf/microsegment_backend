from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks, Path, Query
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.shop_model import Shop
from app.models.extension_model import Extension
from app.models.event_model import Event
from app.core.cache import redis_client

from app.services.shopify_service import ShopifyClient
from app.schemas.shopify_schemas import (
    GenericResponse,  # For more structured error/success messages
    ShopifyEventRequest,
    ShopifyBulkPullRequest,
)

# For potential future use, not directly needed here now
from app.core.config import settings
from app.tasks.data_pull_tasks import pull_all_data
from app.tasks.ai_tasks import process_product_task, process_order_history_task, batch_process_products_task
import json
from typing import Dict, Any, List

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/event", summary="Handle Shopify Events")
async def handle_shopify_events(
    request_data: ShopifyEventRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Get shop from database
        shop_query = select(Shop).where(
            Shop.shop_domain == request_data.shop["name"])
        result = await db.execute(shop_query)
        shop = result.scalar_one_or_none()

        if not shop:
            logger.error(f"Shop not found: {request_data.shop['name']}")
            raise HTTPException(status_code=404, detail="Shop not found")

        # Get extension from database
        extension_query = select(Extension).where(
            Extension.account_id == request_data.account_id)
        result = await db.execute(extension_query)
        extension = result.scalar_one_or_none()

        if not extension:
            logger.error(
                f"Extension not found for account_id: {request_data.account_id}")
            raise HTTPException(status_code=404, detail="Extension not found")

        # Create event record
        event = Event(
            shop_id=shop.id,
            account_id=request_data.account_id,
            event_name=request_data.event_name,
            payload=request_data.payload
        )

        # Save to database
        db.add(event)
        await db.commit()

        logger.info(
            f"Event {request_data.event_name} stored for shop {request_data.shop['name']}")
        return GenericResponse(success=True, message="Event processed successfully")

    except Exception as e:
        logger.error(f"Error processing event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing event")


@router.post("/bulk-pull", summary="Trigger Full Shopify Data Pull (Customers, Products, Orders)", response_model=Dict[str, Any])
async def trigger_bulk_pull(
    background_tasks: BackgroundTasks,
    request_data: ShopifyBulkPullRequest = Body(...)
):
    """
    Triggers a Celery task to pull all resources (customers, products, orders)
    from the specified Shopify store using bulk operations. The task runs in the background.

    Check the status and results using the task ID(s) returned in the response
    and the /api/data-pull/status/{task_id} and /api/data/shopify/results/{shop}/{task_id} endpoints.
    """
    try:
        task = pull_all_data.delay(
            shop=request_data.shop,
            access_token=request_data.access_token
        )

        return {
            "success": True,
            "message": "Bulk data pull task scheduled",
            "task_id": task.id,
            "status": "PENDING"
        }

    except Exception as e:
        logger.error(f"Error starting data pull: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error starting data pull: {str(e)}"
        )


@router.get(
    "/results/{shop}/{task_id}",
    summary="Get Specific Data Type Results for a Data Pull Task",
    response_model=Dict[str, Any]
)
async def get_data_pull_results(
    shop: str = Path(..., description="The Shopify store domain (e.g., your-store.myshopify.com)."),
    task_id: str = Path(..., description="The Celery task ID for the specific data type pull (e.g., customer, product, or order subtask ID)."),
    data_type: str = Query(...,
                           description="Type of data to retrieve ('customers', 'products', or 'orders').",
                           examples=["customers", "products", "orders"])
):
    """
    Retrieves the results of a completed data pull operation for a specific data type
    (customers, products, or orders) from the Redis cache.

    You must use the task ID of the *specific subtask* for the desired data type
    (e.g., the customer pull task ID), not the ID of the main bulk pull task.
    The subtask IDs are returned in the result/info of the main bulk pull task.

    Args:
        shop: The Shopify store domain.
        task_id: The task ID of the specific data type pull subtask.
        data_type: The type of data to retrieve.
    """
    try:
        # Validate data type
        if data_type not in ["customers", "products", "orders"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid data type. Must be one of: customers, products, orders"
            )

        # Construct Redis key - using the new format including task_id
        redis_key = f"shopify:{data_type}:{shop}:{task_id}"
        logger.info(f"Attempting to get data from Redis with key: {redis_key}")

        # Get data from Redis
        data = redis_client.get(redis_key)

        if not data:
            # Check if the task exists and succeeded but data wasn't saved/expired
            # Optional: Add more checks here against Celery task status
            raise HTTPException(
                status_code=404,
                detail=f"No {data_type} data found for shop {shop} with task ID {task_id}. Results may not be ready, task failed, or data expired."
            )

        # Parse JSON data - Handle both string and bytes data from Redis
        try:
            if isinstance(data, bytes):
            parsed_data = json.loads(data.decode('utf-8'))
            else:
                parsed_data = json.loads(data)
        except json.JSONDecodeError:
            logger.error(
                f"Error parsing cached data for key: {redis_key}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Error parsing cached data. Data in cache is corrupted."
            )
        except Exception as e:
            logger.error(
                f"Unexpected error processing data from Redis for key: {redis_key}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error processing data from cache: {str(e)}"
            )

        return {
            "success": True,
            "message": f"Successfully retrieved {data_type} data for task {task_id}",
            "data": parsed_data
        }

    except HTTPException:
        raise  # Re-raise HTTPExceptions
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving {data_type} data for shop {shop}, task {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while retrieving {data_type} data: {str(e)}"
        )


@router.post(
    "/process-with-ai/{shop}/{task_id}",
    summary="Process Shopify Data with AI",
    response_model=Dict[str, Any]
)
async def process_shopify_data_with_ai(
    shop: str = Path(..., description="The Shopify store domain"),
    task_id: str = Path(...,
                        description="The Celery task ID for the data pull"),
    data_type: str = Query(...,
                           description="Type of data to process ('products' or 'orders')"),
    db: AsyncSession = Depends(get_db)
):
    """
    Process Shopify data through the AI system after it has been pulled.
    This endpoint retrieves the data from Redis and submits it to the AI processing pipeline.

    Args:
        shop: The Shopify store domain
        task_id: The task ID of the data pull
        data_type: The type of data to process ('products' or 'orders')
    """
    try:
        # Validate data type
        if data_type not in ["products", "orders"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid data type. Must be either 'products' or 'orders'"
            )

        # Get data from Redis
        redis_key = f"shopify:{data_type}:{shop}:{task_id}"
        try:
            data = redis_client.get(redis_key)
            if not data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No {data_type} data found for shop {shop} with task ID {task_id}. Data not found in cache."
                )
            # Parse JSON data - Handle both string and bytes data from Redis
            if isinstance(data, bytes):
            parsed_data = json.loads(data.decode('utf-8'))
            else:
                parsed_data = json.loads(data)
        except json.JSONDecodeError:
            logger.error(
                f"Error parsing cached data for key: {redis_key}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Error parsing cached data. Data in cache is corrupted."
            )
        except Exception as e:
            logger.error(
                f"Redis connection error or data retrieval error for key {redis_key}: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving data from cache: {str(e)}")

        # Process based on data type
        if data_type == "products":
            if isinstance(parsed_data, list):
                # Batch process products
                task = batch_process_products_task.delay(
                    parsed_data,
                    f"shopify_outputs/{shop.replace('/', '_').replace('..', '_')}/products"
                )
            else:
                # Single product
                task = process_product_task.delay(parsed_data)
        else:  # orders
            output_dir = f"shopify_outputs/{shop.replace('/', '_').replace('..', '_')}"
            task = process_order_history_task.delay(parsed_data, output_dir)

        return {
            "success": True,
            "message": f"AI processing task started for {data_type}",
            "task_id": task.id,
            "status": "PENDING"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error processing {data_type} with AI: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing {data_type} with AI: {str(e)}"
        )
