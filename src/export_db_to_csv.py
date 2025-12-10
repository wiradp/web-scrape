import sqlite3
import pandas as pd
import os
from datetime import datetime
from logger_setup import setup_logger

logger = setup_logger("export_csv")

def export_db_to_csv(db_path: str, table_name: str, output_csv: str):
    """
    Mengekstrak data dari tabel SQLite dan menyimpannya ke file CSV (with logging).
    """
    logger.info("=== START EXPORT CSV PROCESS ===")
    logger.info(f"Source DB: {db_path}")
    logger.info(f"Table Name: {table_name}")
    logger.info(f"Output CSV: {output_csv}")

    # 1. Validasi database
    if not os.path.exists(db_path):
        logger.error(f"Database tidak ditemukan: {db_path}")
        return
    
    # 2. Pastikan direktori CSV ada
    output_dir = os.path.dirname(output_csv)
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Output directory verified: {output_dir}")

    try:
        conn = sqlite3.connect(db_path)
        query = f"SELECT * FROM {table_name}"

        logger.info(f"Membaca data dari tabel '{table_name}'...")
        df = pd.read_sql(query, conn)

        logger.info(f"Total baris yang berhasil dibaca: {len(df)}")

        # Export CSV
        df.to_csv(output_csv, index=False)
        logger.info(f"CSV berhasil dibuat di: {output_csv}")

    except pd.io.sql.DatabaseError as e:
        logger.exception(f"DatabaseError saat membaca tabel {table_name}: {e}")

    except Exception as e:
        logger.exception(f"Unexpected error saat export: {e}")

    finally:
        try:
            conn.close()
            logger.info("Koneksi database ditutup.")
        except:
            pass

    logger.info("=== EXPORT CSV PROCESS FINISHED ===\n")


if __name__ == '__main__':
    DB_FILE = 'data/database/current/laptops_current.db'
    TABLE = 'products_current'
    CSV_FILENAME = 'laptops_current_export.csv'

    # CSV disimpan ke folder data/csv
    OUTPUT_DIR = 'data/csv'
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, CSV_FILENAME)

    export_db_to_csv(DB_FILE, TABLE, OUTPUT_FILE)