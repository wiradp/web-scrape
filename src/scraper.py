"""Production-ready scraper module.
Contains a polite scraping function with retries, user-agent rotation, and saving to CSV.
"""
import requests
from bs4 import BeautifulSoup
import time, random, csv, hashlib, logging, re
from typing import List, Dict, Optional
from urllib.parse import urljoin
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    'User-Agent': 'web-scrape-bot/1.0 (+https://wiradp.github.io)'
}

def fetch_url(url: str, headers: Optional[dict]=None, timeout: int=10, retries: int=3) -> Optional[str]:
    headers = headers or DEFAULT_HEADERS
    for attempt in range(1, retries+1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.warning(f"fetch_url attempt {attempt} failed for {url}: {e}")
            time.sleep(min(2**attempt, 10) + random.random())
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
    soup = BeautifulSoup(html, 'lxml')
    items = []

    # Menargetkan tabel utama di halaman
    table = soup.find('table')
    if not table:
        print("Elemen <table> tidak ditemukan.")
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
            continue
        except Exception as e:
            print(f"Error memproses baris: {e}")
            continue
    
    return items
    
def save_to_db(rows: List[Dict], db_path: str = 'data/database/raw/laptop_data_raw.db'):
    """
    Menyimpan data yang dikumpulkan ke dalam basis data SQLite pada tabel `product_raw`.
    Membuat tabel jika belum ada.
    Menggunakan executemany untuk penyisipan massal yang efisien.
    """
    import os
    # Buat direktori jika belum ada
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Buat table jika belum ada
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS product_raw (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   product_name TEXT NOT NULL,
                   price_raw INTEGER NOT NULL,
                   scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                   );
    """)

    # Persiapkan data untuk bulk insert
    records = [(item['product_name'], item['price_raw'], datetime.now()) for item in rows]

    # Gunakan executemary untuk insert batch
    cursor.executemany("""
                       INSERT INTO product_raw (product_name, price_raw, scraped_at)
                       VALUES (?, ?, ?);
    """, records)

    conn.commit()
    conn.close()
    print(f'Done, {len(rows)} items save to database: {db_path}')    


if __name__ == '__main__':
    url = 'https://viraindo.com/notebook.html'
    html = fetch_url(url)
    if html:
        items = parse_listing_page(html, url)
        # Ganti save_to_csv dengan save_to_db
        save_to_db(items, 'data/database/raw/laptop_data_raw.db')
        # save_to_csv(items, 'data/csv/notebooks_viraindo_scraped.csv')
        print(f"Scraping done. Total {len(items)} items.")
    else:
        print('Scraping failed')
            
