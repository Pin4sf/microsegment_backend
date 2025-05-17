from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Any, Dict

# --- Common Schemas ---


class PageInfo(BaseModel):
    hasNextPage: bool
    endCursor: Optional[str] = None


class ShopifyDataRequest(BaseModel):
    shop: str = Field(...,
                      description="The Shopify store domain (e.g., your-store.myshopify.com)")
    access_token: str = Field(...,
                              description="The Shopify access token for the store.")
    custom_query: Optional[str] = Field(
        None, description="Custom query string for filtering results (e.g., 'title:MyProduct')")
    cursor: Optional[str] = Field(
        None, description="Cursor for pagination to fetch the next set of results.")
    first: int = Field(
        10, ge=1, le=250, description="Number of items to fetch per page.")


class ShopifyTransactionRequest(ShopifyDataRequest):
    order_id: str = Field(...,
                          description="The GraphQL ID of the order to fetch transactions for.")

# --- Product Schemas (Simplified based on JS example) ---


class ProductVariantNode(BaseModel):
    id: str
    title: str
    price: str
    inventoryQuantity: Optional[int] = None
    # selectedOptions: Optional[List[Dict[str, str]]] = None # Can be complex


class ProductVariantEdge(BaseModel):
    node: ProductVariantNode


class ProductVariantConnection(BaseModel):
    edges: List[ProductVariantEdge]


class ProductPriceRange(BaseModel):
    amount: str


class ProductPriceRangeV2(BaseModel):
    maxVariantPrice: ProductPriceRange
    minVariantPrice: ProductPriceRange


class ProductNode(BaseModel):
    id: str
    title: str
    handle: Optional[str] = None
    description: Optional[str] = None
    descriptionHtml: Optional[str] = None
    productType: Optional[str] = None
    vendor: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    createdAt: Optional[str] = None  # Consider datetime type with validator
    priceRangeV2: Optional[ProductPriceRangeV2] = None
    variants: Optional[ProductVariantConnection] = None


class ProductEdge(BaseModel):
    node: ProductNode
    cursor: str


class ProductsConnection(BaseModel):
    edges: List[ProductEdge]
    pageInfo: PageInfo


class ShopifyProductResponse(BaseModel):
    products: Optional[ProductsConnection] = None
    # Can also include a general success/error message structure
    success: bool = True
    message: Optional[str] = None
    # For flexibility if direct data pass-through is needed
    data: Optional[Dict[str, Any]] = None

# --- Order Schemas (Simplified) ---


class MoneySet(BaseModel):
    amount: str
    currencyCode: str


class ShopMoney(BaseModel):
    shopMoney: MoneySet


class OrderLineItemNode(BaseModel):
    title: str
    quantity: int
    discountedTotalSet: Optional[ShopMoney] = None
    originalTotalSet: Optional[ShopMoney] = None


class OrderLineItemEdge(BaseModel):
    node: OrderLineItemNode


class OrderLineItemConnection(BaseModel):
    edges: List[OrderLineItemEdge]


class OrderCustomer(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None


class OrderNode(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    createdAt: str  # Consider datetime
    displayFinancialStatus: Optional[str] = None
    totalDiscountsSet: Optional[ShopMoney] = None
    totalPriceSet: Optional[ShopMoney] = None
    lineItems: Optional[OrderLineItemConnection] = None
    customer: Optional[OrderCustomer] = None


class OrderEdge(BaseModel):
    node: OrderNode
    cursor: str


class OrdersConnection(BaseModel):
    edges: List[OrderEdge]
    pageInfo: PageInfo


class ShopifyOrderResponse(BaseModel):
    orders: Optional[OrdersConnection] = None
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# --- Transaction Schemas (Simplified - assuming part of Order or fetched separately) ---
# The JS example doesn't show a separate transaction fetcher, but implies it.
# If transactions are fetched via Order, they might be part of OrderNode.
# If fetched separately, a structure similar to Products/Orders would be needed.
# For now, let's assume a generic response for transactions if fetched via a dedicated endpoint.


# Example structure, needs to be defined based on actual API response
class TransactionNode(BaseModel):
    id: str
    kind: str
    status: str
    amountSet: ShopMoney
    createdAt: str
    # ... other relevant transaction fields, e.g., test, gateway, fees, paymentDetails, etc.


class ShopifyTransactionResponse(BaseModel):
    # Transactions are fetched for an order and returned as a list under node.transactions
    transactions: Optional[List[TransactionNode]] = None
    success: bool = True
    message: Optional[str] = None
    # For flexibility if direct data pass-through is needed for errors
    data: Optional[Dict[str, Any]] = None

# --- Customer Schemas ---


class CustomerAmountSpent(BaseModel):
    amount: str
    currencyCode: str


class CustomerNode(BaseModel):
    id: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    createdAt: Optional[str] = None  # Consider datetime
    tags: Optional[List[str]] = None
    note: Optional[str] = None
    # e.g., "ENABLED", "DISABLED", "DECLINED", "INVITED"
    state: Optional[str] = None
    amountSpent: Optional[CustomerAmountSpent] = None


class CustomerEdge(BaseModel):
    node: CustomerNode
    cursor: str


class CustomersConnection(BaseModel):
    edges: List[CustomerEdge]
    pageInfo: PageInfo


class ShopifyCustomerResponse(BaseModel):
    customers: Optional[CustomersConnection] = None
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None  # For flexibility

# Generic response for API calls


class GenericResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Any] = None
