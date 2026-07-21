# backend\models.py

from pydantic import BaseModel
from typing import List

class ProductInflow(BaseModel):
    product_id: int
    qty: int

class StockEntry(BaseModel):
    date: str
    invoice_no: str
    inflows: List[ProductInflow]

class ProductOpeningStock(BaseModel):
    product_id: int
    opening_stock: int    
class SimulationRequest(BaseModel):
    month: int
    year: int

    # Dynamic opening stock — one entry per product, no more hardcoded fields
    opening_stocks: List[ProductOpeningStock]

    starting_invoice: int

    # List of purchases (each entry can carry any number of products)
    stock_inflows: List[StockEntry]
    # NOTE: rates are no longer sent by the frontend. main.py reads each
    # product's current rate from the products table at simulation time,
    # so rate edits apply automatically without changing this request shape.

class DailyAction(BaseModel):
    action: str
    qty: int = 0
    product_name: str = "Soore Box" # Default product name

class ReportRequest(BaseModel):
    year: int
    period: str  # values will be "annual", "h1", "h2"

class ProductCreate(BaseModel):
    name: str
    rate: float

class ProductRateUpdate(BaseModel):
    rate: float