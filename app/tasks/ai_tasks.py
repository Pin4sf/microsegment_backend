from typing import Dict, List, Optional
from app.core.celery_app import celery_app
from app.services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="process_product_ai")
def process_product_task(product_data: Dict) -> Dict:
    """Celery task for processing a single product."""
    try:
        return ai_service.microsegment.process_product(product_data)
    except Exception as e:
        logger.error(
            "Error processing product in Celery task",
            extra={
                "error": str(e),
                "product_title": product_data.get("title", "Unknown"),
                "product_handle": product_data.get("handle", "Unknown")
            },
            exc_info=True
        )
        raise  # Re-raise the exception to mark the task as failed


@celery_app.task(name="process_order_history_ai")
def process_order_history_task(order_history: Dict, output_dir: str = None) -> Dict:
    """Celery task for processing order history."""
    try:
        return ai_service.microsegment.process_order_history(order_history, output_dir)
    except Exception as e:
        logger.error(f"Error processing order history: {str(e)}")
        raise


@celery_app.task(name="batch_process_products_ai")
def batch_process_products_task(products: List[Dict], output_dir: str = "outputs") -> List[Dict]:
    """Celery task for batch processing products."""
    try:
        if not products:
            raise ValueError("Products list cannot be empty")
        return ai_service.microsegment.batch_process_products(products, output_dir)
    except Exception as e:
        logger.error(f"Error batch processing products: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error batch processing products: {str(e)}")
        raise
