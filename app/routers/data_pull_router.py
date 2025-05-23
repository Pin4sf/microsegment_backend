from fastapi import APIRouter, HTTPException, Depends
from app.tasks.data_pull_tasks import pull_all_data, pull_customers, pull_products, pull_orders
from app.core.celery_app import celery_app
from app.core.cache import redis_client
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-pull", tags=["data-pull"])


@router.post("/start")
async def start_data_pull(shop: str, access_token: str):
    """
    Start a full data pull for a Shopify store.
    """
    try:
        # Start the main task
        task = pull_all_data.delay(shop, access_token)

        return {
            "status": "started",
            "task_id": task.id,
            "shop": shop
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_pull_status(task_id: str):
    """
    Get the status of a data pull task.
    """
    try:
        task = celery_app.AsyncResult(task_id)

        if task.state == 'PENDING':
            return {
                "status": "pending",
                "task_id": task_id
            }
        elif task.state == 'STARTED':
            return {
                "status": "in_progress",
                "task_id": task_id,
                "info": task.info
            }
        elif task.state == 'SUCCESS':
            return {
                "status": "completed",
                "task_id": task_id,
                "result": task.result
            }
        else:
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(task.info)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{shop}/{task_id}")
async def get_pull_results(shop: str, task_id: str, data_type: str):
    """
    Get the results of a completed data pull.
    """
    try:
        # Get data from Redis
        redis_key = f"{data_type}_pull:{shop}:{task_id}"
        logger.info(f"Attempting to get data from Redis with key: {redis_key}")
        data = redis_client.get(redis_key)

        if data is None:
            # If data is not found in Redis, return a 404 Not Found response directly
            raise HTTPException(
                status_code=404, detail="Results not found or expired")

        logger.info(
            f"Successfully retrieved data from Redis (length: {len(data) if data else 0})")
        # Decode the bytes from Redis to a string before loading as JSON
        try:
            decoded_data = data.decode('utf-8')
            logger.info("Successfully decoded data from Redis")
        except Exception as decode_error:
            logger.error(
                f"Error decoding data from Redis for key {redis_key}: {decode_error}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error decoding data from Redis: {decode_error}")

        try:
            return {
                "status": "success",
                "data": json.loads(decoded_data)
            }
        except json.JSONDecodeError as json_error:
            logger.error(
                f"Error decoding JSON from Redis data for key {redis_key}: {json_error}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error decoding JSON data from Redis: {json_error}")
        except Exception as return_error:
            logger.error(
                f"Unexpected error after JSON decode for key {redis_key}: {return_error}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Unexpected error processing data: {return_error}")
    except HTTPException as http_exc:
        # Re-raise HTTPException so FastAPI handles it correctly (404 in this case)
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors and log the full traceback
        logger.error(
            f"Unexpected error in get_pull_results for key {redis_key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/customers")
async def start_customer_pull(shop: str, access_token: str, batch_size: int = 100):
    """
    Start a customer data pull.
    """
    try:
        task = pull_customers.delay(shop, access_token, batch_size)
        return {
            "status": "started",
            "task_id": task.id,
            "shop": shop
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products")
async def start_product_pull(shop: str, access_token: str, batch_size: int = 100):
    """
    Start a product data pull.
    """
    try:
        task = pull_products.delay(shop, access_token, batch_size)
        return {
            "status": "started",
            "task_id": task.id,
            "shop": shop
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders")
async def start_order_pull(shop: str, access_token: str, batch_size: int = 100):
    """
    Start an order data pull.
    """
    try:
        task = pull_orders.delay(shop, access_token, batch_size)
        return {
            "status": "started",
            "task_id": task.id,
            "shop": shop
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
