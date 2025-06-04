from typing import Dict, List, Optional, Any
import logging
from app.core.config import settings
from app.ai.microsegment import MicroSegment
from app.core.celery_app import celery_app
import json
import re
import os
import requests
from requests.exceptions import RequestException, HTTPError

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.microsegment = MicroSegment()
        # Initialize your AI client here
        # self.ai_client = AIClient(api_key=settings.OPENROUTER_API_KEY)
        self.api_key: Optional[str] = settings.PERPLEXITY_API_KEY
        if not self.api_key:
            logger.error(
                "PERPLEXITY_API_KEY environment variable not set. AI analysis will fail.")
            # Decide how to handle this: could raise an error here or handle it in the analysis method.
            # Handling it in the method allows the application to start even if the key is missing.

        # Initialize an asynchronous HTTP client for making API requests
        # Using a context manager (async with) in the method is also an option,
        # but keeping the client here allows potential connection pooling benefits
        # if the service instance is reused (e.g., via FastAPI Depends).
        # However, for simplicity and avoiding complex shutdown logic, let's create
        # the client within the method using a context manager for now.
        # self._httpx_client = httpx.AsyncClient()

        logger.info("AIService initialized.")

    def process_product(self, product_data: Dict) -> Dict:
        """Process a single product using AI."""
        try:
            return self.microsegment.process_product(product_data)
        except Exception as e:
            logger.error(
                "Error processing product in AIService",
                extra={
                    "error": str(e),
                    "product_title": product_data.get("title", "Unknown"),
                    "product_handle": product_data.get("handle", "Unknown")
                },
                exc_info=True
            )
            return {"error": f"Failed to process product: {str(e)}"}

    def process_order_history(self, order_history: Dict) -> Dict:
        """Process order history using AI."""
        try:
            return self.microsegment.process_order_history(order_history)
        except Exception as e:
            logger.error(
                "Error processing order history in AIService",
                extra={
                    "error": str(e),
                    "order_count": len(order_history.get("orders", [])),
                    "customer_id": order_history.get("customer_id", "Unknown")
                },
                exc_info=True
            )
            return {"error": f"Failed to process order history: {str(e)}"}

    def batch_process_products(self, products: List[Dict], output_dir: str = "outputs") -> List[Dict]:
        """Process multiple products in batch."""
        try:
            if not products:
                raise ValueError("Products list cannot be empty")
            return self.microsegment.batch_process_products(products, output_dir)
        except Exception as e:
            logger.error(
                "Error batch processing products in AIService",
                extra={
                    "error": str(e),
                    "product_count": len(products),
                    "output_dir": output_dir
                },
                exc_info=True
            )
            return [{"error": f"Failed to batch process products: {str(e)}"}]

    def analyze_store_for_preview(self, store_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes public store information using Perplexity's Sonar API to identify
        high-value market segments and product categories (using synchronous requests).

        Args:
            store_details: A dictionary containing public store information
                           fetched by get_store_public_info.

        Returns:
            A dictionary containing lists of high-value segments and product categories
            if successful. Returns an error message if the API call or parsing fails.
            Example success: {"high_value_segments": ["...", "..."], "product_categories": ["...", "..."]}
            Example failure: {"ai_error": "...", "ai_status": "failed", ...}
        """
        logger.info(f"Starting AI analysis for store preview (synchronous).")

        if not self.api_key:
            logger.error(
                "Perplexity API key not configured in settings. Cannot perform AI analysis.")
            return {
                "high_value_segments": [],
                "product_categories": [],
                "ai_error": "Perplexity API key not configured.",
                "ai_status": "failed_auth"
            }

        # 1. Construct the prompt for the AI model
        prompt_text = f"""
        You are an expert e-commerce analyst. Analyze the following online store information and identify:

        1. HIGH-VALUE MARKET SEGMENTS: Identify the primary customer demographics and psychographics most likely to purchase from this store. Be specific and actionable (e.g., "Eco-conscious Millennials interested in sustainable clothing").
        2. PRODUCT CATEGORIES: List the main product lines, collections, and offerings available. Be precise (e.g., "Handmade Ceramic Mugs", "Organic Cotton T-shirts").

        Store Information:
        - Store Name: {store_details.get('name', 'N/A')}
        - Description: {store_details.get('description', 'N/A')}
        - URL: {store_details.get('url', 'N/A')}
        - Keywords: {', '.join(store_details.get('metadata', {}).get('keywords', []))}
        - Navigation Menu: {', '.join([item.get('text', '') for item in store_details.get('navigation', {}).get('main_menu', []) if item and item.get('text')])}
        - Collections: {', '.join(store_details.get('collections', []))}
        - Extracted Features: {', '.join(store_details.get('store_features', []))}


        Based on this information, provide your findings in the following JSON format ONLY. Do not include any other text or formatting outside the JSON object:
        {{
            "high_value_segments": ["segment1", "segment2", "segment3", "segmentN"],
            "product_categories": ["category1", "category2", "category3", "categoryN"]
        }}

        Be specific and actionable in your analysis. Focus on demographics, lifestyle, and purchasing behavior for segments.
        For categories, be precise about product types and groupings.
        """

        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        # 2. Corrected payload structure based on your analysis
        payload = {
            "model": "sonar",  # Changed from "sonar-pro" to "sonar"
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert e-commerce analyst. Return ONLY valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt_text
                }
            ],
            "response_format": {
                "type": "json_schema",  # Changed from "json_object" to "json_schema"
                "json_schema": {        # Added json_schema wrapper
                    "schema": {
                        "type": "object",
                        "properties": {
                            "high_value_segments": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "product_categories": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["high_value_segments", "product_categories"]
                    }
                }
            },
            "temperature": 0.3,
            "max_tokens": 1000,
            # Removed "top_p": 0.95 as suggested
        }

        try:
            # 3. Call Perplexity API using requests (synchronous)
            logger.debug(
                f"Sending prompt to Perplexity Sonar API via requests")

            # Using requests.post (synchronous)
            response = requests.post(
                url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()

            ai_response = response.json()

            # 4. Parse the AI response
            raw_ai_output = ai_response["choices"][0]["message"]["content"].strip(
            )
            logger.debug(f"Received raw AI output:\n{raw_ai_output}")

            # Clean potential markdown code blocks
            clean_output = re.sub(r'^```json\s*|\s*```$',
                                  '', raw_ai_output.strip())
            clean_output = re.sub(r'^```\s*|\s*```$', '', clean_output)

            parsed_response = json.loads(clean_output)

            # 5. Add validation for response structure
            if not isinstance(parsed_response.get("high_value_segments"), list) or \
               not isinstance(parsed_response.get("product_categories"), list):
                logger.error(
                    f"Invalid response structure from API: {parsed_response}")
                return {
                    "high_value_segments": [],
                    "product_categories": [],
                    "ai_error": "Invalid response structure from AI API.",
                    "ai_status": "failed_parsing"
                }

            segments = parsed_response.get("high_value_segments", [])
            categories = parsed_response.get("product_categories", [])

            # Basic cleaning of list items (already present, keeping)
            segments = [seg.strip() for seg in segments if isinstance(
                seg, str) and seg.strip()]
            categories = [cat.strip() for cat in categories if isinstance(
                cat, str) and cat.strip()]

            logger.info(
                f"Successfully parsed segments: {segments}, categories: {categories}")

            # 6. Return the parsed results
            return {
                "high_value_segments": segments,
                "product_categories": categories,
                "ai_status": "success"
            }

        # Catch requests exceptions
        except (HTTPError, RequestException, json.JSONDecodeError, AttributeError, TypeError) as e:
            # Note: requests.exceptions.RequestException is the base class
            # requests.exceptions.HTTPError is for 4xx/5xx responses
            logger.error(f"AI analysis failed: {e}", exc_info=True)
            return {
                "high_value_segments": [],
                "product_categories": [],
                "ai_error": f"AI analysis failed: {str(e)}",
                "ai_status": "failed_processing"
            }
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during AI analysis: {e}", exc_info=True)
            return {
                "high_value_segments": [],
                "product_categories": [],
                "ai_error": f"An unexpected error occurred: {str(e)}",
                "ai_status": "failed_unexpected"
            }


# Create singleton instance
ai_service = AIService()
