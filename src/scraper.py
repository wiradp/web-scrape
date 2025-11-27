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
    'User-Agent': 'web-scrape-bot/1.0 (+https://wiradp.github.io)'
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
    Membersihkan teks dari whitespace characters (\r, \n, \t) dan multiple spaces.
    """
    if not text:
        return text
    
    # Replace \r, \n, \t dengan space
    cleaned = re.sub(r'[\r\n\t]+', ' ', text)
    # Replace multiple spaces dengan single space
    cleaned = re.sub(r'\s+', ' ', cleaned)
    # Trim leading and trailing spaces
    return cleaned.strip()

def parse_listing_page(html: str, base_url: str) -> List[Dict]:
    """
    Mengekstrak informasi produk dari elemen <table> dengan pembersihan teks.
    """
    logger.info("Parsing listing page...")
    soup = BeautifulSoup(html, 'lxml')
    items = []

    # Menargetkan tabel utama di halaman
    table = soup.find('table')
    if not table:
        logger.error("Table element not found in page.")
        return []

    # Mengambil semua baris (tr) di dalam tabel
    rows = table.find_all('tr')
    
    # Loop melalui setiap baris, lewati baris header jika perlu
    for row in rows[1:]: # Mulai dari indeks 1 untuk melewati header
        try:
            cols = row.find_all('td')
            # Memastikan baris memiliki setidaknya 2 kolom (nama dan harga)
            if len(cols) >= 2:
                # Kolom pertama (indeks 0) adalah nama produk - DIBERSIHKAN
                raw_name = cols[0].get_text()
                name = clean_text(raw_name)
                
                # Kolom kedua (indeks 1) adalah harga - DIBERSIHKAN
                raw_price = cols[1].get_text()
                price_str = clean_text(raw_price)
                
                # Membersihkan harga dari 'Rp', '.', dan spasi
                price_cleaned = int(re.sub(r'[^\d]', '', price_str))
                
                # Hanya tambahkan jika nama dan harga valid
                if name and price_cleaned > 0:
                    items.append({
                        'product_name': name,
                        'price_raw': price_cleaned
                    })
                    
        except (ValueError, IndexError) as e:
            # Lewati baris yang mungkin kosong atau formatnya salah
            logger.warning(f"Skipping row due to error: {e}")
            continue
        
        logger.info(f"Parsing completed. Total items extracted: {len(items)}")
    return items

db_path = "data/database/raw/laptops_data_raw.db"

def save_to_db_snapshot(rows: List[Dict], db_path: str):
    """
    Menyimpan data dengan metode SNAPSHOT.
    Tabel lama DIHAPUS, Tabel baru DIBUAT.
    """
    logger.info(f"Saving {len(rows)} raw items to DB snapshot: {db_path}")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Resetting Raw Database (Snapshot Mode)...")
            
    # 1. HAPUS TABEL LAMA (Drop Table)
    cursor.execute("DROP TABLE IF EXISTS products_raw")

    # 2. BUAT TABEL BARU (Create Table)
    cursor.execute("""
        CREATE TABLE products_raw (
            raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT,
            price_raw INTEGER,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 3. INSERT SEMUA DATA (Bulk Insert)
    # Kita insert timestamp saat ini
    current_time = datetime.now()
    records = [(item['product_name'], item['price_raw'], current_time) for item in rows]
    logger.info(f"Inserted {len(records)} new unique items into products_raw table.")

    cursor.executemany("""
        INSERT INTO products_raw (product_name, price_raw, scraped_at)
        VALUES (?, ?, ?);
    """, records)

    conn.commit()
    output_count = cursor.rowcount
    conn.close()
    
    logger.info(f"Snapshot complete. {output_count} records saved")
    
if __name__ == '__main__':
    # URL Target
    url = 'https://viraindo.com/notebook.html'
    
    logger.info("=== START SCRAPER PIPELINE ===")
    html = fetch_url(url)
    
    if not html:
        logger.error("HTML fetch failed. Exiting scraper.")
        exit()

    items = parse_listing_page(html, url)
    if not items:
        logger.warning("No items found during parsing.")
        exit()

    save_to_db_snapshot(items, db_path="data/database/raw/laptops_data_raw.db")

    logger.info("=== SCRAPER COMPLETED SUCCESSFULLY ===")

            
