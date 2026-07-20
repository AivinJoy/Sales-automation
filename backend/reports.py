# backend\reports.py

import pandas as pd
import io
import calendar
import json
from openpyxl.utils import get_column_letter
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def auto_adjust_columns(writer, sheet_name, df):
    """Automatically adjusts column width to fit the content."""
    worksheet = writer.sheets[sheet_name]
    for idx, col in enumerate(df.columns):
        series = df[col]
        
        # Safely calculate the max length of data in the column
        if len(series) > 0:
            # Lambda safely converts every item to a string before checking length
            max_data_len = series.map(lambda x: len(str(x))).max()
        else:
            max_data_len = 0
            
        max_len = max(max_data_len, len(str(col))) + 2
        col_letter = get_column_letter(idx + 1)
        worksheet.column_dimensions[col_letter].width = max_len

def reorder_columns(df):
    """
    Reorders columns to match the EXACT user format.
    Order: GSTIN, INVOICE, DATE, INV_VAL, PLACE, REV_CHG, INV_TYPE, E_COMM, RATE, TAXABLE, IGST, CGST, SGST
    """
    cols = list(df.columns)
    target_order = [
        "GSTIN", "INVOICE", "DATE", "INV_VAL", "PLACE", "REV_CHG", 
        "INV_TYPE", "E_COMM", "RATE", "TAXABLE", "IGST", "CGST", "SGST"
    ]
    
    new_order = []
    
    # 1. Add target columns in the specific order
    for col in target_order:
        if col in cols:
            new_order.append(col)
            cols.remove(col)
            
    # 2. Add remaining columns (like Item Name) at the end
    new_order.extend(cols)
    
    return df[new_order]

def upload_to_supabase(filename, df, sheet_name="Sheet1"):
    """Helper: Writes DF to BytesIO (RAM) and uploads to Supabase Reports Bucket."""
    output = io.BytesIO()
    
    # Generate Excel in memory
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        auto_adjust_columns(writer, sheet_name, df)
    output.seek(0) # Rewind buffer

    # Upload to Cloud
    try:
        supabase.storage.from_("reports").upload(
            file=output.read(),
            path=filename,
            file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "upsert": "true"}
        )
        print(f"✅ Uploaded {filename} to Cloud Storage")
        return filename
    except Exception as e:
        print(f"❌ Upload Failed: {e}")
        return None

def generate_excel_report(sales_data, month, year):
    """Creates Excel in memory and uploads to Cloud."""
    df = pd.DataFrame(sales_data)
    
    # Remove internal tracking fields
    drop_cols = [c for c in ["_qty", "_customer_name"] if c in df.columns]
    if drop_cols: 
        df = df.drop(columns=drop_cols)
    
    # Apply strict formatting
    if not df.empty: 
        df = reorder_columns(df)
    
    month_name = calendar.month_name[month]
    filename = f"{month_name}_{year}.xlsx"
    
    return upload_to_supabase(filename, df, "Sales_Log")

def update_daily_log_excel(all_sales_log):
    """Updates the Live Sales Log in Cloud."""
    df = pd.DataFrame(all_sales_log)
    
    drop_cols = [c for c in ["_qty", "_customer_name"] if c in df.columns]
    if drop_cols: 
        df = df.drop(columns=drop_cols)
        
    if not df.empty: 
        df = reorder_columns(df)
    
    upload_to_supabase("Live_Sales_Log.xlsx", df, "Live_Log")

