from fastapi import APIRouter, HTTPException, Depends, Path
from app.tasks.data_pull_tasks import pull_all_data, pull_customers, pull_products, pull_orders
from app.core.celery_app import celery_app
from app.core.cache import redis_client
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-pull", tags=["data-pull"])


@router.get(
    "/status/{task_id}",
    summary="Get Data Pull Task Status",
    response_model=Dict[str, Any]
)
async def get_pull_status(
    task_id: str = Path(...,
                        description="The Celery task ID to check the status for.")
):
    """
    Get the current status of any data pull-related Celery task by its task ID.
    This can be the ID of the main bulk pull task or one of the specific
    data type subtasks (customers, products, orders).

    Possible statuses include 'PENDING', 'STARTED', 'IN_PROGRESS', 'SUCCESS', 'FAILED'.

    Args:
        task_id: The unique ID of the Celery task.
    """
    try:
        task = celery_app.AsyncResult(task_id)

        response_data: Dict[str, Any] = {
            "task_id": task_id,
            "status": task.state,
        }

        if task.state == 'STARTED':
            response_data["info"] = task.info
        elif task.state == 'SUCCESS':
            response_data["result_summary"] = "Result available via /api/data/shopify/results"
            if isinstance(task.result, dict) and 'count' in task.result:
                response_data["result_summary"] = f"Completed successfully. Count: {task.result['count']}. Get data via /api/data/shopify/results."

        elif task.state in ('FAILURE', 'REVOKED'):
            response_data["error"] = str(task.info)
            response_data["message"] = "Task failed or was revoked."

        return response_data

    except Exception as e:
        logger.error(
            f"Error getting task status for {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving task status: {str(e)}")
