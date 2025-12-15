"""
ETL with SCD Type 2 + Changes Log (production-ready)
- Reads raw scraped SQLite DB (table: products_raw)
- Runs feature extraction hooks (placeholder - reuse your existing functions or import them)
- Computes product_hash (business key) in ETL
- Collapses raw into a snapshot (latest per product_hash)
- Performs SCD Type 2 upsert logic:
    * If product_hash not in current -> insert new (is_active=1)
    * If product_hash exists and any tracked attributes changed -> close previous (valid_to) and insert new version
    * If product_hash existed but missing from latest snapshot -> mark previous as inactive (discontinued)
- Writes audit/meta info into meta DB (etl_runs + changes_log)
- Logging integrated
Usage:
    python src/etl.py
Configurable via parameters to run_etl(...)
"""

import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Tuple, Dict, Any
import pandas as pd
import hashlib
import json

from logger_setup import setup_logger
from extractors import (
    get_brands,
    extract_brand,
    extract_series,
    extract_processor,
    standardize_processor,
    extract_gpu,
    standardize_gpu,
    extract_ram,
    extract_storage,
    extract_display
)

logger = setup_logger("etl")

# -------------------------
# Configuration defaults
# -------------------------
DEFAULTS = {
    "INPUT_DB": "data/database/raw/laptops_data_raw.db",
    "CURRENT_DB": "data/database/current/laptops_current.db",
    "HISTORY_DB": "data/database/history/laptops_history.db",
    "META_DB": "data/database/meta/laptops_meta.db",
    "RAW_TABLE": "products_raw",
    "CURRENT_TABLE": "products_current",
    "HISTORY_TABLE": "products_history",
    "META_RUNS_TABLE": "etl_runs",
    "META_CHANGES_TABLE": "changes_log",
}

# -------------------------
# Utilities
# -------------------------
def now_iso() -> str:
    """Return current UTC time in ISO format (no microseconds)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def compute_product_hash(product_name: str) -> str:
    """
    Business key: deterministic hash based on normalized product_name.
    Normalize: lowercase, strip, collapse whitespace, remove punctuation that doesn't matter.
    """
    if pd.isna(product_name):
        product_name = ""
    s = str(product_name).lower().strip()
    # collapse whitespace
    s = re.sub(r'\s+', ' ', s)
    # optionally remove characters like quotes or repeated punctuation (but keep alnum & spaces)
    s = re.sub(r'[^0-9a-zA-Z\s]', '', s)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def ensure_dirs(*paths):
    for p in paths:
        d = os.path.dirname(p)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

# -------------------------
# Schema helpers: create tables if not exist
# -------------------------
def ensure_current_table(conn: sqlite3.Connection, table_name: str = DEFAULTS["CURRENT_TABLE"]) -> None:
    cur = conn.cursor()
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_id INTEGER,
        product_hash TEXT,
        product_name TEXT,
        brand TEXT,
        series TEXT,
        processor_detail TEXT,
        processor_category TEXT,
        gpu TEXT,
        gpu_category TEXT,
        ram TEXT,
        storage TEXT,
        display TEXT,
        price_raw INTEGER,
        price_in_millions REAL,
        processed_at TEXT,
        valid_from TEXT,
        valid_to TEXT,
        is_active INTEGER DEFAULT 1
    );
    """)
    # Indexes to speed lookups
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_hash ON {table_name}(product_hash);")
    conn.commit()

