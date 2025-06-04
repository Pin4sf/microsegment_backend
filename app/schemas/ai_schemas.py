from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union


class Image(BaseModel):
    src: str


class Option(BaseModel):
    name: str
    values: List[str]


class ProductAIRequest(BaseModel):
    title: str
    description: str = Field(alias='body_html')
    handle: str
    product_type: str
    tags: str | List[str]
    options: List[Option]
    images: List[Image]

    class Config:
        allow_population_by_field_name = True


class OrderHistoryAIRequest(BaseModel):
    customer_history: Dict[str, Any]
    order_history: Dict[str, Any]


class AIProcessingResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    error: Optional[str] = None


class BatchProcessingRequest(BaseModel):
    products: List[ProductAIRequest]
    output_dir: Optional[str] = "outputs"
