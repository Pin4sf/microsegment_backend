# MicroSegment Class

A centralized Python class for handling product and order history processing operations using AI models and background task queues.

## Features

- **AI-Powered Processing**: Integrates with OpenAI/OpenRouter models for product and order analysis
- **Background Tasks**: Uses Huey for asynchronous processing
- **Flexible Product Processing**: Supports both standard and Neat Feat specific product analysis
- **Task Management**: Complete task submission, status tracking, and result retrieval
- **Batch Processing**: Handle multiple products efficiently
- **File Operations**: Automatic output saving and organization

## Installation

```bash
pip install -r requirements.txt
```

Ensure you have a `.env` file with:
```
OPENROUTER_API_KEY=your_api_key_here
```

## Quick Start

```python
from microsegment import MicroSegment

# Initialize
ms = MicroSegment()

# Process a single product
product_data = {
    "title": "Blue Cotton T-Shirt",
    "description": "Comfortable cotton t-shirt in blue",
    "handle": "blue-cotton-tshirt",
    "product_type": "Apparel",
    "tags": "cotton,casual,blue",
    "options": [{"name": "Size", "values": ["S", "M", "L"]}],
    "images": [{"src": "https://example.com/image.jpg"}]
}

result = ms.process_product(product_data)
print(result)
```

## Class Methods

### Core Processing
- `process_product(product_data)` - Process standard products
- `process_product_neat_feat(product_data, model)` - Process Neat Feat products
- `process_order_history(order_history)` - Analyze order histories
- `call_model(messages, model, temperature)` - Direct AI model communication

### Task Management
- `submit_product_for_processing(product_dict)` - Queue product for background processing
- `submit_order_history_for_processing(order_history_dict)` - Queue order history processing
- `get_task_status(task_id)` - Check product task status
- `get_order_history_task_status(task_id)` - Check order history task status

### Utilities
- `save_product_output(handle, data, output_dir)` - Save results to file
- `batch_process_products(products, output_dir, model)` - Process multiple products

## Usage Examples

### Background Task Processing
```python
ms = MicroSegment()

# Submit for background processing
task_response = ms.submit_product_for_processing(product_data)
task_id = task_response["task_id"]

# Check status later
status = ms.get_task_status(task_id)
print(f"Status: {status['status']}")
if status['status'] == 'COMPLETE':
    print(f"Result: {status['result']}")
```

### Batch Processing
```python
products = [product1, product2, product3]
results = ms.batch_process_products(
    products, 
    output_dir="outputs_batch",
    model="openai/gpt-4o-mini"
)
```

### Order History Analysis
```python
order_data = {
    "customer_history": {...},
    "order_history": {...}
}

task_response = ms.submit_order_history_for_processing(order_data)
```

## Configuration

The class automatically loads configuration from:
- Environment variables (`.env` file)
- Huey configuration (`huey_config.py`)
- AI prompts (`PROMPTS.py`)

## Error Handling

All methods include comprehensive error handling:
- Model communication errors
- JSON parsing errors
- Task submission failures
- File I/O errors

## Integration with FastAPI

The MicroSegment class is designed to work seamlessly with your existing FastAPI endpoints. Simply replace direct function calls with MicroSegment method calls.

## Output Structure

Processed results are saved as JSON files with the product handle as filename:
```
outputs/
├── product-handle-1.json
├── product-handle-2.json
└── ...
```

## Dependencies

- `openai` - AI model communication
- `huey` - Background task processing
- `fastapi` - API framework
- `pydantic` - Data validation
- `python-dotenv` - Environment management