def ensure_history_table(conn: sqlite3.Connection, table_name: str = DEFAULTS["HISTORY_TABLE"]) -> None:
    cur = conn.cursor()
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_id INTEGER,
        product_hash TEXT,
        product_name TEXT,
        brand TEXT,
        series TEXT,
        processor_detail TEXT,
        processor_category TEXT,
        gpu TEXT,
        gpu_category TEXT,
        ram TEXT,
        storage TEXT,
        display TEXT,
        price_raw INTEGER,
        price_in_millions REAL,
        processed_at TEXT,
        valid_from TEXT,
        valid_to TEXT,
        is_active INTEGER DEFAULT 0
    );
    """)
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_hash ON {table_name}(product_hash);")
    conn.commit()

def ensure_meta_tables(conn: sqlite3.Connection,
                       runs_table: str = DEFAULTS["META_RUNS_TABLE"],
                       changes_table: str = DEFAULTS["META_CHANGES_TABLE"]) -> None:
    cur = conn.cursor()
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {runs_table} (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at TEXT,
        input_db TEXT,
        rows_input INTEGER,
        stats_json TEXT
    );
    """)
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS {changes_table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER,
        product_hash TEXT,
        change_type TEXT, -- 'new','price_update','attribute_update','discontinued'
        details_json TEXT,
        changed_at TEXT
    );
    """)
    conn.commit()

# -------------------------
# Core ETL logic
# -------------------------
def load_raw_as_df(raw_db_path: str, raw_table: str = DEFAULTS["RAW_TABLE"]) -> pd.DataFrame:
    """
    Load raw scraped table into DataFrame.
    Expected columns: raw_id (or id), product_name, price_raw, scraped_at (timestamp)
    If scraped_at missing, set to now.
    """
    conn = sqlite3.connect(raw_db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {raw_table};", conn)
    except Exception as e:
        logger.exception("Failed to read raw table. Check table name and DB content.")
        conn.close()
        raise
    conn.close()

    # Normalize column names
    cols = {c.lower(): c for c in df.columns}
    # rename common aliases
    rename_map = {}
    if 'id' in cols and 'raw_id' not in cols:
        rename_map[cols['id']] = 'raw_id'
    if 'scraped_at' not in df.columns:
        df['scraped_at'] = now_iso()
    # product_name / price_raw expected - otherwise raise
    if 'product_name' not in df.columns or 'price_raw' not in df.columns:
        raise ValueError("Raw table must include 'product_name' and 'price_raw' columns")

    # keep relevant columns
    df = df.rename(columns=rename_map)
    df = df[['raw_id', 'product_name', 'price_raw', 'scraped_at']].copy()
    # ensure types
    df['scraped_at'] = pd.to_datetime(df['scraped_at'], errors='coerce').fillna(pd.Timestamp(now_iso()))
    df['price_raw'] = pd.to_numeric(df['price_raw'], errors='coerce').fillna(0).astype(int)
    df['product_name'] = df['product_name'].astype(str)

    return df

def prepare_snapshot(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    From raw DataFrame produce snapshot: the latest record for each product_hash.
    Adds product_hash & price_in_millions & processed_at.
    Also collapses duplicates by computing latest scraped_at.
    """
    df = df_raw.copy()
    # compute product_hash in ETL (business key)
    df['product_hash'] = df['product_name'].apply(compute_product_hash)
    # set processed_at
    processed = now_iso()
    df['processed_at'] = processed
    df['price_in_millions'] = (df['price_raw'] / 1_000_000).round(3)
    # sort by scraped_at descending so latest come first
    df = df.sort_values(['product_hash', 'scraped_at'], ascending=[True, False])

    # collapse: keep first (latest) per product_hash
    df_snapshot = df.groupby('product_hash', as_index=False).first()

    # remove obviously empty names
    df_snapshot = df_snapshot[df_snapshot['product_name'].str.strip() != ""].reset_index(drop=True)

    return df_snapshot

