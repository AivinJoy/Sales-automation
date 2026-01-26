from pydantic import BaseModel
from typing import List

class StockEntry(BaseModel):
    date: str
    invoice_no: str
    qty_box: int       # <--- Quantity for Soore Box
    qty_liquid: int    # <--- Quantity for Soore Liquid

class SimulationRequest(BaseModel):
    month: int
    year: int
    
    # Opening Stocks for both products
    opening_stock_box: int
    opening_stock_liquid: int
    # NEW: Editable Rates
    rate_box: float
    rate_liquid: float

    starting_invoice: int
    
    # List of purchases (each entry has both Box and Liquid qtys)
    stock_inflows: List[StockEntry]

class DailyAction(BaseModel):
    action: str
    qty: int = 0
    product_name: str = "Soore Box" # Default product name

class ReportRequest(BaseModel):
    year: int
    period: str  # values will be "annual", "h1", "h2"