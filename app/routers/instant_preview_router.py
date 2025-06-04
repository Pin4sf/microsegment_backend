from fastapi import APIRouter, HTTPException, Body
# Assuming a schema for the URL
from app.schemas.shopify_schemas import InstantPreviewURLRequest
from app.services.shopify_preview_service import verify_shopify_url, get_store_public_info
from app.services.ai_service import AIService
import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/instant-preview", tags=["instant-preview"])


@router.post("/analyze-store", response_model=Dict[str, Any])
async def analyze_store_preview(
    store_url_data: InstantPreviewURLRequest = Body(...),
):
    """
    Analyzes a Shopify store's public information and provides AI-powered insights
    like high-value market segments and product categories for instant preview UI.

    This endpoint does NOT process product data or use the MicroSegment class.
    It uses the Perplexity API via AIService.analyze_store_for_preview.
    """
    store_url = store_url_data.store_url

    logger.info(f"Received request to analyze store preview for: {store_url}")

    # 1. Verify the store URL
    is_valid = await verify_shopify_url(store_url)
    if not is_valid:
        logger.warning(
            f"Invalid or unverified Shopify store URL received: {store_url}")
        raise HTTPException(
            status_code=400,
            detail="Invalid or unverified Shopify store URL."
        )

    # 2. Fetch comprehensive public store information
    store_details = await get_store_public_info(store_url)
    logger.info(f"Fetched basic store details for {store_url}")

    # 3. Use AIService to get insights (Segments and Categories) from Perplexity API
    ai_service = AIService()  # Instantiate or get singleton instance
    ai_insights = ai_service.analyze_store_for_preview(store_details)
    logger.info(f"Received AI insights for {store_url}")

    # 4. Combine results for the response, checking for AI analysis errors
    response_data = {
        "store_preview_details": {
            "name": store_details.get("name"),
            "description": store_details.get("description"),
            "logo": store_details.get("branding", {}).get("logo"),
            "favicon": store_details.get("favicon"),
            "url": store_details.get("url"),
            # Include other extracted store_details as needed for the UI card
            "social_media": store_details.get("social_media"),
            "contact_info": store_details.get("contact_info"),
            "language": store_details.get("language"),
            "currency": store_details.get("currency"),
        },
        "ai_analysis": {
            "high_value_segments": ai_insights.get("high_value_segments", []),
            "product_categories": ai_insights.get("product_categories", []),
            # Pass AI status and error info from the service function
            "ai_status": ai_insights.get("ai_status", "success"),
            "ai_error": ai_insights.get("ai_error")
        },
        "status": "SUCCESS",  # Overall request status
        "message": "Store details and AI analysis fetched successfully."
    }

    # Adjust overall status based on AI analysis outcome
    if ai_insights.get("ai_status") != "success":
        response_data["status"] = "PARTIAL_SUCCESS"
        response_data["message"] = response_data["ai_analysis"].get(
            "ai_error", "AI analysis failed.")

    return response_data
