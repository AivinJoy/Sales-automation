# backend\main.py

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pandas as pd
import calendar
import random

# Import our modules
import config
import storage
import logic
import reports
from config import SETTINGS
from models import (
    SimulationRequest, DailyAction, ReportRequest, StockEntry,
    ProductInflow, ProductOpeningStock, ProductCreate, ProductRateUpdate
)
app = FastAPI()

# --- CORS MIDDLEWARE ---
# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False, # MUST BE FALSE WHEN ORIGINS IS "*"
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.post("/simulate_month")
def simulate_month(req: SimulationRequest):
    customers = storage.get_customers()
    if not customers:
        raise HTTPException(status_code=400, detail="No customers found")
    
    all_products = {p["id"]: p for p in storage.get_products()}
    if not all_products:
        raise HTTPException(status_code=400, detail="No products configured. Add a product first.")

    start_date = datetime(req.year, req.month, 1)
    next_month = start_date.replace(day=28) + timedelta(days=4)
    end_date = next_month - timedelta(days=next_month.day)
    
     # --- DYNAMIC INVENTORY SETUP (keyed by product_id) ---
    current_stock = {po.product_id: po.opening_stock for po in req.opening_stocks}
    for pid in all_products:
        current_stock.setdefault(pid, 0)  # any product missing from the request starts at 0
    
    current_inv = req.starting_invoice - 1 
    all_sales = []
    audit_log = [] 
    
    # 1. Prepare Inflows Map & Purchase Log (accumulate per date, since multiple
    #    rows can now share the same date — one row per product)
    inflows_map = {}
    purchase_log_data = [] 
    
    total_bought = {pid: 0 for pid in all_products}

    for entry in req.stock_inflows:
        if entry.date not in inflows_map:
            inflows_map[entry.date] = []
        inflows_map[entry.date].append(entry)

        for inflow in entry.inflows:
            if inflow.qty > 0 and inflow.product_id in all_products:
                total_bought[inflow.product_id] += inflow.qty
                purchase_log_data.append({
                    "Date": entry.date,
                    "Item": all_products[inflow.product_id]["name"],
                    "Purchase Invoice No": entry.invoice_no,
                    "Quantity Received": inflow.qty
                })
  
    # Prepare Look-Ahead Lists (one list of purchase dates per product)
    inflow_dates_by_product = {pid: [] for pid in all_products}
    for date_str, entries in inflows_map.items():
        for entry in entries:
            for inflow in entry.inflows:
                if inflow.qty > 0 and inflow.product_id in inflow_dates_by_product:
                    inflow_dates_by_product[inflow.product_id].append(datetime.strptime(date_str, "%d/%m/%Y"))
    for pid in inflow_dates_by_product:
        inflow_dates_by_product[pid].sort()
    
    # Trackers
    sales_delay_counter = 0 
    force_low_sales = False 

    # --- Day Loop ---
    curr = start_date
    while curr <= end_date:
        date_str = curr.strftime("%d/%m/%Y")
        
        # --- A. HANDLE STOCK INFLOW ---
        if date_str in inflows_map:
            bal_str = ", ".join(f"{all_products[pid]['name'][:3]}={current_stock[pid]}" for pid in all_products)
            audit_log.append({
                "Date": date_str, "Type": "Cycle Summary",
                "Info": f"Clos Bal: {bal_str}",
                "Customer": "-", "Quantity": "-", "Amount": "-",
                "INVOICE": "-", "GSTIN": "-", "TAXABLE": "-", "CGST": "-", "SGST": "-"
            })

            for entry in inflows_map[date_str]:
                for inflow in entry.inflows:
                    if inflow.qty > 0 and inflow.product_id in all_products:
                        current_stock[inflow.product_id] += inflow.qty
                        prod_name = all_products[inflow.product_id]["name"]
                        audit_log.append({
                            "Date": date_str, "Type": f"Stock Added ({prod_name})", "Info": "Purchase received",
                            "Customer": "-", "Quantity": f"+{inflow.qty}", "Amount": "-"
                        })
            
            start_delay = random.choice([0, 1, 2])
            if start_delay == 0:
                sales_delay_counter = 0
                force_low_sales = True
            else:
                sales_delay_counter = start_delay
                force_low_sales = False

        # --- B. HANDLE DELAY ---
        if sales_delay_counter > 0:
            sales_delay_counter -= 1
            audit_log.append({
                "Date": date_str, "Type": "Restocking Delay", "Info": "Processing Stock...", 
                "Customer": "-", "Quantity": "-", "Amount": "-"
            })
            curr += timedelta(days=1)
            continue

                # --- C & D. PACING + SALES, LOOPED OVER EVERY PRODUCT ---
        daily_sales = []
        statuses = {}

        for pid, prod in all_products.items():
            next_refill = end_date
            for d_obj in inflow_dates_by_product.get(pid, []):
                if d_obj > curr:
                    next_refill = d_obj
                    break
            days_until = (next_refill - curr).days
            if days_until < 1: days_until = 1

            new_stock, sales, current_inv, status = logic.decide_sales_for_day(
                curr, current_stock[pid], customers, current_inv,
                days_until_next_refill=days_until,
                rate_override=prod["rate"],   # <--- LIVE RATE FROM PRODUCTS TABLE
                force_low_mode=force_low_sales,
                product_name=prod["name"]
            )
            current_stock[pid] = new_stock
            statuses[pid] = status

            for s in sales:
                s["Item Name"] = prod["name"]
            daily_sales.extend(sales)

        if force_low_sales: force_low_sales = False

       # --- E. LOGGING ---
        if not daily_sales:
            info_msg = next((s for s in statuses.values() if s != "Active"), "-")
            audit_log.append({
                "Date": date_str, "Type": "No Sales", "Info": info_msg,
                "Customer": "-", "Quantity": "-", "Amount": "-"
            })
        else:
            daily_sales.sort(key=lambda x: x["INVOICE"])

            for s in daily_sales:
                audit_log.append({
                    "Date": date_str, "Type": "Sale", "Info": s["Item Name"],
                    "Customer": s.get("_customer_name", "Unknown"),
                    "Quantity": s["_qty"], "Amount": s["TAXABLE"],
                    "INVOICE": s["INVOICE"], "GSTIN": s["GSTIN"],
                    "TAXABLE": s["TAXABLE"], "CGST": s["CGST"], "SGST": s["SGST"]
                })

        all_sales.extend(daily_sales)
        curr += timedelta(days=1)

    # 4. Save Files to Cloud
    month_name = calendar.month_name[req.month]
    
    filename = reports.generate_excel_report(all_sales, req.month, req.year)
    reports.save_audit_log(audit_log, month_name, req.year)
    
    for pid, qty in total_bought.items():
        purchase_log_data.append({"Date": "TOTAL", "Item": all_products[pid]["name"], "Quantity Received": qty})

    reports.save_purchase_log(purchase_log_data, month_name, req.year)

    total_revenue = sum(s["TAXABLE"] for s in all_sales)

    # 5. Save Monthly Snapshot to Cloud (monthly_snapshots table)
    # NOTE: box_stock/liquid_stock columns are legacy — we still populate them
    # by name-matching so old dashboards/reports reading this table don't break,
    # but the authoritative per-product data now lives in product_stock.
    box_id = next((pid for pid, p in all_products.items() if p["name"] == "Soore Box"), None)
    liquid_id = next((pid for pid, p in all_products.items() if p["name"] == "Soore Liquid"), None)

    snapshot = {
        "month": req.month,
        "year": req.year,
        "box_stock": current_stock.get(box_id, 0),
        "liquid_stock": current_stock.get(liquid_id, 0),
        "custom_stock": 0,  # legacy field — kept for backward compatibility with old rows
        "stock_snapshot": {all_products[pid]["name"]: qty for pid, qty in current_stock.items()},
        "last_invoice": current_inv,
        "total_revenue": total_revenue,
        "snapshot_date": datetime.now().isoformat()
    }
    storage.save_snapshot(snapshot)

    # --- SYNC LIVE STATE (every product, generically) ---
    storage.save_state({
        "stock_map": {all_products[pid]["name"]: qty for pid, qty in current_stock.items()},
        "last_invoice": current_inv,
        "total_sales_val": total_revenue
    })

    final_stock_str = ", ".join(f"{all_products[pid]['name']}: {qty}" for pid, qty in current_stock.items())

    return {
        "message": "Simulation Complete",
        "file": filename,
        "total_sales": total_revenue,
        "final_stock": final_stock_str
    }

    # NEW Output String formatting

