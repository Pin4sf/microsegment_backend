import requests
import json
import time
from typing import Dict, List
import os

# API Configuration
BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/api/ai"

# Test Data
TEST_PRODUCT = {
    "title": "Minimalist Test Tee",
    "body_html": "<p>A simple t-shirt for testing the API and processing pipeline.</p>",
    "handle": "minimalist-test-tee",
    "product_type": "Apparel",
    "tags": ["test", "api", "clothing"],
    "options": [
        {
            "name": "Color",
            "values": ["White", "Black"]
        },
        {
            "name": "Size",
            "values": ["M", "L"]
        }
    ],
    "images": [
        {
            "src": "https://cdn.pixabay.com/photo/2025/05/20/10/57/t-shirt-9611374_1280.jpg"
        }
    ]
}

TEST_ORDER_HISTORY = {
    "customer_history": {
        "total_orders": 5,
        "average_order_value": 75.50,
        "preferred_categories": ["Apparel", "Accessories"]
    },
    "order_history": {
        "orders": [
            {
                "id": "123",
                "items": [
                    {
                        "name": "Product 1",
                        "quantity": 2,
                        "price": "19.99"
                    }
                ],
                "total_price": "39.98"
            }
        ]
    }
}

TEST_BATCH_PRODUCTS = [
    {
        "title": "Premium Denim Jeans",
        "body_html": "<p>High-quality denim jeans with perfect fit.</p>",
        "handle": "premium-denim-jeans",
        "product_type": "Apparel",
        "tags": ["denim", "jeans", "premium"],
        "options": [
            {
                "name": "Color",
                "values": ["Blue", "Black"]
            },
            {
                "name": "Size",
                "values": ["30", "32", "34"]
            }
        ],
        "images": [
            {
                "src": "https://cdn.pixabay.com/photo/2024/03/15/10/04/jeans-8634501_1280.jpg"
            }
        ]
    },
    {
        "title": "Casual Summer Hat",
        "body_html": "<p>Lightweight and stylish summer hat for beach days.</p>",
        "handle": "casual-summer-hat",
        "product_type": "Accessories",
        "tags": ["hat", "summer", "beach"],
        "options": [
            {
                "name": "Color",
                "values": ["Beige", "White"]
            },
            {
                "name": "Size",
                "values": ["One Size"]
            }
        ],
        "images": [
            {
                "src": "https://cdn.pixabay.com/photo/2024/04/17/18/40/ai-generated-8702726_1280.jpg"
            }
        ]
    }
]


