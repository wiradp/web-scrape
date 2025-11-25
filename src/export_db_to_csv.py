import sqlite3
import pandas as pd
import os
from datetime import datetime

def export_db_to_csv(db_path: str, table_name: str, output_csv: str):
    """
    Mengekstrak data dari tabel SQLite dan menyimpannya ke file CSV.
    """
    # 1. Pastikan file database ada
    if not os.path.exists(db_path):
        print(f"Error: Database tidak ditemukan di {db_path}")
        return
    
    # 2. Pastikan direktori output ada
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        
    conn = sqlite3.connect(db_path)
    # Query mengambil semua data dari tabel products_current
    # Tambahkan 'WHERE is_active = 1' jika Anda hanya ingin data yang aktif saat ini
    query = f"SELECT * FROM {table_name}"
    
    try:
        print(f"🔍 Membaca data dari tabel '{table_name}'...")
        df = pd.read_sql(query, conn)
        
        # Simpan DataFrame ke CSV
        df.to_csv(output_csv, index=False)
        print(f"✅ Berhasil mengekspor {len(df)} baris ke file:")
        print(f"   -> {output_csv}")
        
    except pd.io.sql.DatabaseError as e:
        print(f"Error saat membaca tabel {table_name}: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    # --- Konfigurasi Path ---
    
    # Path ke file database sumber
    DB_FILE = 'data/database/current/laptops_current.db'
    TABLE = 'products_current'
    
    # Nama file CSV yang diinginkan
    CSV_FILENAME = 'laptops_current_export.csv'
    
    # Mendapatkan path direktori dari DB_FILE (yaitu: data/database/current)
    db_dir = os.path.dirname(DB_FILE)
    
    # Gabungkan direktori dengan nama file CSV
    OUTPUT_FILE = os.path.join(db_dir, CSV_FILENAME)

    # --- Jalankan Proses Export ---
    export_db_to_csv(DB_FILE, TABLE, OUTPUT_FILE)