@app.get("/state")
def get_state(): return storage.load_state()

@app.post("/everyday/action")
def daily_action(act: DailyAction):
    # This endpoint is for single-day actions. 
    state = storage.load_state()
    customers = storage.get_customers()
    today = datetime.now()
    
    if "stock_map" not in state: state["stock_map"] = {}
    
    prod_name = act.product_name if act.product_name else "Soore Box"
    current_prod_stock = state["stock_map"].get(prod_name, 0)
    
    # Rate now comes from the products table (respects any rate edits),
    # instead of a hardcoded "Box vs Liquid" name check.
    all_products = storage.get_products()
    matching_product = next((p for p in all_products if p["name"] == prod_name), None)
    rate = matching_product["rate"] if matching_product else SETTINGS.get("rate_box", 350)


    if act.action == "add_stock":
        current_prod_stock += act.qty
        state["stock_map"][prod_name] = current_prod_stock
        storage.save_state(state)
        return {"message": f"Stock Added to {prod_name}. New Balance: {current_prod_stock}"}
    
    elif act.action == "simulate":
        new_stock, sales, new_inv, status = logic.decide_sales_for_day(
            today, current_prod_stock, customers, state["last_invoice"], 
            days_until_next_refill=3,
            rate_override=rate,
            product_name=prod_name
        )
        
        if not sales and new_stock == current_prod_stock: return {"message": f"No sales ({status})."}
        
        for s in sales: s["Item Name"] = prod_name

        state["stock_map"][prod_name] = new_stock
        state["last_invoice"] = new_inv
        for s in sales: 
            state["total_sales_val"] += s["TAXABLE"]
            state["sales_log"].append(s)
            
        storage.save_state(state)
        reports.update_daily_log_excel(state["sales_log"])
        return {"message": f"Simulated {len(sales)} sales for {prod_name}.", "new_stock": new_stock}

