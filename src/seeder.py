import pandas as pd
import numpy as np
import importlib
import sys
import math
# from supabase import create_client

# --- KONFIGURASI ---
# Masukkan kredensial Supabase Anda di sini
SUPABASE_URL = "https://bfbysovrwgoegubpgnhk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmYnlzb3Zyd2dvZWd1YnBnbmhrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzczNDAwMywiZXhwIjoyMDc5MzEwMDAzfQ.eqygtDhBRK9CbXmnGtr_3RJF1cjwHx89082WfVwMSBY" # Gunakan service_role key jika ada, atau anon key
CSV_FILE = "data/database/current/laptops_current_export.csv"
TABLE_NAME = "products_current"

# Inisialisasi Client (import supabase secara dinamis untuk menghindari error resolusi import statis)
try:
    supabase_mod = importlib.import_module("supabase")
    create_client = getattr(supabase_mod, "create_client")
except Exception as e:
    raise ImportError(
        "The 'supabase' package is not installed or could not be imported. "
        "Install it with: pip install supabase"
    ) from e

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_data():
    print("Membaca file CSV...")
    df = pd.read_csv(CSV_FILE)
    
    print("Membersihkan data...")
    
    # 1. Ubah Infinity menjadi NaN (jaga-jaga jika ada pembagian 0)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # 2. PENTING: Ubah NaN menjadi None agar diterima JSON Supabase
    # Kita ubah dulu ke tipe object agar kolom angka bisa menampung None
    df = df.astype(object).where(pd.notnull(df), None)

    total_rows = len(df)
    batch_size = 1000
    
    print(f"Total data: {total_rows} baris. Mulai upload...")

    for i in range(0, total_rows, batch_size):
        # Ambil potongan data
        batch = df.iloc[i : i + batch_size].to_dict(orient='records')
        
        try:
            # Kirim ke Supabase
            response = supabase.table(TABLE_NAME).insert(batch).execute()
            print(f"[OK] Batch {i} - {i + len(batch)} berhasil.")
        except Exception as e:
            print(f"[ERROR] Batch {i} gagal: {e}")
            # Kita stop dulu jika ada error agar bisa dibaca log-nya
            break 

    print("=== Proses Selesai ===")

if __name__ == "__main__":
    upload_data()