def generate_summary_report(year, period):
    """
    Downloads monthly files from Cloud, merges them, and uploads the summary.
    period: 'annual', 'h1' (Jan-Jun), 'h2' (Jul-Dec)
    """
    if period == "h1":
        months = range(1, 7)
        title = "Half_Yearly_Report_H1"
    elif period == "h2":
        months = range(7, 13)
        title = "Half_Yearly_Report_H2"
    else:
        months = range(1, 13)
        title = "Annual_Report"

    all_data = []
    
    print(f"Generating Summary for {period}...")

    # Scan Cloud for monthly files
    for m in months:
        month_name = calendar.month_name[m]
        filename = f"{month_name}_{year}.xlsx"
        
        try:
            # Download file to memory
            data = supabase.storage.from_("reports").download(filename)
            df = pd.read_excel(io.BytesIO(data))
            df['Month_Num'] = m
            all_data.append(df)
            print(f"  Merged {filename}")
        except: 
            pass # File might not exist yet, skip it

    if not all_data:
        return None, "No monthly files found in Cloud for this period."

    # Merge Data
    merged_df = pd.concat(all_data, ignore_index=True)
    
    # Create Summary Pivot
    if 'TAXABLE' in merged_df.columns:
        summary_pivot = merged_df.groupby('Month_Num')['TAXABLE'].sum().reset_index()
        summary_pivot.columns = ['Month', 'Total_Revenue']
    else:
        summary_pivot = pd.DataFrame()

    # Save Summary to Cloud
    output_filename = f"{title}_{year}.xlsx"
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        merged_df.to_excel(writer, sheet_name="Consolidated_Data", index=False)
        summary_pivot.to_excel(writer, sheet_name="Summary_Table", index=False)
        auto_adjust_columns(writer, "Consolidated_Data", merged_df)
    output.seek(0)

    try:
        supabase.storage.from_("reports").upload(
            file=output.read(),
            path=output_filename,
            file_options={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "upsert": "true"}
        )
        return output_filename, f"Merged {len(all_data)} files from Cloud."
    except Exception as e:
        return None, f"Upload Failed: {e}"

def save_audit_log(audit_data, month_name, year):
    """Saves audit log as JSON to Cloud."""
    filename = f"{month_name}_{year}_Audit.json"
    json_str = json.dumps(audit_data, indent=4)
    
    try:
        supabase.storage.from_("reports").upload(
            file=json_str.encode(), # Convert string to bytes
            path=filename,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
    except Exception as e:
        print(f"Audit Upload Error: {e}")

def save_purchase_log(purchase_data, month_name, year):
    """Saves purchase log as JSON to Cloud."""
    filename = f"{month_name}_{year}_Purchases.json"
    json_str = json.dumps(purchase_data, indent=4)
    
    try:
        supabase.storage.from_("reports").upload(
            file=json_str.encode(),
            path=filename,
            file_options={"content-type": "application/json", "upsert": "true"}
        )
    except Exception as e:
        print(f"Purchase Log Upload Error: {e}")

# --- REPORT RETRIEVAL FUNCTIONS (Used by Main API) ---

def get_report_url(filename):
    """Generates a temporary download URL for the file."""
    try:
        # Create a signed URL valid for 60 seconds
        res = supabase.storage.from_("reports").create_signed_url(filename, 60)
        return res.get("signedURL")
    except Exception as e:
        return None

def list_cloud_reports():
    """Lists Excel files in the Supabase bucket."""
    try:
        res = supabase.storage.from_("reports").list()
        # Filter for .xlsx
        files = [f['name'] for f in res if f['name'].endswith('.xlsx')]
        return sorted(files, reverse=True)
    except:
        return []

def list_cloud_purchases():
    """Lists purchase logs in the Supabase bucket."""
    try:
        res = supabase.storage.from_("reports").list()
        files = [f['name'] for f in res if f['name'].endswith('_Purchases.json')]
        return sorted(files, reverse=True)
    except:
        return []

def read_cloud_json(filename):
    """Downloads and reads a JSON file from cloud to memory."""
    try:
        data = supabase.storage.from_("reports").download(filename)
        return json.loads(data)
    except Exception as e:
        print(e)
        return None

def read_cloud_excel(filename):
    """Downloads Excel from cloud and reads into Pandas."""
    try:
        data = supabase.storage.from_("reports").download(filename)
        return pd.read_excel(io.BytesIO(data)).fillna("")
    except Exception as e:
        print(e)
        return None