@app.post("/generate_summary")
def generate_summary(req: ReportRequest):
    filename, msg = reports.generate_summary_report(req.year, req.period)
    if not filename: return {"success": False, "message": msg}
    return {"success": True, "message": msg, "file": filename}

# --- REPORT RETRIEVAL (CLOUD) ---

@app.get("/reports/list")
def list_reports():
    """Lists available reports directly from Supabase Cloud."""
    files = reports.list_cloud_reports()
    return {"files": files} 

@app.get("/purchases/list")
def list_purchases():
    """Lists purchase logs directly from Supabase Cloud."""
    files = reports.list_cloud_purchases()
    return {"files": files} 

@app.get("/reports/view/{filename}")
def view_report(filename: str):
    """Downloads a report from cloud to memory and returns JSON for UI preview."""
    base_name = filename.replace(".xlsx", "")
    audit_name = f"{base_name}_Audit.json"
    
    # Try fetching audit log first (lighter)
    audit_data = reports.read_cloud_json(audit_name)
    if audit_data:
        return {"data": audit_data, "type": "audit"}
    
    # Fallback to Excel
    df = reports.read_cloud_excel(filename)
    if df is not None:
         return {"data": df.to_dict(orient="records"), "type": "excel"}
    
    raise HTTPException(status_code=404, detail="File not found in Cloud Storage")

@app.get("/purchases/view/{filename}")
def view_purchase_log(filename: str):
    """Downloads purchase log from cloud."""
    data = reports.read_cloud_json(filename)
    if data:
        return {"data": data, "type": "purchase"}
    raise HTTPException(status_code=404, detail="File not found in Cloud Storage")

@app.get("/reports/download/{filename}")
def download_report(filename: str):
    """Redirects the user to a secure, temporary download URL from Supabase."""
    signed_url = reports.get_report_url(filename)
    if signed_url:
        return RedirectResponse(url=signed_url)
    raise HTTPException(status_code=404, detail="Could not generate download link")

@app.get("/products")
def get_products():
    """Returns all products with id, name, rate."""
    return {"products": storage.get_products()}

@app.post("/products")
def create_product(req: ProductCreate):
    """Creates a new product (and its zero-stock row) permanently in the DB."""
    existing = [p for p in storage.get_products() if p["name"].strip().lower() == req.name.strip().lower()]
    if existing:
        raise HTTPException(status_code=400, detail=f"Product '{req.name}' already exists")

    new_product = storage.add_product(req.name, req.rate)
    if not new_product:
        raise HTTPException(status_code=500, detail="Failed to create product")
    return {"message": f"Product '{req.name}' created", "product": new_product}

@app.put("/products/{product_id}")
def update_product_rate(product_id: int, req: ProductRateUpdate):
    """Updates a product's rate going forward. Past reports keep their original rate."""
    storage.update_product_rate(product_id, req.rate)
    return {"message": "Rate updated"}