def scd2_apply(snapshot: pd.DataFrame,
               current_db: str,
               history_db: str,
               meta_db: str,
               run_at: str) -> Dict[str, int]:
    """
    Apply SCD2 logic:
     - load current table
     - compare by product_hash
     - detect new products / price updates / attribute updates / discontinued
     - update products_current and products_history accordingly
    Returns stats dict: new_products, price_updates, attribute_updates, discontinued, unchanged
    """
    stats = {"new_products": 0, "price_updates": 0, "attribute_updates": 0, "discontinued": 0, "unchanged": 0, "duplicates_in_raw": 0}

    # ensure directories exist
    ensure_dirs(current_db, history_db, meta_db)

    # load current
    conn_cur = sqlite3.connect(current_db)
    ensure_current_table(conn_cur)
    cur = conn_cur.cursor()

    try:
        current_df = pd.read_sql_query(f"SELECT * FROM {DEFAULTS['CURRENT_TABLE']} WHERE is_active=1;", conn_cur)
    except Exception:
        # empty if table exists but no rows
        current_df = pd.DataFrame(columns=[
            'product_id','raw_id','product_hash','product_name','brand','series','processor_detail','processor_category',
            'gpu','gpu_category','ram','storage','display','price_raw','price_in_millions','processed_at','valid_from','valid_to','is_active'
        ])
    # map current by product_hash
    current_map = {}
    if not current_df.empty:
        # normalize index by product_hash
        current_df['product_hash'] = current_df['product_hash'].astype(str)
        current_map = current_df.set_index('product_hash').to_dict('index')

    # prepare history DB
    conn_hist = sqlite3.connect(history_db)
    ensure_history_table(conn_hist)

    # prepare meta DB
    conn_meta = sqlite3.connect(meta_db)
    ensure_meta_tables(conn_meta)
    meta_cur = conn_meta.cursor()

    # Build a set of product_hash in snapshot and current
    snapshot_hashes = set(snapshot['product_hash'].tolist())
    current_hashes = set(current_map.keys())

    # --- Detect discontinued: those in current but not in snapshot ---
    discontinued_hashes = current_hashes.difference(snapshot_hashes)
    for ph in discontinued_hashes:
        row = current_map[ph]
        # update current row: set valid_to, is_active=0
        valid_to = run_at
        try:
            cur.execute(f"""
                UPDATE {DEFAULTS['CURRENT_TABLE']}
                SET valid_to = ?, is_active = 0
                WHERE product_hash = ? AND is_active = 1;
            """, (valid_to, ph))
            conn_cur.commit()
            stats['discontinued'] += 1
            # also insert into history for archival (copy row with valid_to)
            history_row = dict(row)
            history_row['product_hash'] = ph
            history_row['valid_to'] = valid_to
            history_row['is_active'] = 0
            # remove product_id to avoid conflicts
            history_row.pop('product_id', None)
            # insert into history table
            cols = ",".join(history_row.keys())
            placeholders = ",".join(["?"]*len(history_row))
            conn_hist.execute(f"INSERT INTO {DEFAULTS['HISTORY_TABLE']} ({cols}) VALUES ({placeholders})",
                              tuple(history_row.values()))
            conn_hist.commit()

            # meta log
            meta_cur.execute(f"INSERT INTO {DEFAULTS['META_CHANGES_TABLE']} (run_id, product_hash, change_type, details_json, changed_at) VALUES (?, ?, ?, ?, ?)",
                             (None, ph, 'discontinued', json.dumps({'note': 'no longer present in latest snapshot'}), run_at))
            conn_meta.commit()
        except Exception:
            logger.exception(f"Failed to mark discontinued product: {ph}")

    # --- Upsert logic: iterate snapshot rows ---
    # We'll decide change_type by comparing a subset of tracked attributes:
    tracked_cols = ['product_name','brand','series','processor_detail','processor_category','gpu','gpu_category','ram','storage','display','price_raw']
    for _, srow in snapshot.iterrows():
        ph = srow['product_hash']
        # if not in current -> new product
        if ph not in current_map:
            # insert into current
            insert_row = {
                'raw_id': int(srow.get('raw_id')) if not pd.isna(srow.get('raw_id')) else None,
                'product_hash': ph,
                'product_name': srow.get('product_name'),
                'brand': srow.get('brand') if 'brand' in srow else None,
                'series': srow.get('series') if 'series' in srow else None,
                'processor_detail': srow.get('processor_detail') if 'processor_detail' in srow else None,
                'processor_category': srow.get('processor_category') if 'processor_category' in srow else None,
                'gpu': srow.get('gpu') if 'gpu' in srow else None,
                'gpu_category': srow.get('gpu_category') if 'gpu_category' in srow else None,
                'ram': srow.get('ram') if 'ram' in srow else None,
                'storage': srow.get('storage') if 'storage' in srow else None,
                'display': srow.get('display') if 'display' in srow else None,
                'price_raw': int(srow.get('price_raw')) if not pd.isna(srow.get('price_raw')) else None,
                'price_in_millions': float(srow.get('price_in_millions')) if not pd.isna(srow.get('price_in_millions')) else None,
                'processed_at': srow.get('processed_at'),
                'valid_from': run_at,
                'valid_to': None,
                'is_active': 1
            }
            cols = ",".join(insert_row.keys())
            placeholders = ",".join(["?"]*len(insert_row))
            cur_vals = tuple(insert_row.values())
            cur.execute(f"INSERT INTO {DEFAULTS['CURRENT_TABLE']} ({cols}) VALUES ({placeholders});", cur_vals)
            conn_cur.commit()
            stats['new_products'] += 1

            # meta log
            meta_cur.execute(f"INSERT INTO {DEFAULTS['META_CHANGES_TABLE']} (run_id, product_hash, change_type, details_json, changed_at) VALUES (?, ?, ?, ?, ?)",
                             (None, ph, 'new', json.dumps({'price_raw': insert_row['price_raw']}), run_at))
            conn_meta.commit()

        else:
            # exists in current active row: compare tracked attributes
            cur_row = current_map[ph]
            # comparison: for price change or any tracked attribute difference
            changed = {}
            for col in tracked_cols:
                sval = srow.get(col) if col in srow else None
                crow = cur_row.get(col)
                # normalize types for comparison
                sval_norm = None if pd.isna(sval) else str(sval).strip()
                crow_norm = None if crow is None else str(crow).strip()
                if sval_norm != crow_norm:
                    changed[col] = {'old': crow, 'new': sval}
            if not changed:
                stats['unchanged'] += 1
                # nothing to do
            else:
                # Close previous active record (set valid_to and is_active=0)
                try:
                    cur.execute(f"""
                        UPDATE {DEFAULTS['CURRENT_TABLE']}
                        SET valid_to = ?, is_active = 0
                        WHERE product_hash = ? AND is_active = 1;
                    """, (run_at, ph))
                    conn_cur.commit()
                except Exception:
                    logger.exception(f"Failed to close previous active row for {ph}")

                # Insert new current record with new attributes
                insert_row = {
                    'raw_id': int(srow.get('raw_id')) if not pd.isna(srow.get('raw_id')) else None,
                    'product_hash': ph,
                    'product_name': srow.get('product_name'),
                    'brand': srow.get('brand') if 'brand' in srow else None,
                    'series': srow.get('series') if 'series' in srow else None,
                    'processor_detail': srow.get('processor_detail') if 'processor_detail' in srow else None,
                    'processor_category': srow.get('processor_category') if 'processor_category' in srow else None,
                    'gpu': srow.get('gpu') if 'gpu' in srow else None,
                    'gpu_category': srow.get('gpu_category') if 'gpu_category' in srow else None,
                    'ram': srow.get('ram') if 'ram' in srow else None,
                    'storage': srow.get('storage') if 'storage' in srow else None,
                    'display': srow.get('display') if 'display' in srow else None,
                    'price_raw': int(srow.get('price_raw')) if not pd.isna(srow.get('price_raw')) else None,
                    'price_in_millions': float(srow.get('price_in_millions')) if not pd.isna(srow.get('price_in_millions')) else None,
                    'processed_at': srow.get('processed_at'),
                    'valid_from': run_at,
                    'valid_to': None,
                    'is_active': 1
                }
                cols = ",".join(insert_row.keys())
                placeholders = ",".join(["?"]*len(insert_row))
                conn_cur.execute(f"INSERT INTO {DEFAULTS['CURRENT_TABLE']} ({cols}) VALUES ({placeholders});", tuple(insert_row.values()))
                conn_cur.commit()

                # Also copy previous version into history with its valid_to (if not already copied)
                # We can copy by selecting from current history prior to update — but to keep simple, insert an archival row:
                history_row = dict(cur_row)
                history_row['product_hash'] = ph
                history_row.pop('product_id', None)
                history_row['valid_to'] = run_at
                history_row['is_active'] = 0
                cols_h = ",".join(history_row.keys())
                placeholders_h = ",".join(["?"]*len(history_row))
                conn_hist.execute(f"INSERT INTO {DEFAULTS['HISTORY_TABLE']} ({cols_h}) VALUES ({placeholders_h});", tuple(history_row.values()))
                conn_hist.commit()

                # classify change
                if 'price_raw' in changed and len(changed) == 1:
                    stats['price_updates'] += 1
                    change_type = 'price_update'
                else:
                    stats['attribute_updates'] += 1
                    change_type = 'attribute_update'

                # meta log
                meta_cur.execute(f"INSERT INTO {DEFAULTS['META_CHANGES_TABLE']} (run_id, product_hash, change_type, details_json, changed_at) VALUES (?, ?, ?, ?, ?)",
                                 (None, ph, change_type, json.dumps(changed), run_at))
                conn_meta.commit()

    # ----- finalize: ensure only one active row per product_hash -----
    # (This is a safeguard: in case duplicates exist, close extra ones by keeping the latest valid_from)
    try:
        # For each product_hash find active rows count >1 and keep latest
        active_duplicates = pd.read_sql_query(
            f"SELECT product_hash, COUNT(*) as cnt FROM {DEFAULTS['CURRENT_TABLE']} WHERE is_active=1 GROUP BY product_hash HAVING cnt > 1;",
            conn_cur
        )
        if not active_duplicates.empty:
            logger.warning(f"Found {len(active_duplicates)} product_hash with multiple active rows. Reconciling...")
            for _, row in active_duplicates.iterrows():
                ph = row['product_hash']
                rows_active = pd.read_sql_query(f"SELECT product_id, valid_from FROM {DEFAULTS['CURRENT_TABLE']} WHERE is_active=1 AND product_hash = ? ORDER BY valid_from DESC;", conn_cur, params=(ph,))
                # keep first (latest), close the rest
                keep = rows_active.iloc[0]['product_id']
                to_close = rows_active['product_id'].tolist()[1:]
                for pid in to_close:
                    conn_cur.execute(f"UPDATE {DEFAULTS['CURRENT_TABLE']} SET is_active=0, valid_to=? WHERE product_id=?;", (run_at, pid))
            conn_cur.commit()
    except Exception:
        logger.exception("Failed during duplicate active reconciliation.")

    # close connections
    conn_hist.close()
    conn_cur.close()
    conn_meta.close()

    return stats