def load_products_from_json(file_path: str) -> List[Dict]:
    """Load products from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('products', [])
    except Exception as e:
        print(f"Error loading products from {file_path}: {e}")
        return []


def wait_for_task_completion(task_id: str, max_attempts: int = 40, poll_interval: int = 5) -> Dict:
    """Poll task status until completion or timeout."""
    consecutive_errors = 0
    max_consecutive_errors = 3

    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}{API_PREFIX}/tasks/{task_id}")
            response.raise_for_status()
            status_data = response.json()

            print(
                f"Attempt {attempt + 1}/{max_attempts}: Status - {status_data['status']}")

            if status_data['status'] == 'SUCCESS':
                # Handle both list and dictionary responses
                if isinstance(status_data.get('result'), list):
                    return {
                        'status': 'SUCCESS',
                        'result': {'products': status_data['result']}
                    }
                return status_data
            elif status_data['status'] == 'FAILURE':
                print(
                    f"Task failed: {status_data.get('error', 'Unknown error')}")
                return status_data
            elif status_data['status'] == 'STARTED':
                print(
                    f"Task is still processing... ({attempt + 1}/{max_attempts})")
                consecutive_errors = 0  # Reset error counter on successful response
            else:
                print(f"Unexpected status: {status_data['status']}")

            time.sleep(poll_interval)
        except requests.exceptions.RequestException as e:
            consecutive_errors += 1
            print(f"Error checking task status: {e}")

            if consecutive_errors >= max_consecutive_errors:
                print(
                    f"Too many consecutive errors ({consecutive_errors}). Task may have failed.")
                return {
                    'status': 'FAILURE',
                    'error': f'Task failed after {consecutive_errors} consecutive errors'
                }

            if attempt < max_attempts - 1:  # Don't sleep on the last attempt
                time.sleep(poll_interval)
        except Exception as e:
            print(f"Unexpected error checking task status: {e}")
            if attempt < max_attempts - 1:  # Don't sleep on the last attempt
                time.sleep(poll_interval)

    print("Task did not complete within the time limit")
    return {"status": "TIMEOUT", "error": "Task processing took too long"}


def test_single_product():
    """Test single product processing endpoint."""
    print("\n=== Testing Single Product Processing ===")
    try:
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/products/process",
            json=TEST_PRODUCT
        )
        response.raise_for_status()
        task_data = response.json()
        print(f"Task submitted successfully. Task ID: {task_data['task_id']}")

        result = wait_for_task_completion(task_data['task_id'])
        if result.get('result'):
            print("\nProcessing Result:")
            print(json.dumps(result['result'], indent=2))
    except Exception as e:
        print(f"Error in single product test: {e}")


def test_order_history():
    """Test order history processing endpoint."""
    print("\n=== Testing Order History Processing ===")
    try:
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/orders/process",
            json=TEST_ORDER_HISTORY
        )
        response.raise_for_status()
        task_data = response.json()
        print(f"Task submitted successfully. Task ID: {task_data['task_id']}")

        result = wait_for_task_completion(task_data['task_id'])
        if result.get('result'):
            print("\nProcessing Result:")
            print(json.dumps(result['result'], indent=2))
    except Exception as e:
        print(f"Error in order history test: {e}")


def test_batch_processing():
    """Test batch product processing endpoint."""
    print("\n=== Testing Batch Product Processing ===")
    try:
        batch_request = {
            "products": TEST_BATCH_PRODUCTS,
            "output_dir": "test_outputs"
        }

        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/products/batch",
            json=batch_request
        )
        response.raise_for_status()
        task_data = response.json()
        print(f"Task submitted successfully. Task ID: {task_data['task_id']}")

        result = wait_for_task_completion(task_data['task_id'])
        if result.get('result'):
            print("\nBatch Processing Results:")
            print(json.dumps(result['result'], indent=2))
    except Exception as e:
        print(f"Error in batch processing test: {e}")


def test_products_json_batch():
    """Test batch processing with products from products.json file."""
    print("\n=== Testing Batch Processing with products.json ===")

    # Load products from JSON file
    products = load_products_from_json('tests/data/products.json')
    if not products:
        print("No products loaded from file")
        return

    print(f"Loaded {len(products)} products from file")

    # Process products in smaller batches to avoid overwhelming the system
    batch_size = 2  # Further reduced batch size for better reliability
    total_batches = (len(products) + batch_size - 1) // batch_size

    all_results = []
    failed_batches = []

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(products))
        current_batch = products[start_idx:end_idx]

        print(
            f"\nProcessing batch {batch_num + 1}/{total_batches} ({len(current_batch)} products)")

        try:
            batch_request = {
                "products": current_batch,
                "output_dir": f"test_outputs/batch_{batch_num + 1}"
            }

            response = requests.post(
                f"{BASE_URL}{API_PREFIX}/products/batch",
                json=batch_request
            )
            response.raise_for_status()
            task_data = response.json()
            print(
                f"Batch {batch_num + 1} submitted successfully. Task ID: {task_data['task_id']}")

            result = wait_for_task_completion(task_data['task_id'])

            if result.get('status') == 'SUCCESS':
                if isinstance(result.get('result'), dict) and 'products' in result['result']:
                    batch_results = result['result']['products']
                    all_results.extend(batch_results)
                    print(f"\nBatch {batch_num + 1} Processing Results:")
                    for idx, product_result in enumerate(batch_results):
                        print(f"\nProduct {idx + 1}:")
                        print(json.dumps(product_result, indent=2))
                else:
                    print(
                        f"\nUnexpected result format for batch {batch_num + 1}:")
                    print(json.dumps(result, indent=2))
                    failed_batches.append(batch_num + 1)
            elif result.get('status') == 'FAILURE':
                print(f"\nBatch {batch_num + 1} failed:")
                print(json.dumps(result.get('error', 'Unknown error'), indent=2))
                failed_batches.append(batch_num + 1)

            # Add a longer delay between batches
            if batch_num < total_batches - 1:
                print("Waiting 15 seconds before next batch...")
                time.sleep(15)

        except Exception as e:
            print(f"Error processing batch {batch_num + 1}: {e}")
            print("Continuing with next batch...")
            failed_batches.append(batch_num + 1)

    # Save all results to a single file
    if all_results:
        output_dir = "test_outputs"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "all_results.json")

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({"results": all_results}, f, indent=2)
            print(f"\nAll results saved to {output_file}")
        except Exception as e:
            print(f"Error saving results to file: {e}")

    print(f"\nProcessed {len(all_results)} products in total")
    if failed_batches:
        print(f"Failed batches: {failed_batches}")


def run_all_tests():
    """Run all test cases."""
    print("Starting AI Backend Tests...")
    print("Make sure your FastAPI server is running!")

    # Uncomment the tests you want to run
    # test_single_product()
    # test_order_history()
    # test_batch_processing()
    test_products_json_batch()

    print("\nAll tests completed!")


if __name__ == "__main__":
    run_all_tests()
