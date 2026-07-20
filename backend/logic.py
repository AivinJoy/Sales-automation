#backend\logic.py

import random
from config import SETTINGS, HOLIDAYS

def is_holiday(date_str, date_obj):
    # Check if Sunday OR if date is in the specific Holiday List
    return date_obj.weekday() == 6 or date_str in HOLIDAYS

def decide_sales_for_day(date_obj, current_stock, customers, last_invoice, days_until_next_refill, rate_override=None, force_low_mode=False, product_name="Unknown Product"):
    """
    Decides sales based on PACING logic with a RANDOMIZED target buffer.
    """
    date_str = date_obj.strftime("%d/%m/%Y")

    # 1. Check Holiday (Sunday or Public Holiday)
    if is_holiday(date_str, date_obj):
        return current_stock, [], last_invoice, "Holiday"

    # 2. Check Random Quiet Day (Only if NOT in 'force low' mode)
    if not force_low_mode:
        if random.random() < SETTINGS["quiet_day_chance"]:
            return current_stock, [], last_invoice, "Quiet Day (Random)"

    # 3. PACING LOGIC
    
    # HARD STOP: If we are below the absolute minimum, stop selling immediately.
    if current_stock <= SETTINGS["min_stock_buffer"]:
        return current_stock, [], last_invoice, "Stock Low (Buffer Hit)"

    # RANDOM TARGET: Aim for a random safety net between Min and Max buffer.
    # This ensures the closing stock varies naturally (e.g. 22 one month, 48 another).
    # We use .get() to be safe if max_stock_buffer key is missing in old configs
    max_buf = SETTINGS.get("max_stock_buffer", 40)
    target_buffer = random.randint(SETTINGS["min_stock_buffer"], max_buf)
    
    available_stock = current_stock - target_buffer

    # If available_stock is <= 0, it means we have healthy stock (e.g. 35) but the 
    # random target for today was high (e.g. 45).
    # In this case, we don't stop completely; we just sell a very small amount (Slow Day).
    if available_stock <= 0:
        max_qty_allowed_today = random.randint(1, 3) 
    else:
        # Standard Pacing
        if days_until_next_refill < 1: days_until_next_refill = 1
        
        ideal_daily_burn = available_stock / days_until_next_refill
        max_qty_allowed_today = int(ideal_daily_burn * 1.5) # Allow 50% fluctuation

    # --- HANDLING FORCE LOW MODE (Purchase Day) ---
    if force_low_mode:
        # User requested "Little sales" (e.g. truck just arrived). Cap at 3-8 boxes.
        max_qty_allowed_today = min(max_qty_allowed_today, random.randint(3, 8))
    
    # Ensure minimum viability (don't sell 0 if we have plenty of stock)
    if max_qty_allowed_today < 1 and current_stock > SETTINGS["min_stock_buffer"] + 5:
        max_qty_allowed_today = 2

    # 4. Generate Sales
    daily_sales = []
    qty_sold_today = 0
    temp_stock = current_stock
    inv_counter = last_invoice
    
    # Use override if provided, otherwise fallback safely
    final_rate = rate_override if rate_override is not None else SETTINGS.get("rate_box", 350)

    random.shuffle(customers)
    
    for cust in customers:
        if qty_sold_today >= max_qty_allowed_today: break
        if temp_stock <= SETTINGS["min_stock_buffer"]: break

        remaining_cap = max_qty_allowed_today - qty_sold_today
        possible_qty = min(SETTINGS["max_qty_per_user"], remaining_cap)
        
        if possible_qty < 1: break
        
        qty = random.randint(1, possible_qty)

        temp_stock -= qty
        qty_sold_today += qty
        inv_counter += 1
        
        taxable = qty * final_rate
        
        sale = {
            "_customer_name": cust.get("name", "Unknown"),
            "_product_name": product_name, 
            "GSTIN": cust.get("gstin", ""),
            "INVOICE": f"{SETTINGS['invoice_prefix']}{inv_counter}",
            "DATE": date_str,
            "INV_VAL": taxable,
            "PLACE": SETTINGS["place_code"],
            "REV_CHG": "N",
            "INV_TYPE": "Regular",
            "E_COMM": "",
            "RATE": 0,
            "TAXABLE": taxable,
            "IGST": 0,
            "CGST": 0,
            "SGST": 0,
            "_qty": qty
        }
        daily_sales.append(sale)

    if not daily_sales:
        return current_stock, [], last_invoice, "Quiet Day (Pacing/Low Stock)"

    return temp_stock, daily_sales, inv_counter, "Active"