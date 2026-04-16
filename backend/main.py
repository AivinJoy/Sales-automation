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
from models import SimulationRequest, DailyAction, ReportRequest, StockEntry

app = FastAPI()

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sales-automation-beige.vercel.app", # Your live Vercel frontend
        "http://localhost:5173"                      # Keep this so it still works when testing locally
    ], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.post("/simulate_month")
def simulate_month(req: SimulationRequest):
    customers = storage.get_customers()
    if not customers:
        raise HTTPException(status_code=400, detail="No customers found")

    start_date = datetime(req.year, req.month, 1)
    next_month = start_date.replace(day=28) + timedelta(days=4)
    end_date = next_month - timedelta(days=next_month.day)
    
    # --- DUAL INVENTORY SETUP ---
    current_stock_box = req.opening_stock_box
    current_stock_liquid = req.opening_stock_liquid
    
    current_inv = req.starting_invoice - 1 
    all_sales = []
    audit_log = [] 
    
    # 1. Prepare Inflows Map & Purchase Log
    inflows_map = {}
    purchase_log_data = [] 
    
    total_bought_box = 0
    total_bought_liquid = 0

    for entry in req.stock_inflows:
        if entry.date not in inflows_map:
            inflows_map[entry.date] = []
        inflows_map[entry.date].append(entry)
        
        # Track totals
        total_bought_box += entry.qty_box
        total_bought_liquid += entry.qty_liquid
        
        # Log Box Purchase
        if entry.qty_box > 0:
            purchase_log_data.append({
                "Date": entry.date,
                "Item": "Soore Box",
                "Purchase Invoice No": entry.invoice_no,
                "Quantity Received": entry.qty_box
            })
            
        # Log Liquid Purchase
        if entry.qty_liquid > 0:
            purchase_log_data.append({
                "Date": entry.date,
                "Item": "Soore Liquid",
                "Purchase Invoice No": entry.invoice_no,
                "Quantity Received": entry.qty_liquid
            })

    # Prepare Look-Ahead Lists
    inflow_dates_box = sorted([
        datetime.strptime(d, "%d/%m/%Y") 
        for d, entries in inflows_map.items() 
        if any(e.qty_box > 0 for e in entries)
    ])
    
    inflow_dates_liquid = sorted([
        datetime.strptime(d, "%d/%m/%Y") 
        for d, entries in inflows_map.items() 
        if any(e.qty_liquid > 0 for e in entries)
    ])
    
    # Trackers
    sales_delay_counter = 0 
    force_low_sales = False 

    # --- Day Loop ---
    curr = start_date
    while curr <= end_date:
        date_str = curr.strftime("%d/%m/%Y")
        
        # --- A. HANDLE STOCK INFLOW ---
        if date_str in inflows_map:
            audit_log.append({
                "Date": date_str, "Type": "Cycle Summary", 
                "Info": f"Clos Bal: Box={current_stock_box}, Liq={current_stock_liquid}",
                "Customer": "-", "Quantity": "-", "Amount": "-", 
                "INVOICE": "-", "GSTIN": "-", "TAXABLE": "-", "CGST": "-", "SGST": "-"
            })

            for inflow in inflows_map[date_str]:
                if inflow.qty_box > 0:
                    current_stock_box += inflow.qty_box
                    audit_log.append({
                        "Date": date_str, "Type": "Stock Added (Box)", "Info": f"Inv: {inflow.invoice_no}", 
                        "Customer": "-", "Quantity": f"+{inflow.qty_box}", "Amount": "-"
                    })
                if inflow.qty_liquid > 0:
                    current_stock_liquid += inflow.qty_liquid
                    audit_log.append({
                        "Date": date_str, "Type": "Stock Added (Liq)", "Info": f"Inv: {inflow.invoice_no}", 
                        "Customer": "-", "Quantity": f"+{inflow.qty_liquid}", "Amount": "-"
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

        # --- C. CALCULATE PACING ---
        next_box_refill = end_date
        for d_obj in inflow_dates_box:
            if d_obj > curr:
                next_box_refill = d_obj
                break
        days_until_box = (next_box_refill - curr).days
        if days_until_box < 1: days_until_box = 1
        
        next_liq_refill = end_date
        for d_obj in inflow_dates_liquid:
            if d_obj > curr:
                next_liq_refill = d_obj
                break
        days_until_liq = (next_liq_refill - curr).days
        if days_until_liq < 1: days_until_liq = 1

        # --- D. RUN SALES LOGIC (DUAL PASS WITH USER RATES) ---
        
        # PASS 1: SOORE BOX
        current_stock_box, sales_box, current_inv, status_box = logic.decide_sales_for_day(
            curr, current_stock_box, customers, current_inv, 
            days_until_next_refill=days_until_box, 
            rate_override=req.rate_box,  # <--- USES USER EDITED RATE
            force_low_mode=force_low_sales
        )
        
        # Inject Product Name
        for s in sales_box: s["Item Name"] = "Soore Box"

        # PASS 2: SOORE LIQUID
        current_stock_liquid, sales_liquid, current_inv, status_liq = logic.decide_sales_for_day(
            curr, current_stock_liquid, customers, current_inv, 
            days_until_next_refill=days_until_liq, 
            rate_override=req.rate_liquid, # <--- USES USER EDITED RATE
            force_low_mode=force_low_sales
        )

        # Inject Product Name
        for s in sales_liquid: s["Item Name"] = "Soore Liquid"
        
        if force_low_sales: force_low_sales = False

        # --- E. LOGGING ---
        daily_sales = sales_box + sales_liquid
        
        if not daily_sales:
            info_msg = "-"
            if status_box != "Active": info_msg = status_box
            elif status_liq != "Active": info_msg = status_liq
            
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
    
    # Save Purchase Log Summary
    purchase_log_data.append({"Date": "TOTAL", "Item": "Soore Box", "Quantity Received": total_bought_box})
    purchase_log_data.append({"Date": "TOTAL", "Item": "Soore Liquid", "Quantity Received": total_bought_liquid})
    
    reports.save_purchase_log(purchase_log_data, month_name, req.year)

    total_revenue = sum(s["TAXABLE"] for s in all_sales)

    # 5. Update Live State in Cloud
    new_state = storage.load_state()
    if "stock_map" not in new_state: new_state["stock_map"] = {}
    
    new_state["stock_map"]["Soore Box"] = current_stock_box
    new_state["stock_map"]["Soore Liquid"] = current_stock_liquid
    
    new_state["last_invoice"] = current_inv
    new_state["total_sales_val"] = total_revenue 
    
    storage.save_state(new_state)
    
    return {
        "message": "Simulation Complete", 
        "file": filename, 
        "total_sales": total_revenue,
        "final_stock": f"Box: {current_stock_box}, Liq: {current_stock_liquid}"
    }

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
    
    # Rate logic for Everyday Mode
    rate = SETTINGS["rate_liquid"] if "Liquid" in prod_name else SETTINGS["rate_box"]

    if act.action == "add_stock":
        current_prod_stock += act.qty
        state["stock_map"][prod_name] = current_prod_stock
        storage.save_state(state)
        return {"message": f"Stock Added to {prod_name}. New Balance: {current_prod_stock}"}
    
    elif act.action == "simulate":
        new_stock, sales, new_inv, status = logic.decide_sales_for_day(
            today, current_prod_stock, customers, state["last_invoice"], 
            days_until_next_refill=3,
            rate_override=rate
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