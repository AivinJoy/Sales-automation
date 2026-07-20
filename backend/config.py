# backend\config.py

import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Locate and load the .env file dynamically
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

# --- FILE PATHS (Keep these for temporary operations) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# Ensure folders exist (just in case)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- SUPABASE CREDENTIALS ---
# These are the keys required to talk to your Cloud Database
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Note: In production, keep this key secret. For now, it matches your migration script.
SUPABASE_KEY = os.getenv("SUPABASE_API")

# --- BUSINESS RULES ---
SETTINGS = {
    # Product Details (Defaults)
    "item_name": "Product A",
    "rate_per_box": 350,
    "rate_liquid": 280,
    
    # Invoice Settings
    "starting_invoice": 4520,
    "invoice_prefix": "A",
    "place_code": "32-KERALA",

    # Stock Logic
    "min_stock_buffer": 20,       # Stock won't drop below this if possible
    "max_stock_buffer": 50,       # Cap for random logic
    "max_qty_per_user": 9,        # Max boxes one customer can buy
    
    # Simulation Logic
    "quiet_day_chance": 0.25,     # 25% chance of a "No Sales" day
}

# --- PRODUCT LIST ---
PRODUCTS = {
    "Soore Box": 350,
    "Soore Liquid": 280
}

# --- PUBLIC HOLIDAYS (DD/MM/YYYY) ---
# Dates where NO sales will happen.
HOLIDAYS = [
    # --- 2025 ---
    "02/01/2025", # Mannam Jayanti
    "26/01/2025", # Republic Day
    "26/02/2025", # Maha Shivaratri
    "14/03/2025", # Holi
    "31/03/2025", # Eid-ul-Fitr
    "10/04/2025", # Mahavir Jayanti
    "14/04/2025", # Vishu
    "18/04/2025", # Good Friday
    "01/05/2025", # May Day
    "06/06/2025", # Eid-ul-Adha (Bakrid)
    "06/07/2025", # Muharram
    "15/08/2025", # Independence Day
    "04/09/2025", # First Onam
    "05/09/2025", # Thiruvonam / Eid-e-Milad
    "07/09/2025", # Sree Narayana Guru Jayanti
    "21/09/2025", # Sree Narayana Guru Samadhi
    "01/10/2025", # Maha Navami
    "02/10/2025", # Gandhi Jayanti / Dussehra
    "21/10/2025", # Diwali
    "25/12/2025", # Christmas

    # --- 2026 ---
    "02/01/2026", # Mannam Jayanti
    "26/01/2026", # Republic Day
    "15/02/2026", # Maha Shivaratri
    "21/03/2026", # Idul Fitr
    "03/04/2026", # Good Friday
    "05/04/2026", # Easter Sunday
    "14/04/2026", # Vishu / Ambedkar Jayanti
    "01/05/2026", # May Day
    "27/05/2026", # Bakrid
    "15/08/2026", # Independence Day
    "25/08/2026", # First Onam
    "26/08/2026", # Eid e Milad
    "27/08/2026", # Thiruvonam
    "21/09/2026", # Sree Narayana Guru Samadhi
    "26/09/2026", # Sree Narayana Guru Jayanti
    "02/10/2026", # Gandhi Jayanti
    "19/10/2026", # Maha Navami
    "20/10/2026", # Vijaya Dashami
    "08/11/2026", # Diwali
    "25/12/2026", # Christmas
]