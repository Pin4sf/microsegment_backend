from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.ai_schemas import (
    ProductAIRequest,
    OrderHistoryAIRequest,
    AIProcessingResponse,
    BatchProcessingRequest
)
from app.tasks.ai_tasks import (
    process_product_task,
    process_order_history_task,
    batch_process_products_task
)
from app.core.celery_app import celery_app
from celery.result import AsyncResult

router = APIRouter(tags=["AI Processing"])


@router.post("/products/process", response_model=AIProcessingResponse)
async def process_product(product: ProductAIRequest):
    """Submit a product for AI processing."""
    try:
        task = process_product_task.delay(
            product.model_dump())  # keep field names
        return {
            "task_id": task.id,
            "status": "PENDING"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/process", response_model=AIProcessingResponse)
async def process_order_history(order_history: OrderHistoryAIRequest):
    """Submit order history for AI processing."""
    try:
        task = process_order_history_task.delay(order_history.model_dump())
        return {
            "task_id": task.id,
            "status": "PENDING"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products/batch", response_model=AIProcessingResponse)
async def batch_process_products(batch_request: BatchProcessingRequest):
    """Submit multiple products for batch processing."""
    try:
        task = batch_process_products_task.delay(
            [p.model_dump(by_alias=True) for p in batch_request.products],
            batch_request.output_dir
        )
        return {
            "task_id": task.id,
            "status": "PENDING"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=AIProcessingResponse)
async def get_task_status(task_id: str):
    """Get the status of an AI processing task."""
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task_result.status
    }

    if task_result.ready():
        if task_result.successful():
            # Handle both single and batch results
            result = task_result.result
            if isinstance(result, list):
                response["result"] = {"products": result}
            else:
                response["result"] = result
        else:
            response["error"] = str(task_result.result)

    return response
