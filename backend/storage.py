from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_state():
    """
    Fetches the live inventory and invoice stats from Supabase Cloud.
    Replaces reading from 'store_state.json'.
    """
    try:
        # Get the global state row (id=1)
        response = supabase.table("app_state").select("*").eq("id", 1).single().execute()
        data = response.data
        
        # Convert DB columns back to your App's expected format (stock_map)
        return {
            "stock_map": {
                "Soore Box": data.get("stock_box", 0),
                "Soore Liquid": data.get("stock_liquid", 0)
            },
            "last_invoice": data.get("last_invoice", 4520),
            "total_sales_val": data.get("total_revenue", 0),
            # We don't load full history into memory anymore, it's safe in the DB
            "sales_log": [] 
        }
    except Exception as e:
        print(f"⚠️ DB Error loading state: {e}")
        # Fallback safe mode if internet is down
        return {
            "stock_map": {"Soore Box": 0, "Soore Liquid": 0}, 
            "last_invoice": 4520, 
            "total_sales_val": 0, 
            "sales_log": []
        }

def save_state(state):
    """
    Updates the live inventory in Supabase Cloud.
    Replaces writing to 'store_state.json'.
    """
    try:
        stock_map = state.get("stock_map", {})
        
        # Map app data to DB columns
        payload = {
            "stock_box": stock_map.get("Soore Box", 0),
            "stock_liquid": stock_map.get("Soore Liquid", 0),
            "last_invoice": state.get("last_invoice"),
            "total_revenue": state.get("total_sales_val")
        }
        
        # Update row 1
        supabase.table("app_state").update(payload).eq("id", 1).execute()
        
    except Exception as e:
        print(f"❌ DB Error saving state: {e}")

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