def record_run_meta(meta_db: str, input_db: str, rows_input: int, stats: Dict[str, int], run_at: str) -> int:
    """
    Insert a run record into meta_db.etl_runs and update meta_changes entries with run_id.
    Returns run_id.
    """
    conn = sqlite3.connect(meta_db)
    ensure_meta_tables(conn)
    cur = conn.cursor()
    stats_json = json.dumps(stats)
    cur.execute(f"INSERT INTO {DEFAULTS['META_RUNS_TABLE']} (run_at, input_db, rows_input, stats_json) VALUES (?, ?, ?, ?);", (run_at, input_db, rows_input, stats_json))
    conn.commit()
    run_id = cur.lastrowid

    # attach run_id to changes_log rows that had run_id NULL
    cur.execute(f"UPDATE {DEFAULTS['META_CHANGES_TABLE']} SET run_id = ? WHERE run_id IS NULL;", (run_id,))
    conn.commit()
    conn.close()
    return run_id

# -------------------------
# Entrypoint
# -------------------------
def run_etl(input_db_path: str = DEFAULTS["INPUT_DB"],
            current_db_path: str = DEFAULTS["CURRENT_DB"],
            history_db_path: str = DEFAULTS["HISTORY_DB"],
            meta_db_path: str = DEFAULTS["META_DB"],
            raw_table: str = DEFAULTS["RAW_TABLE"]) -> Dict[str, Any]:
    """Main ETL runner. Returns a dict with run stats."""
    logger.info("="*80)
    logger.info("=== START ETL PIPELINE ===")
    run_at = now_iso()

    # ensure dirs
    ensure_dirs(input_db_path, current_db_path, history_db_path, meta_db_path)

    # 1) load raw
    try:
        df_raw = load_raw_as_df(input_db_path, raw_table)
        rows_input = len(df_raw)
        logger.info(f"📥 Berhasil membaca {rows_input} baris data raw.")
    except Exception as e:
        logger.exception("Failed loading raw data.")
        return {"status": "error", "msg": str(e)}

    # small dedupe check: count distinct product_hash after compute - used for stats
    df_raw['product_hash_temp'] = df_raw['product_name'].apply(compute_product_hash)
    distinct_after_hash = df_raw['product_hash_temp'].nunique()
    duplicates_removed = rows_input - distinct_after_hash
    if duplicates_removed > 0:
        logger.warning(f"⚠️ Dibuang {duplicates_removed} data duplikat berdasarkan business key (hash).")

    # 2) prepare snapshot (this also computes final product_hash and processed_at)
    snapshot = prepare_snapshot(df_raw)
    logger.info("🛠️ Menjalankan Feature Extraction & Snapshot preparation... (snapshot rows: %d)" % len(snapshot))

    # --- FEATURE EXTRACTION ---
    # Extract brand, series, processor, GPU, RAM, storage, display dari product_name
    brands_list = get_brands()
    
    logger.info("📝 Extracting brand...")
    snapshot['brand'] = snapshot['product_name'].apply(lambda x: extract_brand(x, brands_list))
    
    logger.info("📝 Extracting series...")
    snapshot['series'] = snapshot['product_name'].apply(extract_series)
    
    logger.info("📝 Extracting processor...")
    snapshot['processor_detail'] = snapshot['product_name'].apply(extract_processor)
    snapshot['processor_category'] = snapshot['processor_detail'].apply(standardize_processor)
    
    logger.info("📝 Extracting GPU...")
    snapshot['gpu'] = snapshot['product_name'].apply(extract_gpu)
    snapshot['gpu_category'] = snapshot['gpu'].apply(standardize_gpu)
    
    logger.info("📝 Extracting RAM...")
    snapshot['ram'] = snapshot['product_name'].apply(extract_ram)
    
    logger.info("📝 Extracting storage...")
    snapshot['storage'] = snapshot['product_name'].apply(extract_storage)
    
    logger.info("📝 Extracting display...")
    snapshot['display'] = snapshot['product_name'].apply(extract_display)
    
    logger.info("✅ Feature extraction completed")

    # 3) Apply SCD2 logic
    stats = scd2_apply(snapshot, current_db_path, history_db_path, meta_db_path, run_at)

    # 4) Record meta run (attach run_id to changes rows)
    run_id = record_run_meta(meta_db_path, input_db_path, rows_input, stats, run_at)
    logger.info(f"Run logged to meta_db with run_id: {run_id}")

    logger.info(f"=== ETL SELESAI. Stats: {stats} ===")
    logger.info("="*80)
    return {"status": "ok", "rows_input": rows_input, "meta_run_id": run_id, **stats}

# -------------------------
# CLI run
# -------------------------
if __name__ == "__main__":
    # default paths (you can override by editing the call below)
    res = run_etl()
    print(res)
