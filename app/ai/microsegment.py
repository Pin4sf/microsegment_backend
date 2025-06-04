import os
import json
import re
from typing import Any, Dict, List, Optional, Union
from openai import OpenAI
from dotenv import load_dotenv

from app.core.celery_app import celery_app
from app.ai.PROMPTS import (
    SYSTEM_PROMPT,
    USER_PROMPT,
    SYSTEM_PROMPT_NEAT_FEAT,
    USER_PROMPT_NEAT_FEAT,
    ORDER_HISTORY_SYSTEM_PROMPT_FOOD,
    ORDER_HISTORY_USER_PROMPT_FOOD
)

load_dotenv()


class MicroSegment:
    """
    Centralized class for handling all product and order history processing operations.
    """

    def __init__(self):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def call_model(self, messages: List[Dict], model: str = "openai/gpt-4o-mini", temperature: float = 0.0, **kwargs) -> Any:
        """Calls the specified OpenAI model."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            return response.choices[0].message
        except Exception as e:
            print(f"Error calling model: {e}")
            return None

    def process_product(self, product_data: Dict) -> Dict:
        """Prepares messages and calls the AI model for a given product."""
        product_json = {
            "title": product_data.get('title'),
            "description": product_data.get('description'),
            "handle": product_data.get('handle'),
            "product_type": product_data.get('product_type'),
            "tags": product_data.get('tags'),
            "options": product_data.get('options'),
        }

        user_message_content = [
            {
                "type": "text",
                "text": USER_PROMPT.format(product_details=json.dumps(product_json, indent=2))
            }
        ]

        # Only add images if they are valid URLs
        images = product_data.get('images', [])
        valid_images = []
        for img in images:
            if img.get('src') and img['src'].startswith(('http://', 'https://')):
                valid_images.append(img)

        # Add up to 2 valid images
        for img in valid_images[:2]:
            user_message_content.append({
                "type": "image_url",
                "image_url": {"url": img['src']}
            })

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message_content}
        ]

        try:
            response = self.call_model(messages, temperature=0.0)
            print(f"Model response: {response}")

            if response and response.content:
                try:
                    json_response = json.loads(response.content)
                    return json_response
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON response from model: {e}")
                    print(f"Raw response content: {response.content}")
                    return {"error": "Failed to parse model response", "raw_content": response.content}
                except Exception as e:
                    print(f"An unexpected error occurred: {e}")
                    return {"error": "An unexpected error occurred processing model response"}
            else:
                print("No valid response received from model.")
                return {"error": "No response from model"}
        except Exception as e:
            print(f"Error in process_product: {e}")
            return {"error": f"Error processing product: {str(e)}"}

    def process_product_neat_feat(self, product_data: Dict, model: str = "openai/gpt-4o-mini") -> Dict:
        """Process product specifically for Neat Feat products."""
        product_json = {
            "title": product_data.get('title'),
            "description": product_data.get('body_html'),
            "handle": product_data.get('handle'),
            "product_type": product_data.get('product_type'),
            "tags": product_data.get('tags'),
            "options": product_data.get('options'),
        }

        user_message_content = [
            {
                "type": "text",
                "text": USER_PROMPT_NEAT_FEAT.format(product_details=product_json)
            }
        ]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_NEAT_FEAT},
            {"role": "user", "content": user_message_content}
        ]

        response = self.call_model(messages, model, temperature=0.1)

        if response and response.content:
            try:
                json_match = re.search(
                    r'<JSON_OUTPUT>(.*?)</JSON_OUTPUT>', response.content, re.DOTALL)
                if json_match is None:
                    return {"error": "Missing JSON_OUTPUT section in response", "raw_content": response.content}
                json_content = json_match.group(1)
                json_response = json.loads(json_content)
                return json_response
            except Exception as e:
                print(f"Error processing Neat Feat product: {e}")
                return {"error": str(e), "raw_content": response.content}

        return {"error": "No response from model"}

    def save_order_output(self, order_id: str, result: Dict, output_dir: str) -> None:
        """Save order processing result to a JSON file."""
        try:
            print(f"Attempting to save order output for order {order_id}")
            print(f"Output directory: {output_dir}")

            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            print(f"Created/verified output directory: {output_dir}")

            # Create orders subdirectory
            orders_dir = os.path.join(output_dir, "orders")
            os.makedirs(orders_dir, exist_ok=True)
            print(f"Created/verified orders subdirectory: {orders_dir}")

            # Save the result to a JSON file
            output_file = os.path.join(orders_dir, f"{order_id}.json")
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)

            print(f"Successfully saved order output to {output_file}")
        except Exception as e:
            print(f"Error saving order output: {e}")
            print(f"Error details: {str(e)}")
            raise  # Re-raise the exception to ensure the error is logged in Celery

    def process_order_history(self, order_history: Dict, output_dir: Optional[str] = None) -> Dict:
        """Processes order history data using the AI model."""
        print(order_history)

        messages = [
            {"role": "system", "content": ORDER_HISTORY_SYSTEM_PROMPT_FOOD},
            {"role": "user", "content": ORDER_HISTORY_USER_PROMPT_FOOD.format(
                order_history=json.dumps(order_history, indent=2))}
        ]

        response = self.call_model(messages, temperature=0.0)

        if response and response.content:
            try:
                # Extract JSON output from the response
                json_match = re.search(
                    r'<JSON_OUTPUT>(.*?)</JSON_OUTPUT>', response.content, re.DOTALL)
                if json_match:
                    json_content = json_match.group(1)
                    json_response = json.loads(json_content)

                    # Save output if order_id is available and output_dir is provided
                    if 'id' in order_history and output_dir is not None:
                        self.save_order_output(
                            order_history['id'], json_response, output_dir)

                    return json_response
                else:
                    print("No JSON output found in response")
                    return {"error": "No JSON output found in model response", "raw_content": response.content}
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON response from model: {e}")
                print(f"Raw response content: {response.content}")
                return {"error": "Failed to parse model response", "raw_content": response.content}
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return {"error": "An unexpected error occurred processing model response"}
        else:
            print("No valid response received from model.")
            return {"error": "No response from model"}

    def batch_process_products(self, products: List[Dict], output_dir: Optional[str] = "outputs", model: str = "openai/gpt-4o-mini") -> List[Dict]:
        """Process multiple products in batch."""
        results = []
        for product in products:
            result = self.process_product(product)
            results.append(result)

            # Save output if handle is available and output_dir is provided
            if 'handle' in product and output_dir is not None:
                self.save_product_output(product['handle'], result, output_dir)

        return results

    def save_product_output(self, product_handle: str, output_data: Dict, output_dir: str = "outputs") -> str:
        """Save product processing output to a file."""
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{product_handle}.json")

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        return output_file
