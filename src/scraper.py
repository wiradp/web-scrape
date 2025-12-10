"""Production-ready scraper module.
Contains a polite scraping function with retries, user-agent rotation, and saving to CSV.
"""
import requests
from bs4 import BeautifulSoup
import time, random, logging, re
from typing import List, Dict, Optional
from urllib.parse import urljoin
import sqlite3
import os
from datetime import datetime
from logger_setup import setup_logger

logger = setup_logger("scraper")

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
}

def fetch_url(url: str, headers: Optional[dict]=None, timeout: int=10, retries: int=3) -> Optional[str]:
    headers = headers or DEFAULT_HEADERS
    logger.info(f"Fetching URL: {url}")
    for attempt in range(1, retries+1):
        try:
            start = time.time()
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            elapsed = round(time.time() - start , 2)
            logger.info(f"Fetched success in {elapsed}s (status={resp.status_code}, size={len(resp.text)} char)")

            return resp.text
        
        except Exception as e:
            logger.warning(f"[Attempt {attempt}/{retries}] Failed fetching {url}: {e}")
            sleep_time = min(2**attempt, 10) + random.random()
            logger.info(f"Retrying in {sleep_time:.1f}s...")
            time.sleep(sleep_time)
    logger.error(f"Giving up after {retries} attempts to fetch {url}.")
    return None

def clean_text(text):
    """
    Cleaning text from whitespace characters (\r, \n, \t) and multiple spaces.
    """
    if not text:
        return text
    
    # Replace \r, \n, \t with space
    cleaned = re.sub(r'[\r\n\t]+', ' ', text)
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Trim leading and trailing spaces
    return cleaned.strip()

def parse_listing_page(html: str, base_url: str = None) -> List[Dict]:
    """
    Extract product information from <table> elements with text cleaning.
    The base_url parameter is not used but is retained for compatibility.
    """
    logger.info("Parsing listing page...")
    soup = BeautifulSoup(html, 'lxml')
    items = []

    # Targeting the main table on the page
    table = soup.find('table')
    if not table:
        logger.error("Table element not found in page.")
        return []

    # Take all rows (tr) in the table
    rows = table.find_all('tr')
    
    # Loop through each row, skipping the header row if necessary
    for row in rows[1:]: # Starting from index 1 to skip the header
        try:
            cols = row.find_all('td')
            # Ensure that the row has at least 2 columns (name and price)
            if len(cols) >= 2:
                # The first column (index 0) is the product name - CLEANED
                raw_name = cols[0].get_text()
                name = clean_text(raw_name)
                
                # The second column (index 1) is the price - CLEANED
                raw_price = cols[1].get_text()
                price_str = clean_text(raw_price)
                
                # Remove ‘Rp’, ‘.’, and spaces from the price
                price_cleaned = int(re.sub(r'[^\d]', '', price_str))
                
                # Only add if the name and price are valid
                if name and price_cleaned > 0:
                    items.append({
                        'product_name': name,
                        'price_raw': price_cleaned
                    })
                    
        except (ValueError, IndexError) as e:
            # Skip lines that may be empty or have incorrect formatting.
            logger.warning(f"Skipping row due to error: {e}")
            continue
        
        logger.info(f"Parsing completed. Total items parsed: {len(items)}")
    return items

def normalize_name_for_dedupe(s: str) -> str:
    if not isinstance(s, str): return ""
    s = s.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    return s

DB_PATH = "data/database/raw/laptops_data_raw.db"

def save_snapshot_dedup(rows: List[Dict], db_path: str = DB_PATH):
    """Snapshot mode: drop/create products_raw, but dedupe entries by normalized name before insert."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    logger.info(f"Saving snapshot to {db_path} (dedup before insert)...")
    # dedupe by normalized product_name (keep first occurrence)
    seen = set()
    deduped = []
    for r in rows:
        key = normalize_name_for_dedupe(r['product_name'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    now_iso = datetime.utcnow().isoformat(sep=' ', timespec='seconds')  # e.g. '2025-11-24 21:38:00'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS products_raw;")
    cur.execute("""
        CREATE TABLE products_raw (
            raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            price_raw INTEGER,
            scraped_at TEXT
        );
    """)
    records = [(r['product_name'], r['price_raw'], now_iso) for r in deduped]
    cur.executemany("INSERT INTO products_raw (product_name, price_raw, scraped_at) VALUES (?, ?, ?);", records)
    conn.commit()
    conn.close()
    logger.info(f"Snapshot save complete. {len(records)} rows written (deduped from {len(rows)}).")
    
if __name__ == '__main__':
    # URL Target
    url = "https://viraindo.com/notebook.html"
    logger.info("=== START SCRAPER ===")
    html = fetch_url(url)
    if not html:
        logger.error("HTML fetch failed.")
        raise SystemExit(1)
    items = parse_listing_page(html)
    if not items:
        logger.warning("No items parsed. Exiting.")
        raise SystemExit(0)
    save_snapshot_dedup(items, DB_PATH)
    logger.info("=== SCRAPER FINISHED ===")

            
