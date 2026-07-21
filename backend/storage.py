# backend\storage.py

from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_state():
    """
    Fetches live invoice/revenue stats from app_state, and per-product
    stock from product_stock (joined with products for names).
    """
    try:
        response = supabase.table("app_state").select("id, last_invoice, total_revenue").eq("id", 1).single().execute()
        data = response.data

        return {
            "stock_map": get_product_stock_map(),
            "last_invoice": data.get("last_invoice", 4520),
            "total_sales_val": data.get("total_revenue", 0),
            "sales_log": [] 
        }
    except Exception as e:
        print(f"⚠️ DB Error loading state: {e}")
        return {
            "stock_map": {}, 
            "last_invoice": 4520, 
            "total_sales_val": 0, 
            "sales_log": []
        }

def save_state(state):
    """
    Updates last_invoice/total_revenue in app_state, and syncs stock
    for every product present in state['stock_map'] individually.
    """
    try:
        payload = {
            "last_invoice": state.get("last_invoice"),
            "total_revenue": state.get("total_sales_val")
        }
        supabase.table("app_state").update(payload).eq("id", 1).execute()

        stock_map = state.get("stock_map", {})
        for product_name, stock_qty in stock_map.items():
            update_product_stock(product_name, stock_qty)
    except Exception as e:
        print(f"❌ DB Error saving state: {e}")


# --- NEW: PRODUCT MANAGEMENT ---

def get_products():
    """Fetches all products (id, name, rate) from Supabase."""
    try:
        response = supabase.table("products").select("*").execute()
        return response.data
    except Exception as e:
        print(f"❌ DB Error fetching products: {e}")
        return []

def get_product_stock_map():
    """Returns {product_name: current_stock} by joining product_stock -> products."""
    try:
        response = supabase.table("product_stock").select("current_stock, products(name)").execute()
        stock_map = {}
        for row in response.data:
            name = row["products"]["name"]
            stock_map[name] = row["current_stock"]
        return stock_map
    except Exception as e:
        print(f"❌ DB Error fetching product stock: {e}")
        return {}

def update_product_stock(product_name, new_stock):
    """Looks up a product by name and updates its stock row."""
    try:
        prod = supabase.table("products").select("id").eq("name", product_name).single().execute()
        product_id = prod.data["id"]
        supabase.table("product_stock").update({"current_stock": new_stock}).eq("product_id", product_id).execute()
    except Exception as e:
        print(f"❌ DB Error updating stock for '{product_name}': {e}")

def add_product(name, rate):
    """Creates a new product + its initial (zero) stock row."""
    try:
        result = supabase.table("products").insert({"name": name, "rate": rate}).execute()
        new_id = result.data[0]["id"]
        supabase.table("product_stock").insert({"product_id": new_id, "current_stock": 0}).execute()
        return result.data[0]
    except Exception as e:
        print(f"❌ DB Error adding product '{name}': {e}")
        return None

def update_product_rate(product_id, rate):
    """Updates a product's rate going forward. Past reports are unaffected since they store the rate used at simulation time."""
    try:
        supabase.table("products").update({"rate": rate}).eq("id", product_id).execute()
    except Exception as e:
        print(f"❌ DB Error updating rate for product {product_id}: {e}")

def get_customers():
    """
    Fetches customer list from Supabase Cloud.
    Replaces reading from 'customers.json'.
    """
    try:
        response = supabase.table("customers").select("*").execute()
        
        # Convert DB rows back to your App's simple list format
        customers = []
        for row in response.data:
            customers.append({
                "name": row["name"],
                "gstin": row["gstin"]
            })
        return customers
    except Exception as e:
        print(f"❌ DB Error fetching customers: {e}")
        return []

def save_snapshot(snapshot_data):
    """
    Inserts a new monthly snapshot row into the 'monthly_snapshots' table.
    """
    try:
        # This inserts the new record without affecting your 'app_state' table
        supabase.table("monthly_snapshots").insert(snapshot_data).execute()
        print("✅ Snapshot saved to history.")
    except Exception as e:
        print(f"❌ DB Error saving snapshot: {e}")    