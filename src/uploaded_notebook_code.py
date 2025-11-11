# Concatenated code cells from uploaded notebook

# ---- cell 1 ----
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

def fetch_page(url, headers):
    """Mengirim permintaan GET ke URL dan mengembalikan objek BeautifulSoup."""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"Error saat mengambil URL {url}: {e}")
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

# --- FUNGSI PARSING YANG DIPERBAIKI ---
def parse_products_from_table(soup):
    """
    Mengekstrak informasi produk dari elemen <table> dengan pembersihan teks.
    """
    products = []
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
                    products.append({
                        'Product_Name': name,
                        'Price': price_cleaned
                    })
        except (ValueError, IndexError) as e:
            # Lewati baris yang mungkin kosong atau formatnya salah
            continue
        except Exception as e:
            print(f"Error memproses baris: {e}")
            continue
            
    return products

# --- Alur Kerja Utama (Main Workflow) ---

if __name__ == "__main__":
    URL = "https://viraindo.com/notebook.html"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    print("Mengambil data dari halaman...")
    soup = fetch_page(URL, HEADERS)
    
    all_products = []
    if soup:
        all_products = parse_products_from_table(soup)

    if not all_products:
        print("Tidak ada produk yang ditemukan. Proses berhenti.")
    else:
        # Konversi ke DataFrame
        df = pd.DataFrame(all_products)
        
        # Simpan ke CSV
        df.to_csv('data/notebooks_viraindo.csv', index=False)
        
        print(f"\nProses scraping selesai. Total {len(df)} produk ditemukan.")
        print("Data berhasil disimpan ke 'notebooks_viraindo.csv'")
        print("\nContoh 5 data teratas:")
        print(df.head())


# ---- cell 2 ----
# Set pandas display options untuk menampilkan seluruh konten
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)

# Membaca file CSV untuk verifikasi
df = pd.read_csv('notebooks_viraindo.csv')
df.head()


# ---- cell 3 ----
# Mengcopy dataframe ke df baru bernama df_copy
df_copy = df.copy()


# ---- cell 4 ----
# Menampilkan nilai kosong pada DataFrame
df.isnull().sum()


# ---- cell 5 ----
# Menampilkan informasi DataFrame
df.info()


# ---- cell 6 ----
# Menalmpikan isi direksori all_products
all_products


# ---- cell 7 ----
# --- Fungsi untuk ekstrak fitur ---
def get_brands():
    """
    Menyediakan daftar merek laptop populer untuk ekstraksi fitur.
    """
    return [
        'Acer', 'Apple', 'Asus', 'Dell', 'HP', 'Lenovo', 'MSI', 'Samsung', 'Toshiba', 
        'Microsoft', 'Sony', 'ADVAN', 'Zyrex', 'Axioo', 'Advan', 'Xiaomi', 'Avita', 'Tecno', 'Huawei',
        'Infinix', 'Jumper', 'SPC'
    ]

def extract_brand(all_products, brand_list):
    """
    Mengekstrak merek dari nama produk berdasarkan daftar merek yang diberikan.
    """
    # Memastikan product_name adalah string
    if not isinstance(all_products, str):
        return 'Other'
    
    # Normalisasi teks untuk pencarian yang lebih baik
    product_text = all_products.strip()
    
     # Pengecekan khusus untuk model Lenovo Legion
    if re.search(r'\bLegion\s*\d', product_text, re.IGNORECASE):
        return 'Lenovo'

    for brand in brand_list:
        if re.search(r'\b' + re.escape(brand) + r'\b', product_text, re.IGNORECASE):
            return brand
    return 'Other'


# ---- cell 8 ----
def extract_processor(all_products):
    """
    Mengekstrak dan menstandardisasi nama Processor dari nama produk.
    Versi revisi - lebih akurat untuk AMD Ryzen R-series dan FX series.
    """
    name_upper = all_products.upper()
    
    # Mapping pattern untuk berbagai tipe processor dengan prioritas
    processor_patterns = [
        # 0. SNAPDRAGON X SERIES - PATTERN BARU DIPINDAHKAN LEBIH TINGGI
        (r'SNAPDRAGON\s+X\s+ELITE\s+X?1E?-?\d{2}-?\d{2,3}', 1,
         lambda m: "Snapdragon X Elite"),
        (r'SNAPDRAGON\s+X\s+ELITE', 1,
         lambda m: "Snapdragon X Elite"),
        (r'SNAPDRAGON\s+X\s+PLUS\s+X?1P?-?\d{2}-?\d{2,3}', 1,
         lambda m: "Snapdragon X Plus"),
        (r'SNAPDRAGON\s+X\s+PLUS', 1,
         lambda m: "Snapdragon X Plus"),
        (r'SNAPDRAGON\s+X\s+X1[EP]', 1,
         lambda m: "Snapdragon X Series"),
        (r'SNAPDRAGON\s+X', 1,
         lambda m: "Snapdragon X"),
        
        # 1. SNAPDRAGON TRADITIONAL SERIES (8xx series)
        (r'SNAPDRAGON\s+(\d{3}[A-Z]?)', 1,
         lambda m: f"Snapdragon {m.group(1)}"),
        (r'SNAPDRAGON\s+(\d{3})\s+CORE', 1,
         lambda m: f"Snapdragon {m.group(1)}"),
        
        # 2. MICROSOFT SQ SERIES
        (r'MICROSOFT\s+SQ[12]', 1,
        lambda m: f"Microsoft {m.group(0).replace('MICROSOFT ', '')}"),
        (r'\bSQ[12]\b', 1,
        lambda m: f"Microsoft {m.group(0)}"),

        # 3. AMD RYZEN AI MAX+ SERIES
        (r'(AMD\s+)?RYZEN\s+AI\s+MAX\s*[+]?\s*(\d{3})', 1,
         lambda m: f"AMD Ryzen AI MAX+ {m.group(2)}"),
        (r'(AMD\s+)?RYZEN\s+AI\s+MAX[+]?\s*(\d{3})', 1,
         lambda m: f"AMD Ryzen AI MAX+ {m.group(2)}"),
        (r'RYZEN\s+AI\s+MAX[+]?\s*(\d{3})', 1,
         lambda m: f"AMD Ryzen AI MAX+ {m.group(1)}"),
        
        # 4. AMD RYZEN AI SERIES
        (r'(AMD\s+)?RYZEN\s+AI\s+([579])\s+(\d{3})', 1,
         lambda m: f"AMD Ryzen AI {m.group(2)} {m.group(3)}"),
        (r'(AMD\s+)?RYZEN\s+AI\s+([579])\s*[-]?(\d{3})', 1,
         lambda m: f"AMD Ryzen AI {m.group(2)}-{m.group(3)}"),
        
        # 5. AMD RYZEN R-SERIES (R5, R7, R9) - PATTERN BARU
        (r'AMD\s+RYZEN\s+R([579])\s*[-]?(\d{4}[A-Z]*)', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        (r'RYZEN\s+R([579])\s*[-]?(\d{4}[A-Z]*)', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        (r'AMD\s+RYZEN\s+R([579])[-](\d{4}[A-Z]*)', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        
        # 6. AMD FX SERIES - PATTERN BARU
        (r'AMD\s+(FX\s*[-]?\s*(\d{4}[A-Z]?))', 1,
         lambda m: f"AMD {m.group(1)}"),
        (r'AMD\s+QUAD\s+CORE\s+(FX\s*[-]?\s*\d{4}[A-Z]?)', 1,
         lambda m: f"AMD {m.group(1)}"),
        (r'\b(FX[-]?\d{4}[A-Z]?)\b', 1,
         lambda m: f"AMD {m.group(1)}" if 'AMD' in name_upper else None),
        
        # 7. MediaTek Series
        (r'(MEDIATEK\s+(\d{4}[A-Z]?))', 1,
         lambda m: f"MediaTek {m.group(2)}"),
        (r'(MEDIATEK\s+([A-Z]?\d+))', 1,
         lambda m: f"MediaTek {m.group(2)}"),
        
        # 8. Apple M Series
        (r'\b(APPLE\s+)?(M[1-9]\s*(?:PRO|MAX|ULTRA)?)\b', 1,
         lambda m: f"Apple {m.group(2)}"),
        
        # 9. AMD Ryzen 3-digit (270, 370, dll)
        (r'AMD\s+RYZEN\s+([3579])\s+(\d{3})\b', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        (r'RYZEN\s+([3579])\s+(\d{3})\b', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        
        # 10. Snapdragon X Series (traditional patterns)
        (r'(SNAPDRAGON\s+X\s+(ELITE\s+)?X?[1-9]E?-?\d{2,3}[A-Z]?)', 1, 
         lambda m: "Snapdragon X Elite" if 'ELITE' in m.group(0) else "Snapdragon X Series"),
        (r'(SNAPDRAGON\s+X\s+PLUS\s+X?1P-?\d{2}-?\d{2,3})', 1,
         lambda m: "Snapdragon X Plus"),
        
        # 11. AMD A-Series (A4, A6, A8, A9, A10, A12)
        (r'AMD\s+(A[4689]|A10|A12)\s*[-]?(\d{4}[A-Z]?)', 1,
         lambda m: f"AMD {m.group(1)}-{m.group(2)}"),
        (r'AMD\s+(A[4689]|A10|A12)\s*(\d{4}[A-Z]?)', 1,
         lambda m: f"AMD {m.group(1)}-{m.group(2)}"),
        (r'\b(A[4689]|A10|A12)[-]?(\d{4}[A-Z]?)\b', 1,
         lambda m: f"AMD {m.group(1)}-{m.group(2)}" if 'AMD' in name_upper else None),
        
        # 12. AMD Dual Core A-series
        (r'AMD\s+DUAL\s+CORE\s+(A[4689][-]?\d{4}[A-Z]?)', 1,
         lambda m: f"AMD {m.group(1)}"),
        
        # 13. AMD Ryzen Series 4-digit dengan suffix lengkap (HS, H, U, dll)
        (r'AMD\s+RYZEN\s+([3579])\s+(\d{4}[A-Z]{1,2})', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        (r'AMD\s+RYZEN\s+([3579])\s*[-]?(\d{4}[A-Z]{1,2})', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        (r'RYZEN\s+([3579])\s+(\d{4}[A-Z]{1,2})', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        
        # 14. AMD Ryzen Series 4-digit standard (tanpa suffix atau suffix pendek)
        (r'AMD\s+RYZEN\s+([3579])\s+(\d{4}[A-Z]?)', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        (r'AMD\s+RYZEN\s+([3579])\s*[-]?(\d{4}[A-Z]?)', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        (r'RYZEN\s+([3579])\s+(\d{4}[A-Z]?)', 1,
         lambda m: f"AMD Ryzen {m.group(1)} {m.group(2)}"),
        
        # 15. Intel Core Ultra Series dengan suffix lengkap (HX, HK, dll) - PATTERN BARU DIPINDAHKAN LEBIH TINGGI
        (r'INTEL\s+CORE\s+ULTRA\s+([579])\s+(\d{3}[A-Z]{1,2})', 1,
         lambda m: f"Intel Core Ultra {m.group(1)} {m.group(2)}"),
        (r'CORE\s+ULTRA\s+([579])\s+(\d{3}[A-Z]{1,2})', 1,
         lambda m: f"Intel Core Ultra {m.group(1)} {m.group(2)}"),
        (r'\b(ULTRA\s+[579]\s+\d{3}[A-Z]{1,2})\b', 1,
         lambda m: f"Intel Core {m.group(1)}"),
        
        # 16. Intel Core i Series dengan suffix lengkap (HX, HK, HS, U, dll)
        (r'INTEL\s+CORE\s+(I[3579])\s+(\d{4,5}[A-Z]{1,2})', 1,
         lambda m: f"Intel Core {m.group(1)}-{m.group(2)}"),
        (r'CORE\s+(I[3579])\s+(\d{4,5}[A-Z]{1,2})', 1,
         lambda m: f"Intel Core {m.group(1)}-{m.group(2)}"),
        (r'\b(I[3579][-]\d{4,5}[A-Z]{1,2})\b', 1,
         lambda m: f"Intel Core {m.group(1)}"),
        
        # 17. Intel Core i Series dengan format angka lengkap (12450H, 13620H, 14900HX, dll)
        (r'INTEL\s+CORE\s+(I[3579])\s+(\d{5}[A-Z]{1,2})', 1,
         lambda m: f"Intel Core {m.group(1)}-{m.group(2)}"),
        (r'CORE\s+(I[3579])\s+(\d{5}[A-Z]{1,2})', 1,
         lambda m: f"Intel Core {m.group(1)}-{m.group(2)}"),
        (r'\b(I[3579][-]\d{5}[A-Z]{1,2})\b', 1,
         lambda m: f"Intel Core {m.group(1)}"),
        
        # 18. AMD Athlon Series
        (r'AMD\s+ATHLON\s+(\d{4}[A-Z]?)', 1,
         lambda m: f"AMD Athlon {m.group(1)}"),
        (r'AMD\s+ATHLON\s+(GOLD|SILVER)\s+(\d{4}[A-Z]?)', 1,
         lambda m: f"AMD Athlon {m.group(1)} {m.group(2)}"),
        
        # 19. Intel Xeon W-series (W-11855M, dll)
        (r'(XEON\s+(W-[1-9]\d{4}[A-Z]?))', 1,
         lambda m: f"Intel Xeon {m.group(2)}"),
        
        # 20. AMD Ryzen AI Series (traditional)
        (r'(RYZEN\s+AI\s+([579])\s*(HX\s+)?(\d{3}))', 1,
         lambda m: f"AMD Ryzen AI {m.group(2)} {m.group(4)}" if not m.group(3) 
         else f"AMD Ryzen AI {m.group(2)} HX {m.group(4)}"),
        
        # 21. Intel Core Ultra Series (standard)
        (r'(CORE\s+ULTRA\s+([579])\s+(\d{3}[A-Z]))', 2,
         lambda m: f"Intel Core Ultra {m.group(2)} {m.group(3)}"),
        
        # 22. Intel Core i Series dengan berbagai format (standard)
        (r'(CORE\s+(I[3579])\s*[-]?(\d{4}[A-Z]?))', 2,
         lambda m: f"Intel Core {m.group(2)}-{m.group(3)}"),
        (r'(CORE\s+(I[3579])\s+(\d{4}[A-Z]?))', 2,
         lambda m: f"Intel Core {m.group(2)} {m.group(3)}"),
        (r'\b(I[3579][-]\d{4}[A-Z]?)\b', 2,
         lambda m: f"Intel Core {m.group(1)}"),
        
        # 23. AMD Model Number dengan vendor eksplisit
        (r'AMD\s+(\d{4}[A-Z]{1,2})\b', 2,
         lambda m: f"AMD {m.group(1)}"),
        
        # 24. Intel Core Standard Series
        (r'(CORE\s+([3579])\s+(\d{4}[A-Z]?))', 2,
         lambda m: f"Intel Core {m.group(2)} {m.group(3)}"),
        
        # 25. Intel Processor 4-digit dengan vendor eksplisit
        (r'INTEL\s+(\d{4}[A-Z])\b', 2,
         lambda m: f"Intel {m.group(1)}"),
        
        # 26. AMD Model Number Only (3020E, 3050U, 7735HS, etc)
        (r'\bAMD\s+(\d{4}[A-Z]{1,2})\b', 2,
         lambda m: f"AMD {m.group(1)}"),
        
        # 27. Intel N Series
        (r'\b(INTEL\s+)?(N\d{3,4})\b', 3,
         lambda m: f"Intel {m.group(2)}"),
        
        # 28. Intel Celeron/Pentium Specific
        (r'(CELERON\s+([NJ]?\d{4}[A-Z]?))', 3,
         lambda m: f"Intel Celeron {m.group(2)}"),
        (r'(PENTIUM\s+(SILVER|GOLD)\s+([A-Z]?\d{4}))', 3,
         lambda m: f"Intel Pentium {m.group(2)} {m.group(3)}"),
        
        # 29. Intel Xeon Series lainnya
        (r'(XEON\s+([E]\d?[-]\d{4}[A-Z]?)\s*(V\d+)?)', 3,
         lambda m: f"Intel Xeon {m.group(2)} {m.group(3)}" if m.group(3) 
         else f"Intel Xeon {m.group(2)}"),
        (r'(XEON\s+([A-Z]?[1-9]\d{0,4}[A-Z]?))', 3,
         lambda m: f"Intel Xeon {m.group(2)}"),
    ]

    # Cari pattern dengan priority tertinggi
    for pattern, priority, formatter in processor_patterns:
        match = re.search(pattern, name_upper)
        if match:
            result = formatter(match)
            if result:  # Skip None results
                return result
    
    # Fallback: Deteksi berdasarkan vendor dan pattern umum
    vendor_keywords = [
        ('SNAPDRAGON X ELITE', 'Snapdragon X Elite'),
        ('SNAPDRAGON X PLUS', 'Snapdragon X Plus'), 
        ('SNAPDRAGON X', 'Snapdragon X'),
        ('SNAPDRAGON 8', 'Snapdragon 8 Series'),
        ('SNAPDRAGON 7', 'Snapdragon 7 Series'),
        ('SNAPDRAGON 6', 'Snapdragon 6 Series'),
        ('SNAPDRAGON 4', 'Snapdragon 4 Series'),
        ('MICROSOFT SQ1', 'Microsoft SQ1'), 
        ('MICROSOFT SQ2', 'Microsoft SQ2'), 
        ('AMD RYZEN R5', 'AMD Ryzen 5'),
        ('AMD RYZEN R7', 'AMD Ryzen 7'), 
        ('AMD RYZEN R9', 'AMD Ryzen 9'),
        ('AMD FX', 'AMD FX Series'),
        ('AMD RYZEN AI MAX', 'AMD Ryzen AI MAX+ Series'),
        ('AMD RYZEN AI', 'AMD Ryzen AI Series'),
        ('MEDIATEK', 'MediaTek'),
        ('AMD RYZEN 9', 'AMD Ryzen 9'),
        ('AMD RYZEN 7', 'AMD Ryzen 7'),
        ('AMD RYZEN 5', 'AMD Ryzen 5'),
        ('AMD RYZEN 3', 'AMD Ryzen 3'),
        ('AMD A4', 'AMD A4 Series'),
        ('AMD A6', 'AMD A6 Series'),
        ('AMD A8', 'AMD A8 Series'),
        ('AMD A9', 'AMD A9 Series'),
        ('AMD A10', 'AMD A10 Series'),
        ('AMD DUAL CORE', 'AMD Dual Core'),
        ('AMD ATHLON', 'AMD Athlon Series'),
        ('SNAPDRAGON', 'Snapdragon Series'),
        ('APPLE M1', 'Apple M1'),
        ('APPLE M2', 'Apple M2'),
        ('APPLE M3', 'Apple M3'),
        ('INTEL XEON', 'Intel Xeon'),
        ('INTEL CORE I7', 'Intel Core i7'),
        ('INTEL CORE I5', 'Intel Core i5'),
        ('INTEL CORE I3', 'Intel Core i3'),
        ('INTEL CORE', 'Intel Core Series'),
        ('INTEL CELERON', 'Intel Celeron'),
        ('INTEL PENTIUM', 'Intel Pentium'),
        ('INTEL ATOM', 'Intel Atom'),
    ]
    
    for keyword, processor_name in vendor_keywords:
        if keyword in name_upper:
            return processor_name
    
    # Final fallback: Cari berbagai pattern yang mungkin terlewat dengan pengecekan RADEON
    final_patterns = [
        (r'\b(MEDIATEK\s+\w+)', lambda m: m.group(1)),
        (r'\b(FX[-]?\d{4}[A-Z]?)\b', lambda m: f"AMD {m.group(1)}"),
        (r'\b(R[579][-]\d{4}[A-Z]?)\b', lambda m: f"AMD Ryzen {m.group(1)}"),
        (r'\b(A[4689][-]?\d{4}[A-Z]?)\b', lambda m: f"AMD {m.group(1)}"),
        (r'\b(I[3579][-]\d{4,5}[A-Z]{1,2})\b', lambda m: f"Intel Core {m.group(1)}"),
        (r'\b(\d{4,5}[A-Z]{1,2})\b', lambda m: f"AMD {m.group(1)}" if 'AMD' in name_upper and not 'RADEON' in name_upper else None),
        (r'\b(RYZEN\s+[3579]\s+\d{3,4}[A-Z]{0,2})\b', lambda m: f"AMD {m.group(1)}"),
        (r'\b(CORE\s+[I3579]\s+\d{4,5}[A-Z]{0,2})\b', lambda m: f"Intel {m.group(1)}"),
        (r'\b(I[3579])\s+(\d{4,5}[A-Z]{1,2})\b', lambda m: f"Intel Core {m.group(1)}-{m.group(2)}"),
        (r'\b(SNAPDRAGON\s+\d{3})', lambda m: f"Snapdragon {m.group(1).replace('SNAPDRAGON ', '')}"),
        (r'\b(ULTRA\s+[579]\s+\d{3}[A-Z]{1,2})\b', lambda m: f"Intel Core {m.group(1)}"),
    ]
    
    for pattern, formatter in final_patterns:
        match = re.search(pattern, name_upper)
        if match:
            result = formatter(match)
            # Pastikan ini bukan bagian dari spesifikasi lain dan BUKAN RADEON GPU
            if result and not re.search(r'(RAM|GB|SSD|HDD|VGA|RADEON|VEGA)\s*' + re.escape(match.group(0)), name_upper):
                return result
    
    return 'Unknown Processor'


# ---- cell 9 ----
def standardize_processor(processor):
    """
    Standardisasi dan kelompokkan processor ke kategori yang lebih terstruktur
    """
    if pd.isna(processor) or processor == 'Unknown Processor':
        return 'Unknown Category'
        
    processor_upper = str(processor).upper()
    
    # 1. INTEL XEON SERIES
    if 'XEON' in processor_upper:
        return 'Intel Xeon'
    
    # 2. MICROSOFT SQ SERIES - PATTERN BARU (DITAMBAHKAN DI SINI)
    if 'MICROSOFT SQ' in processor_upper or ' SQ1' in processor_upper or ' SQ2' in processor_upper:
        return 'Qualcomm Snapdragon'
    
    # 3. AMD RYZEN AI MAX+ SERIES - PATTERN BARU (priority tertinggi)
    if 'RYZEN AI MAX+' in processor_upper or 'RYZEN AI MAX' in processor_upper:
        # Ryzen AI MAX+ 395 adalah flagship, setara dengan Ryzen 9
        if any(model in processor_upper for model in [' 395', ' MAX+ 395', ' MAX 395']):
            return 'AMD Ryzen 9'
        elif any(model in processor_upper for model in [' 390', ' MAX+ 390', ' MAX 390']):
            return 'AMD Ryzen 9'  # Juga high-end
        elif any(model in processor_upper for model in [' 385', ' MAX+ 385', ' MAX 385']):
            return 'AMD Ryzen 7'  # Mid-high end
        else:
            return 'AMD Ryzen 9'  # Default untuk AI MAX+ series
    
    # 4. AMD RYZEN AI SERIES
    if 'RYZEN AI' in processor_upper:
        if 'RYZEN AI 9' in processor_upper or any(model in processor_upper for model in [' AI 9', '365', '370', '375']):
            return 'AMD Ryzen 9'
        elif 'RYZEN AI 7' in processor_upper or any(model in processor_upper for model in [' AI 7', '350']):
            return 'AMD Ryzen 7'
        elif 'RYZEN AI 5' in processor_upper or any(model in processor_upper for model in [' AI 5', '340']):
            return 'AMD Ryzen 5'
        else:
            return 'AMD Ryzen Series'
    
    # 5. INTEL N-SERIES & LOW POWER
    if any(n_series in processor_upper for n_series in [
        ' N100', ' N150', ' N200', ' N300', ' N305', ' N355',
        ' N3350', ' N3450', ' N4000', ' N4020', ' N4120', ' N4500', 
        ' N5000', ' N5030', ' N5100', ' N5105', ' N6000', ' N6210',
        ' N6211', ' N6230', ' N6410', ' N6420'
    ]):
        return 'Intel N-Series'
    
    # 6. INTEL PENTIUM/CELERON BERDASARKAN MODEL
    pentium_models = ['6405', '4415', '4410', '5405', '4425', 'G6500', 'G6400', '7505']
    celeron_models = ['5205', '5305', 'N5100', 'N4500', 'N4020', 'N4000', 'N3350', 'N3450']
    
    for model in pentium_models:
        if model in processor_upper:
            return 'Intel Pentium'
    
    for model in celeron_models:
        if model in processor_upper:
            return 'Intel Celeron'
    
    # 7. INTEL CORE SERIES (termasuk Core Ultra)
    if 'INTEL CORE ULTRA' in processor_upper:
        return 'Intel Core Ultra'
    elif 'INTEL CORE' in processor_upper:
        if 'I9' in processor_upper:
            return 'Intel Core i9'
        elif 'I7' in processor_upper:
            return 'Intel Core i7' 
        elif 'I5' in processor_upper:
            return 'Intel Core i5'
        elif 'I3' in processor_upper:
            return 'Intel Core i3'
        elif any(n_series in processor_upper for n_series in ['-N100', '-N200', '-N300', '-N305', '-N355']):
            return 'Intel Core i3'
        else:
            return 'Intel Core Series'
    
    # 8. AMD RYZEN SERIES (termasuk yang hanya berupa angka)
    elif 'RYZEN' in processor_upper:
        # Fallback untuk Ryzen AI (seharusnya sudah ditangani di atas)
        if 'RYZEN AI' in processor_upper:
            if any(model in processor_upper for model in [' AI 9', '365', '370', '375', '395']):
                return 'AMD Ryzen 9'
            elif any(model in processor_upper for model in [' AI 7', '350', '385']):
                return 'AMD Ryzen 7'
            elif any(model in processor_upper for model in [' AI 5', '340']):
                return 'AMD Ryzen 5'
        
        # Standard Ryzen series - PERBAIKAN URUTAN DAN MODEL
        if 'RYZEN 9' in processor_upper or any(model in processor_upper for model in [' 6900', ' 6980', ' 7945', ' 7845', ' 8940', ' 8945', ' 9955']):
            return 'AMD Ryzen 9'
        elif 'RYZEN 7' in processor_upper or any(model in processor_upper for model in [' 5800', ' 5700', ' 6800', ' 7735', ' 8840', ' 7840', ' 7745', ' 8845H', ' 8845HS']):
            return 'AMD Ryzen 7'
        elif 'RYZEN 5' in processor_upper or any(model in processor_upper for model in [' 3500', ' 4500', ' 5500', ' 5600', ' 6600', ' 7520', ' 7530', ' 7535', ' 7640', ' 8645']):
            return 'AMD Ryzen 5'
        elif 'RYZEN 3' in processor_upper or any(model in processor_upper for model in [' 3200', ' 3250', ' 3300', ' 4300', ' 5300', ' 7320', ' 7330', ' 7425']):
            return 'AMD Ryzen 3'
        else:
            return 'AMD Ryzen Series'
    
    # 9. AMD PROCESSOR dengan format angka saja (3020E, 7120U, dll) - REVISI MENJADI ENTRY-LEVEL
    elif processor_upper.startswith('AMD ') and any(char.isdigit() for char in processor_upper):
        # Cek model Ryzen AI MAX+ (fallback)
        if any(model in processor_upper for model in [' 395', ' 390']):
            return 'AMD Ryzen 9'
        elif any(model in processor_upper for model in [' 385']):
            return 'AMD Ryzen 7'
        
        # Cek model Ryzen berdasarkan angka - PERBAIKAN: SEMUA MODEL 4-DIGIT TANPA RYZEN ADALAH ENTRY-LEVEL
        if any(model in processor_upper for model in [' 6900', ' 6980', ' 7945', ' 7845', ' 8940', ' 8945', ' 9955']):
            return 'AMD Ryzen 9'
        elif any(model in processor_upper for model in [' 5800', ' 5700', ' 6800', ' 7735', ' 8840', ' 7840', ' 7745', ' 8845H', ' 8845HS']):
            return 'AMD Ryzen 7'
        elif any(model in processor_upper for model in [' 3500', ' 4500', ' 5500', ' 5600', ' 6600', ' 7520', ' 7530', ' 7535', ' 7640', ' 8645']):
            return 'AMD Ryzen 5'
        elif any(model in processor_upper for model in [' 3200', ' 3250', ' 3300', ' 4300', ' 5300', ' 7320', ' 7330', ' 7425']):
            return 'AMD Ryzen 3'
        # SEMUA MODEL LAIN SEPERTI 3020E, 7120U, DLL ADALAH ENTRY-LEVEL
        else:
            return 'AMD Entry-Level'
    
    # 10. INTEL PROCESSOR 4-DIGIT (4305U, 6305U, 6405U, dll)
    if processor_upper.startswith('INTEL ') and re.search(r'\b\d{4}[A-Z]\b', processor_upper):
        model_match = re.search(r'\b(\d{4})[A-Z]\b', processor_upper)
        if model_match:
            model = model_match.group(1)
            if model in ['4305', '6305', '6405']:
                return 'Intel Pentium'
            elif model in ['5205', '5305']:
                return 'Intel Celeron'
            else:
                return 'Intel Other'
    
    # 11. INTEL PENTIUM/CELERON/ATOM (berdasarkan keyword)
    elif 'PENTIUM' in processor_upper:
        return 'Intel Pentium'
    elif 'CELERON' in processor_upper:
        return 'Intel Celeron'
    elif 'ATOM' in processor_upper:
        return 'Intel Atom'
    
    # 12. AMD ATHLON & DUAL CORE - REVISI: SEMUA ATHLON ADALAH ENTRY-LEVEL
    elif 'ATHLON' in processor_upper:
        return 'AMD Entry-Level'
    elif 'DUAL CORE' in processor_upper:
        return 'AMD Entry-Level'
    
    # 13. APPLE SILICON
    elif 'APPLE' in processor_upper or any(m_series in processor_upper for m_series in [' M1', ' M2', ' M3', ' M4']):
        return 'Apple Silicon'
    
    # 14. QUALCOMM SNAPDRAGON
    elif 'SNAPDRAGON' in processor_upper:
        return 'Qualcomm Snapdragon'
    
    # 15. MEDIATEK
    elif 'MEDIATEK' in processor_upper:
        return 'MediaTek'
    
    # 16. FALLBACK CATEGORIES
    elif 'INTEL' in processor_upper:
        return 'Intel Other'
    elif 'AMD' in processor_upper:
        return 'AMD Other'
    
    # 17. UNKNOWN
    else:
        return 'Unknown Category'


# ---- cell 10 ----
def extract_gpu(all_products):
    """
    Mengekstrak dan menstandardisasi nama GPU dari nama produk.
    Versi revisi - lebih akurat untuk Apple Silicon dan AMD Integrated Graphics.
    """
    name_upper = all_products.upper()
    
    # 1. APPLE SILICON GRAPHICS - PATTERN YANG LEBIH SPESIFIK (priority tertinggi)
    # Deteksi produk Apple dengan M series processor
    apple_m_patterns = [
        r'APPLE\s+M[1-4]\s*(?:PRO|MAX|ULTRA)?\s*(?:\d+-CORE\s*CPU)?\s*(?:\d+-CORE\s*GPU)',
        r'MACBOOK\s+(?:AIR|PRO)\s+M[1-4]',
        r'APPLE\s+M[1-4][^.]*(?:CPU|GPU)',
        r'MACBOOK[^.]*M[1-4]'
    ]
    
    # Cek apakah ini produk Apple dengan M series
    is_apple_m_product = False
    for pattern in apple_m_patterns:
        if re.search(pattern, name_upper):
            is_apple_m_product = True
            break
    
    # Juga cek keyword tambahan untuk memastikan ini produk Apple
    has_apple_keywords = any(keyword in name_upper for keyword in [
        'MACBOOK', 'IMAC', 'MAC MINI', 'MAC PRO', 'MAC STUDIO', 'APPLE M1', 'APPLE M2', 'APPLE M3', 'APPLE M4', 'MAC OS'
    ])
    
    if is_apple_m_product and has_apple_keywords:
        return "Apple Silicon Graphics"
    
    # 2. AMD INTEGRATED GRAPHICS - PATTERN BARU
    if 'AMD' in name_upper and ('INTEGRATED AMD GRAPHICS' in name_upper or 'INTEGRATED GRAPHICS' in name_upper):
        return "Integrated AMD Graphics"
    
    # Mapping pattern untuk berbagai tipe GPU dengan prioritas
    gpu_patterns = [
        # 3. AMD Radeon Pro Series (Pro 555X, Pro 560X, dll) - PATTERN BARU DIPINDAHKAN LEBIH TINGGI
        (r'RADEON\s+PRO\s+(\d{3,4}[A-Z]?)\b', 1,
         lambda m: f"Radeon Pro {m.group(1)}"),
        
        # 4. AMD Radeon 800M Series (890M, 880M, dll)
        (r'RADEON\s+(8[89]\dM)\b', 1,
         lambda m: f"Radeon {m.group(1)}"),
        
        # 5. AMD Radeon 700M Series (780M, 760M, 740M, dll)
        (r'RADEON\s+(7[4-8]\dM)\b', 1,
         lambda m: f"Radeon {m.group(1)}"),
        
        # 6. AMD Radeon 600M Series (680M, 660M, 610M, dll)
        (r'RADEON\s+(6[1-8]\dM)\b', 1,
         lambda m: f"Radeon {m.group(1)}"),
        
        # 7. AMD Radeon Vega series (Vega 7, Vega 8, Vega 10, dll)
        (r'(?:ATI\s)?RADEON\s+(VEGA\s?[2-9]|VEGA\s?10)\b', 1,
         lambda m: f"Radeon {m.group(1)}"),
        
        # 8. AMD Radeon R series (R5, R7, R8, R9) - PATTERN REVISI: HANYA AMBIL R5/R7/R8/R9
        (r'RADEON\s+(R[5-9])\s+[A-Z]\d+[A-Z]+\b', 1,
         lambda m: f"Radeon {m.group(1)}"),
        
        # 9. AMD Radeon R series basic (R5, R7, R8, R9)
        (r'RADEON\s+(R[5-9])\b', 1,
         lambda m: f"Radeon {m.group(1)}"),
        
        # 10. NVIDIA RTX 40 series (4050, 4060, 4070, 4080, 4090)
        (r'(RTX)\s*(\d{4})\b', 1,
         lambda m: f"{m.group(1)} {m.group(2)}"),
        
        # 11. NVIDIA RTX 30 series (3050, 3060, 3070, 3080, 3090)
        (r'(RTX)\s*(\d{4})\b', 1,
         lambda m: f"{m.group(1)} {m.group(2)}"),
        
        # 12. NVIDIA RTX 20 series (2050, 2060, 2070, 2080)
        (r'(RTX)\s*(\d{4})\b', 1,
         lambda m: f"{m.group(1)} {m.group(2)}"),
        
        # 13. NVIDIA GTX 16 series (1650, 1660)
        (r'(GTX)\s*(\d{4})\b', 1,
         lambda m: f"{m.group(1)} {m.group(2)}"),
        
        # 14. NVIDIA GTX 10 series (1050, 1060, 1070, 1080)
        (r'(GTX)\s*(\d{4})\b', 1,
         lambda m: f"{m.group(1)} {m.group(2)}"),
        
        # 15. NVIDIA GeForce M-series (920M, 940M, 970M, dll) - DIPINDAH KE BAWAH
        (r'(GEFORCE\s+)?(\d{3,4}[A-Z]?M)\b', 5,
         lambda m: f"GTX {m.group(2)}" if int(re.search(r'\d+', m.group(2)).group()) >= 1000 
         else f"GT{m.group(2)}"),
        
        # 16. NVIDIA Quadro T-series (T600, T500, T1000, T2000)
        (r'(QUADRO\s+)?(T[1-6]\d{2,3})\b', 2,
         lambda m: f"Quadro {m.group(2)}"),
        
        # 17. NVIDIA RTX A-series (A500, A1000, A2000, A3000, A4000, A5000)
        (r'(RTX\s+)?(A[1-5]\d{3})\b', 2,
         lambda m: f"RTX {m.group(2)}"),
        
        # 18. NVIDIA GeForce RTX/GTX dengan Ti
        (r'(RTX|GTX)\s*(\d{4})\s*(TI)', 2,
         lambda m: f"{m.group(1)} {m.group(2)} Ti"),
        
        # 19. NVIDIA GeForce MX series
        (r'(MX\s*(\d{3}))', 3,
         lambda m: f"MX {m.group(2)}"),
        
        # 20. NVIDIA GeForce GT series (tanpa X)
        (r'(GT\s*\d{3,4}[A-Z]?)', 3,
         lambda m: m.group(1).replace(' ', '')),
        
        # 21. NVIDIA Quadro P-series (P1000, P2000, P3200, P4200)
        (r'(QUADRO\s+)?(P[1-4]\d{3}[A-Z]?)', 3,
         lambda m: f"Quadro {m.group(2)}"),
        
        # 22. NVIDIA Quadro M-series (M2000M, M3000M, M2200M)
        (r'(QUADRO\s+)?(M[1-3]\d{3}[A-Z]?)', 3,
         lambda m: f"Quadro {m.group(2)}"),
        
        # 23. AMD Radeon RX series
        (r'(RX\s*(\d{4})\s*([M]?))', 3,
         lambda m: f"Radeon RX {m.group(2)}{m.group(3)}"),
        
        # 24. Intel Iris Xe Graphics - PRIORITY DITINGKATKAN
        (r'IRIS\s?XE', 1,
         lambda m: 'Intel Iris Xe Graphics'),
        
        # 25. Intel Arc Graphics - PATTERN BARU
        (r'INTEL\s+ARC', 1,
         lambda m: 'Intel Arc Graphics'),
        
        # 26. Intel UHD/HD Graphics dengan seri spesifik
        (r'INTEL\s+(UHD|HD)\s+GRAPHICS\s+(\d+)', 2,
         lambda m: f"Intel {m.group(1)} Graphics {m.group(2)}"),
        
        # 27. Intel UHD Graphics
        (r'INTEL\s+UHD', 2,
         lambda m: 'Intel UHD Graphics'),
        
        # 28. Intel HD Graphics
        (r'INTEL\s+HD', 2,
         lambda m: 'Intel HD Graphics'),
        
        # 29. Intel Graphics basic
        (r'VGA\s+INTEL', 2,
         lambda m: 'Intel Graphics'),
        
        # 30. Qualcomm Adreno GPU - PATTERN BARU
        (r'QUALCOMM\s+ADRENO', 2,
         lambda m: 'Adreno Graphics'),
        
        # 31. VGA NVIDIA dengan model spesifik
        (r'VGA\s+(?:NVIDIA|GEFORCE)[^,]*?(RTX|GTX|MX|GT|QUADRO)\s*([A-Z]?\d{3,4}[A-Z]?)', 3,
         lambda m: f"{m.group(1)} {m.group(2)}" if m.group(1) != 'QUADRO' else f"Quadro {m.group(2)}"),
        
        # 32. AMD Radeon series dengan model angka (fallback)
        (r'RADEON\s+(\d{3,4}M)\b', 3,
         lambda m: f"Radeon {m.group(1)}"),
        
        # 33. AMD Radeon Vega series (fallback)
        (r'(?:ATI\s)?RADEON\s+(VEGA\s?\d{1,2})', 3,
         lambda m: f"Radeon {m.group(1)}"),
    ]

    # Cari pattern dengan priority tertinggi (diurutkan berdasarkan priority)
    sorted_patterns = sorted(gpu_patterns, key=lambda x: x[1])
    for pattern, priority, formatter in sorted_patterns:
        match = re.search(pattern, name_upper)
        if match:
            result = formatter(match)
            if result:  # Skip None results
                return result
    
    # Fallback: Deteksi berdasarkan kata kunci VGA
    if 'VGA ' in name_upper:
        vga_match = re.search(r'VGA\s+([A-Z][A-Z0-9\s]+?)(?=,|\(|\)|RAM|SSD|HDD|LED|WIN|WINDOWS|READY)', name_upper)
        if vga_match:
            vga_name = vga_match.group(1).strip()
            if any(keyword in vga_name for keyword in ['NVIDIA', 'GEFORCE', 'QUADRO']):
                # Coba ekstrak model NVIDIA dari VGA description
                nvidia_patterns = [
                    r'(RTX|GTX)\s*(\d{4})',
                    r'(RTX|GTX)\s*(\d{4})\s*(TI)',
                    r'(MX\s*(\d{3}))',
                    r'(GT\s*\d{3,4}[A-Z]?)',
                    r'(\d{3,4}[A-Z]?M)\b',
                    r'(QUADRO\s+\w+)'
                ]
                for nv_pattern in nvidia_patterns:
                    nv_match = re.search(nv_pattern, vga_name)
                    if nv_match:
                        if 'QUADRO' in nv_match.group(0):
                            return nv_match.group(0)
                        elif 'RTX' in nv_pattern or 'GTX' in nv_pattern:
                            if 'TI' in nv_match.groups():
                                return f"{nv_match.group(1)} {nv_match.group(2)} Ti"
                            else:
                                return f"{nv_match.group(1)} {nv_match.group(2)}"
                        elif 'MX' in nv_pattern:
                            return f"MX {nv_match.group(2)}"
                        elif 'M' in nv_match.group(0) and nv_match.group(0)[0].isdigit():
                            model = nv_match.group(0)
                            return f"GT{model}" if int(re.search(r'\d+', model).group()) < 1000 else f"GTX {model}"
                        else:
                            return nv_match.group(0)
                return 'Integrated Graphics'
            elif 'INTEL' in vga_name:
                # Cek tipe Intel Graphics yang spesifik
                intel_patterns = [
                    r'IRIS\s?XE',
                    r'INTEL\s+ARC',
                    r'INTEL\s+(UHD|HD)\s+GRAPHICS\s+(\d+)',
                    r'INTEL\s+UHD',
                    r'INTEL\s+HD'
                ]
                for intel_pattern in intel_patterns:
                    intel_match = re.search(intel_pattern, vga_name)
                    if intel_match:
                        if 'IRIS XE' in intel_pattern:
                            return 'Intel Iris Xe Graphics'
                        elif 'ARC' in intel_pattern:
                            return 'Intel Arc Graphics'
                        elif 'GRAPHICS' in intel_pattern and intel_match.lastindex and intel_match.lastindex > 1:
                            return f"Intel {intel_match.group(1)} Graphics {intel_match.group(2)}"
                        elif 'UHD' in intel_pattern:
                            return 'Intel UHD Graphics'
                        elif 'HD' in intel_pattern:
                            return 'Intel HD Graphics'
                return 'Intel Graphics'
            elif any(keyword in vga_name for keyword in ['AMD', 'ATI', 'RADEON']):
                # Cek apakah ini AMD Radeon iGPU spesifik atau Radeon Pro
                amd_patterns = [
                    r'RADEON\s+PRO\s+(\d{3,4}[A-Z]?)',
                    r'RADEON\s+(8[89]\dM)',
                    r'RADEON\s+(7[4-8]\dM)',
                    r'RADEON\s+(6[1-8]\dM)',
                    r'RADEON\s+(VEGA\s?[2-9]|VEGA\s?10)',
                    r'RADEON\s+(\d{3,4}M)',
                    # Pattern untuk Radeon R series dalam VGA description
                    r'RADEON\s+(R[5-9])\s+[A-Z]\d+[A-Z]+\b',
                    r'RADEON\s+(R[5-9])\b'
                ]
                for amd_pattern in amd_patterns:
                    amd_match = re.search(amd_pattern, vga_name)
                    if amd_match:
                        if 'PRO' in amd_pattern:
                            return f"Radeon Pro {amd_match.group(1)}"
                        elif 'R' in amd_pattern and 'RADEON' in amd_pattern:
                            # Untuk R series, hanya kembalikan R5/R7/R8/R9 tanpa model detail
                            return f"Radeon {amd_match.group(1)}"
                        else:
                            return f"Radeon {amd_match.group(1)}"
                return 'AMD Radeon Graphics'
            elif 'QUALCOMM' in vga_name or 'ADRENO' in vga_name:
                return 'Adreno Graphics'
    
    # Fallback untuk GPU vendor lain
    vendor_patterns = [
        ('POWERVR', 'PowerVR Graphics'),
        ('MALI', 'Mali Graphics'),
        ('ADRENO', 'Adreno Graphics'),
        ('RADEON', 'AMD Radeon Graphics'),
        ('INTEL', 'Intel Graphics')
    ]
    
    for keyword, gpu_name in vendor_patterns:
        if keyword in name_upper:
            return gpu_name
    
    return 'Unknown Graphics'


# ---- cell 11 ----
def standardize_gpu(gpu_name):
    """
    Standardisasi dan kelompokkan GPU ke kategori yang lebih terstruktur
    """
    if pd.isna(gpu_name) or gpu_name == 'Integrated Graphics':
        return 'Integrated Graphics'
        
    gpu_upper = str(gpu_name).upper()
    
    # 1. INTEL INTEGRATED GRAPHICS - REVISI: SEMUA iGPU INTEL DIKELOMPOKKAN SEBAGAI INTEL INTEGRATED GRAPHICS
    if any(intel_igpu in gpu_upper for intel_igpu in [
        'INTEL GRAPHICS', 'INTEL UHD', 'INTEL HD', 'INTEL IRIS', 'INTEL ARC',
        'IRIS XE', 'IRIS PLUS', 'UHD GRAPHICS', 'HD GRAPHICS', 'ARC GRAPHICS'
    ]):
        return 'Intel Integrated Graphics'
    
    # 2. AMD INTEGRATED GRAPHICS
    if any(amd_igpu in gpu_upper for amd_igpu in [
        'AMD RADEON GRAPHICS', 'INTEGRATED AMD GRAPHICS',
        'VEGA 2', 'VEGA 3', 'VEGA 5', 'VEGA 6', 'VEGA 7', 'VEGA 8', 'VEGA 10',
        'RADEON 600M', 'RADEON 700M', 'RADEON 800M', '610M', '680M', '660M', '740M', '760M', 
        '780M', '840M', '860M', '880M', '890M', '920M', '940M', '970M', '980M'
    ]):
        return 'AMD Integrated Graphics'
    
    # 3. APPLE SILICON GRAPHICS
    if 'APPLE' in gpu_upper and 'GRAPHICS' in gpu_upper:
        return "Apple Silicon Graphics"
    
    # 4. AMD RADEON R SERIES DEDICATED - KATEGORI BARU (priority tinggi)
    if (gpu_upper.startswith('RADEON R') and 
        any(r_series in gpu_upper for r_series in ['R5', 'R7', 'R8', 'R9'])):
        return 'AMD Radeon Dedicated'
    
    # 5. AMD RADEON PRO WORKSTATION
    if (gpu_upper.startswith('RADEON PRO') or 
        any(radeon_pro in gpu_upper for radeon_pro in [
            'PRO 555X', 'PRO 5300M', 'PRO 560X', 'PRO WX', 'PRO W5000', 'PRO W6000', 'PRO W7000'
        ])):
        return 'AMD Radeon Pro Workstation'
    
    # 6. NVIDIA QUADRO WORKSTATION (REVISI - tambah RTX series workstation)
    if (gpu_upper.startswith('QUADRO') or gpu_upper.startswith('RTX A') or 
        any(quadro in gpu_upper for quadro in [
            'RTX 1000', 'RTX 2000', 'RTX 3000', 'RTX 4000', 'RTX 5000', 'RTX 3500'
        ])):
        return 'NVIDIA Quadro Workstation'
    
    # 7. NVIDIA GEFORCE ENTRY-LEVEL
    if gpu_upper.startswith('MX ') or any(entry in gpu_upper for entry in [
        'GT920', 'GT940', 'GTX 920', 'GTX 940'
    ]):
        return 'NVIDIA GeForce Entry-Level'
    
    # 8. NVIDIA GEFORCE MAINSTREAM
    if any(mainstream in gpu_upper for mainstream in [
        'GTX 1050', 'GTX 1060', 'GTX 1070', 'GTX 1080', 'GTX 1650', 'GTX 1660'
    ]):
        return 'NVIDIA GeForce Mainstream'
    
    # 9. NVIDIA GEFORCE PERFORMANCE
    if any(performance in gpu_upper for performance in [
        'RTX 2050', 'RTX 2060', 'RTX 2070', 'RTX 2080', 'RTX 3050', 'RTX 3060', 'RTX 3070', 'RTX 3080'
    ]):
        return 'NVIDIA GeForce Performance'
    
    # 10. NVIDIA GEFORCE HIGH-END
    if any(highend in gpu_upper for highend in [
        'RTX 4050', 'RTX 4060', 'RTX 4070', 'RTX 4080', 'RTX 4090',
        'RTX 5050', 'RTX 5060', 'RTX 5070', 'RTX 5080', 'RTX 5090'
    ]):
        return 'NVIDIA GeForce High-End'
    
    # 11. AMD RADEON RX DEDICATED (Consumer/Gaming)
    if gpu_upper.startswith('RADEON RX'):
        return 'AMD Radeon Dedicated'
    
    # 12. AMD RADEON DEDICATED (Fallback untuk Radeon lainnya)
    if gpu_upper.startswith('RADEON'):
        return 'AMD Radeon Dedicated'
    
    # 13. OTHER/MOBILE GPUs
    if any(other in gpu_upper for other in ['ADRENO', 'POWERVR', 'MALI']):
        return 'Other Mobile Graphics'
    
    # Fallback untuk NVIDIA GT/GTX/RTX series yang tidak tercakup
    if gpu_upper.startswith('GT') or gpu_upper.startswith('GTX') or gpu_upper.startswith('RTX'):
        # Coba klasifikasikan berdasarkan angka model
        model_match = re.search(r'(?:GTX?|RTX)\s*(\d{3,4})', gpu_upper)
        if model_match:
            model_num = int(model_match.group(1))
            if model_num < 1000:  # GT series
                return 'NVIDIA GeForce Entry-Level'
            elif model_num < 2000:  # GTX 10-series
                return 'NVIDIA GeForce Mainstream'
            elif model_num >= 2000 and model_num < 4000:  # GTX 16/20/30-series
                return 'NVIDIA GeForce Performance'
            else:  # RTX 40/50-series
                return 'NVIDIA GeForce High-End'
    
    return 'Other GPU'


# ---- cell 12 ----
def extract_ram(all_products):
    """
    Mengekstrak dan menstandardisasi ukuran RAM dari nama produk.
    Versi revisi - lebih akurat untuk format Apple dan frekuensi RAM.
    """
    name_upper = str(all_products).upper()
    
    # Pattern untuk mengekstrak RAM dengan berbagai format (priority tinggi)
    ram_patterns = [
        # Pattern 1: Format Apple dengan frekuensi - "8GB 2133MHz LPDDR3", "16GB 2400MHz DDR4"
        (r'(\d+)\s*GB\s*\d+[KM]?HZ\s*(?:LPDDR|DDR)[345]', 1),
        # Pattern 2: Format Apple dengan MHz - "8GB 2133MHz", "16GB 2400MHz"
        (r'(\d+)\s*GB\s*\d+[KM]?HZ', 1),
        # Pattern 3: "RAM 4GB", "RAM 8 GB", "RAM 16GB", dll - dengan kata kunci RAM
        (r'RAM\s*(\d+)\s*GB', 2),
        # Pattern 4: "Memori 4GB", "Memori 8 GB", "Memori 16GB", dll
        (r'MEMORI\s*(\d+)\s*GB', 2),
        # Pattern 5: "Memory Ram 8GB", "Memory 16GB", dll
        (r'MEMORY\s*(?:RAM)?\s*(\d+)\s*GB', 2),
        # Pattern 6: "2x16GB DDR4", "2x8GB DDR5", dll (RAM dengan multiplier)
        (r'(\d+)[X*]\s*(\d+)\s*GB\s*(?:DDR|RAM)', 2),
        # Pattern 7: "4GB DDR3L", "8GB DDR4", "16GB DDR5", dll - dengan DDR
        (r'(\d+)\s*GB\s*DDR[345]?[A-Z]?', 2),
        # Pattern 8: "DDR4 8GB", "DDR5 16GB", dll - HARUS dengan DDR
        (r'DDR[345]?[A-Z]?\s*(\d+)\s*GB', 2),
        # Pattern 9: "8GB RAM", "16GB RAM", dll - HARUS dengan kata RAM setelahnya
        (r'(\d+)\s*GB\s*RAM', 2),
        # Pattern 10: "8GB Memory", "16GB Memory", dll - HARUS dengan kata Memory setelahnya
        (r'(\d+)\s*GB\s*MEMORY', 2),
        # Pattern 11: Angka + GB yang diikuti oleh spesifikasi processor/storage
        (r'(\d+)\s*GB\s*(?:DDR|,|\s+[A-Z]|\s+SSD|\s+HDD|\s+INTEL|\s+AMD|\s+RYZEN|\s+CORE)', 2),
        # Pattern 12: Angka + GB di dalam kurung sebelum spesifikasi lain
        (r'\([^)]*?(\d+)\s*GB\s*[^)]*?\)', 2),
    ]
    
    # Cari pattern dengan priority tertinggi
    for pattern, priority in ram_patterns:
        match = re.search(pattern, name_upper)
        if match:
            # Handle pattern dengan multiplier (2x16GB)
            if len(match.groups()) == 2:
                multiplier = int(match.group(1))
                ram_size = int(match.group(2))
                total_ram = multiplier * ram_size
            else:
                total_ram = int(match.group(1))
            
            # Validasi ukuran RAM yang umum
            if total_ram in [2, 4, 8, 16, 32, 64, 128]:
                return f"{total_ram}GB"
            elif 1 <= total_ram <= 256:  # Fallback untuk ukuran tidak umum
                return f"{total_ram}GB"
    
    # Pattern fallback yang LEBIH KETAT (priority rendah)
    fallback_patterns = [
        # Hanya angka + GB yang berdiri sendiri atau sebelum kata tertentu
        (r'\b(\d+)\s*GB\b', lambda m: not any(storage in name_upper for storage in [
            'SSD', 'HDD', 'STORAGE', 'SSD'+m.group(1)+'GB', 'HDD'+m.group(1)+'GB',
            'SSD '+m.group(1)+'GB', 'HDD '+m.group(1)+'GB'
        ])),
    ]
    
    for pattern, condition in fallback_patterns:
        match = re.search(pattern, name_upper)
        if match and condition(match):
            ram_size = int(match.group(1))
            # Hanya terima ukuran RAM yang umum dalam fallback
            if ram_size in [2, 4, 8, 16, 32, 64, 128]:
                return f"{ram_size}GB"
    
    return 'Unknown RAM'


# ---- cell 13 ----
def extract_storage(all_products):
    """
    Mengekstrak dan menstandardisasi spesifikasi storage dari nama produk.
    Versi revisi - lebih akurat untuk SSHD dan format storage lainnya.
    """
    name_upper = str(all_products).upper()
    
    storage_specs = []
    
    # Pattern untuk mengekstrak storage dengan berbagai format
    storage_patterns = [
        # Pattern 1: SSHD + kapasitas (1TB SSHD)
        (r'(\d+)\s*(GB|TB)\s*SSHD', 'SSHD'),
        # Pattern 2: SSHD + kapasitas (SSHD 1TB)
        (r'SSHD\s*(\d+)\s*(GB|TB)', 'SSHD'),
        # Pattern 3: eMMC + kapasitas (eMMC 128GB, EMMC 32GB)
        (r'(?:EMMC|E?MMC)\s*(\d+)\s*(GB|TB)', 'eMMC'),
        # Pattern 4: SSD + kapasitas (SSD 256GB, SSD 512GB, SSD 1TB)
        (r'SSD\s*(\d+)\s*(GB|TB)', 'SSD'),
        # Pattern 5: HDD + kapasitas (HDD 1TB, HDD 2TB)  
        (r'HDD\s*(\d+)\s*(GB|TB)', 'HDD'),
        # Pattern 6: NVMe + kapasitas (NVMe 512GB, NVME 1TB)
        (r'NVME?\s*(\d+)\s*(GB|TB)', 'NVMe'),
        # Pattern 7: Storage + kapasitas (Storage 128GB, Storage 256GB)
        (r'STORAGE\s*(\d+)\s*(GB|TB)', 'Storage'),
        # Pattern 8: Kapasitas + SSD (256GB SSD, 512GB SSD, 1TB SSD)
        (r'(\d+)\s*(GB|TB)\s*SSD', 'SSD'),
        # Pattern 9: Kapasitas + HDD (1TB HDD, 2TB HDD)
        (r'(\d+)\s*(GB|TB)\s*HDD', 'HDD'),
        # Pattern 10: Kapasitas + eMMC (128GB eMMC, 32GB EMMC)
        (r'(\d+)\s*(GB|TB)\s*(?:EMMC|E?MMC)', 'eMMC'),
        # Pattern 11: Kapasitas + NVMe (512GB NVMe, 1TB NVME)
        (r'(\d+)\s*(GB|TB)\s*NVME?', 'NVMe'),
        # Pattern 12: Kapasitas + SSHD (1TB SSHD)
        (r'(\d+)\s*(GB|TB)\s*SSHD', 'SSHD'),
    ]
    
    # Cari semua pattern storage yang eksplisit
    for pattern, storage_type in storage_patterns:
        matches = re.finditer(pattern, name_upper)
        for match in matches:
            capacity = int(match.group(1))
            unit = match.group(2)
            
            # Convert to GB untuk konsistensi
            if unit == 'TB':
                capacity_gb = capacity * 1024
            else:
                capacity_gb = capacity
            
            storage_specs.append({
                'capacity': capacity,
                'unit': unit,
                'capacity_gb': capacity_gb,
                'type': storage_type,
                'pattern_used': pattern
            })
    
    # Jika tidak ada pattern eksplisit, cari pattern fallback yang lebih ketat
    if not storage_specs:
        fallback_patterns = [
            # Pattern 13: Kapasitas saja - hanya di konteks yang jelas storage
            (r'\b(\d+)\s*(GB|TB)\s*(?=STORAGE|SSD|HDD|EMMC|NVME|SSHD|$|,|\))', 'Storage'),
            # Pattern 14: Kapasitas setelah koma atau di akhir deskripsi
            (r',\s*(\d+)\s*(GB|TB)\s*(?:,|\)|$)', 'Storage'),
            # Pattern 15: Kapasitas dalam kurung yang jelas storage context
            (r'\(\s*(\d+)\s*(GB|TB)\s*[^)]*\)', 'Storage'),
        ]
        
        for pattern, storage_type in fallback_patterns:
            matches = re.finditer(pattern, name_upper)
            for match in matches:
                capacity = int(match.group(1))
                unit = match.group(2)
                
                if unit == 'TB':
                    capacity_gb = capacity * 1024
                else:
                    capacity_gb = capacity
                
                # Skip jika ini kemungkinan RAM (angka kecil + konteks RAM)
                if (capacity_gb <= 128 and 
                    any(ram_keyword in name_upper for ram_keyword in ['RAM', 'MEMORY', 'MEMORI', 'DDR']) and
                    not any(storage_keyword in name_upper for storage_keyword in ['STORAGE', 'SSD', 'HDD', 'EMMC', 'SSHD'])):
                    continue
                    
                storage_specs.append({
                    'capacity': capacity,
                    'unit': unit,
                    'capacity_gb': capacity_gb,
                    'type': storage_type,
                    'pattern_used': pattern
                })
    
    # Proses hasil ekstraksi - AMBIL HANYA SATU YANG UTAMA
    if not storage_specs:
        return 'Unknown Storage'
    
    # Pilih storage dengan kapasitas terbesar sebagai utama
    main_storage = max(storage_specs, key=lambda x: x['capacity_gb'])
    
    # Return hanya kapasitasnya saja
    return f"{main_storage['capacity']}{main_storage['unit']}"


# ---- cell 14 ----
def extract_display(all_products):
    # Pastikan input adalah string
    if not isinstance(all_products, str):
        return 'Unknown'
    
    # Normalisasi tanda kutip khusus - TAMBAHKAN LEBIH BANYAK VARIASI
    product_name = all_products.replace('″', '"').replace('′', '\'').replace('．', '.').replace('', '"').replace('', '"').replace('´', '\'').replace('`', '\'')

    candidates = []

    # 1. Pola dengan tanda kutip langsung dan resolusi
    quote_patterns = [
        # LED xx" dengan resolusi
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)["\'′´`]\s*(?:WQHD|QHD\+|QHD|2\.2K|2\.8K|3K|FHD|UHD|OLED)',
        # xx" dengan resolusi
        r'([1-3][0-9](?:[\.,]\d{1,2})?)["\'′´`]\s*(?:WQHD|QHD\+|QHD|2\.2K|2\.8K|3K|FHD|UHD|OLED)',
        # LED xx" saja
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)["\'′´`]',
        # xx" saja
        r'([1-3][0-9](?:[\.,]\d{1,2})?)["\'′´`]'
    ]

    # 2. Pola khusus untuk format baru (ditambahkan)
    new_patterns = [
        # LED xx 2.5K/2.8K WQXGA format
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:2\.5K|2\.8K)\s+(?:WQXGA|IPS|OLED)',
        # LED xx WQXGA format
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:WQXGA|2\.5K|2\.8K)',
        # xx 2.5K/2.8K format tanpa LED
        r'[\s,\(]([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:2\.5K|2\.8K)',
        # LED xx dengan refresh rate
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:\d{3}Hz)',
        # PATTERN BARU: LED xx 2K IPS Touchscreen (untuk kasus Advan)
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+2K\s+(?:IPS|OLED)\s*(?:Touchscreen)?',
        # PATTERN BARU: LED xx 2K Touchscreen  
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+2K\s+Touchscreen',
        # PATTERN BARU: LED xx 2K
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+2K',
        # PATTERN BARU: LED xx, (dengan koma setelah angka) - untuk kasus Acer TravelMate
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*,',
        # PATTERN BARU: LED xx ) (dengan kurung tutup setelah angka)
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*\)',
        # PATTERN BARU UNTUK KASUS "LED 16 WQUXGA OLED": LED xx WQUXGA
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+WQUXGA',
        # PATTERN BARU: LED xx WUXGA
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+WUXGA',
        # PATTERN BARU UNTUK KASUS "LED 14 4K WQUXGA OLED": LED xx 4K WQUXGA
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+WQUXGA',
        # PATTERN BARU: LED xx 4K WUXGA
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+WUXGA',
        # PATTERN BARU: LED xx 4K OLED
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+OLED',
    ]
    quote_patterns.extend(new_patterns)

    # Coba pola dengan tanda kutip dulu
    for priority, pattern in enumerate(quote_patterns):
        matches = list(re.finditer(pattern, product_name, re.IGNORECASE))
        if matches:
            for match in matches:
                size = match.group(1).replace(',', '.')
                try:
                    fsize = float(size)
                    if 10 <= fsize <= 39:
                        score = 100 - priority * 5
                        if any(ctx in product_name[match.start():match.end()+20].upper() 
                               for ctx in ['WQHD', 'QHD+', 'QHD', '2.2K', '2.8K', '3K', 'OLED', '120HZ', '144HZ', '240HZ', 'WQXGA', '2.5K', '2K', 'WQUXGA', 'WUXGA', '4K', 'TOUCHSCREEN']):
                            score += 10
                        if '.' in size:
                            score += 3
                        candidates.append((size, match.start(), score))
                except:
                    continue

    # 3. Pola tanpa tanda kutip tapi dengan resolusi/teknologi display
    display_patterns = [
        # LED xx.x dengan resolusi/teknologi
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*(?:WQHD|QHD\+|QHD|2\.2K|2\.8K|3K|FHD|UHD|IPS|OLED|WQXGA|2\.5K)',
        # LED xx dengan resolusi/teknologi
        r'LED\s*([1-3][0-9])\s*(?:WQHD|QHD\+|QHD|2\.2K|2\.8K|3K|FHD|UHD|IPS|OLED|WQXGA|2\.5K)',
        # LED xx.x diikuti HD atau konteks display lain
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*(?:HD|WUXGA|WQXGA|Touch)',
        # LED xx diikuti HD atau konteks display lain
        r'LED\s*([1-3][0-9])\s*(?:HD|WUXGA|WQXGA|Touch)',
        # xx.x-inch dengan konteks
        r'([1-3][0-9](?:[\.,]\d{1,2})?)-?inch\s*(?:Liquid|Retina|IPS|Touch|HD|FHD)',
        # xx-inch dengan konteks
        r'([1-3][0-9])-?inch\s*(?:Liquid|Retina|IPS|Touch|HD|FHD)',
        # Pola umum LED xx.x
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+Inch',
        # Pola baru: LED xx spasi konteks
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:\d{3}Hz|IPS|Touch|OLED)',
        # Pola baru: xx inch dengan HD/FHD
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+inch\s+(?:HD|FHD)',
        # Pola baru: LED xx inch dengan HD/FHD
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+inch\s+(?:HD|FHD)',
        # PATTERN BARU: LED xx 2K IPS (tanpa Touchscreen)
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+2K\s+IPS',
        # PATTERN BARU: LED xx IPS Touchscreen
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+IPS\s+Touchscreen',
        # PATTERN BARU: LED xx Touchscreen
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+Touchscreen',
        # PATTERN BARU: LED xx, (dengan koma) - untuk kasus Acer TravelMate
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*,',
        # PATTERN BARU: LED xx ) (dengan kurung tutup)
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*\)',
        # PATTERN BARU UNTUK KASUS "14 HD": xx HD" (tanpa LED di depan)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+HD["\'′´`]',
        # PATTERN BARU: xx HD (tanpa kutip)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+HD\s*[\),]',
        # PATTERN BARU UNTUK KASUS "LED 16 WQUXGA OLED": LED xx WQUXGA OLED
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+WQUXGA\s+OLED',
        # PATTERN BARU: LED xx WQUXGA
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+WQUXGA',
        # PATTERN BARU: LED xx WUXGA OLED
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+WUXGA\s+OLED',
        # PATTERN BARU: LED xx WUXGA
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+WUXGA',
        # PATTERN BARU UNTUK KASUS "LED 14 4K WQUXGA OLED": LED xx 4K WQUXGA OLED
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+WQUXGA\s+OLED',
        # PATTERN BARU: LED xx 4K WQUXGA
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+WQUXGA',
        # PATTERN BARU: LED xx 4K OLED Touchscreen
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+OLED\s+Touchscreen',
        # PATTERN BARU: LED xx 4K OLED
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+OLED',
        # PATTERN BARU: LED xx 4K Touchscreen
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+Touchscreen',
        # PATTERN BARU: LED xx 4K
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K',
        # PATTERN BARU UNTUK KASUS "17.3 FHD 144Hz": xx.x FHD dengan refresh rate
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:FHD|QHD\+|QHD)\s+(?:\d{3}Hz)',
        # PATTERN BARU: xx.x FHD/QHD+ saja
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:FHD|QHD\+|QHD)',
        # PATTERN BARU: xx.x dengan refresh rate saja
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:\d{3}Hz)',
        # PATTERN BARU UNTUK KASUS "TRANSCEND 14 OLED": Model xx OLED
        r'(?:TRANSCEND|OMEN|YOGA|THINKPAD|IDEAPAD|SURFACE|MACBOOK)\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+OLED',
        # PATTERN BARU: Model xx teknologi display
        r'(?:TRANSCEND|OMEN|YOGA|THINKPAD|IDEAPAD|SURFACE|MACBOOK)\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:IPS|Touch|Touchscreen)',
        # PATTERN BARU: xx.xFHD (tanpa spasi)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)FHD',
        # PATTERN BARU: xxFHD (tanpa spasi dan desimal)
        r'([1-3][0-9])FHD',
        # PATTERN BARU: xx.xOLED (tanpa spasi)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)OLED',
        # PATTERN BARU: xxOLED (tanpa spasi dan desimal)
        r'([1-3][0-9])OLED',
    ]

    for priority, pattern in enumerate(display_patterns):
        matches = list(re.finditer(pattern, product_name, re.IGNORECASE))
        if matches:
            for match in matches:
                size = match.group(1).replace(',', '.')
                try:
                    fsize = float(size)
                    if 10 <= fsize <= 39:
                        score = 80 - priority * 5
                        if any(ctx in product_name[match.start():match.end()+20].upper() 
                               for ctx in ['WQHD', 'QHD+', 'QHD', '2.2K', '2.8K', '3K', 'IPS', 'OLED', 'WQXGA', '2.5K', '2K', 'TOUCHSCREEN', 'HD', 'WQUXGA', 'WUXGA', '4K', 'FHD', '144HZ', '240HZ']):
                            score += 8
                        if '.' in size:
                            score += 3
                        # Tambah skor khusus untuk pola model produk + ukuran
                        if any(model in product_name[max(0, match.start()-20):match.start()].upper() 
                               for model in ['TRANSCEND', 'OMEN', 'YOGA', 'THINKPAD', 'IDEAPAD', 'SURFACE', 'MACBOOK']):
                            score += 10
                        candidates.append((size, match.start(), score))
                except:
                    continue

    # 4. Pola fallback untuk kasus edge
    fallback_patterns = [
        r'([1-3][0-9](?:[\.,]\d{1,2})?)-inch',
        r'LCD\s*([1-3][0-9](?:[\.,]\d{1,2})?)',
        r'Display\s*([1-3][0-9](?:[\.,]\d{1,2})?)',
        r'[\s,\(]([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:WQXGA|2\.5K|2\.8K)',
        r'Vga[^,]+LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)',
        # Pola baru: untuk kasus spesifik
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:HD|FHD)',
        # PATTERN BARU: LED xx IPS (sederhana)
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+IPS',
        # PATTERN BARU: LED xx 2K (sederhana)
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+2K',
        # PATTERN BARU: LED xx, (dengan koma) - fallback
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*,',
        # PATTERN BARU: LED xx ) (dengan kurung tutup) - fallback
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*\)',
        # PATTERN BARU: LED xx . (dengan titik setelah angka)
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s*\.',
        # PATTERN BARU UNTUK KASUS "17.3 inch UHD 4K": xx.x inch dengan resolusi UHD/4K
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+inch\s+(?:UHD|4K|FHD|HD)',
        # PATTERN BARU: xx.x inch dengan teknologi display
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+inch\s+(?:IPS|OLED|Touch)',
        # PATTERN BARU: xx.x inch saja (tanpa konteks tambahan)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+inch',
        # PATTERN BARU: , xx.x inch (dengan koma di depan)
        r',\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+inch',
        # PATTERN BARU UNTUK KASUS "14 HD": , xx HD (dengan koma di depan dan tanpa kutip)
        r',\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+HD',
        # PATTERN BARU: ) xx HD (dengan kurung tutup di depan)
        r'\)\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+HD',
        # PATTERN BARU: Graphics, xx HD (konteks setelah graphics)
        r'Graphics[,\s]+([1-3][0-9](?:[\.,]\d{1,2})?)\s+HD',
        # PATTERN BARU UNTUK KASUS "LED 16 WQUXGA OLED": LED xx dengan standar display tinggi
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:WQUXGA|WUXGA)',
        # PATTERN BARU: xx WQUXGA/WUXGA (tanpa LED)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:WQUXGA|WUXGA)',
        # PATTERN BARU UNTUK KASUS "LED 14 4K WQUXGA OLED": LED xx dengan kombinasi 4K dan teknologi lain
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+4K\s+(?:WQUXGA|WUXGA|OLED|Touchscreen)',
        # PATTERN BARU: LED xx dengan kombinasi teknologi display
        r'LED\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:4K|OLED|Touchscreen)',
        # PATTERN BARU UNTUK KASUS "17.3 FHD 144Hz": xx.x dengan resolusi dan refresh rate (tanpa LED)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:FHD|QHD\+|QHD|UHD)\s+(?:\d{3}Hz)',
        # PATTERN BARU: xx.x dengan resolusi saja (tanpa LED)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:FHD|QHD\+|QHD|UHD)',
        # PATTERN BARU: xx.x dengan refresh rate saja (tanpa LED)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:\d{3}Hz)',
        # PATTERN BARU: , xx.x FHD/QHD (dengan koma di depan)
        r',\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:FHD|QHD\+|QHD)',
        # PATTERN BARU UNTUK KASUS "TRANSCEND 14 OLED": Model produk dengan ukuran dan teknologi
        r'(?:TRANSCEND|OMEN|YOGA|THINKPAD|IDEAPAD|SURFACE|MACBOOK)\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+(?:OLED|IPS|Touchscreen)',
        # PATTERN BARU: Model produk dengan ukuran saja
        r'(?:TRANSCEND|OMEN|YOGA|THINKPAD|IDEAPAD|SURFACE|MACBOOK)\s*([1-3][0-9](?:[\.,]\d{1,2})?)\s+[A-Z]',
        # PATTERN BARU: xx.xFHD (tanpa spasi) - fallback
        r'([1-3][0-9](?:[\.,]\d{1,2})?)FHD',
        # PATTERN BARU: xxFHD (tanpa spasi) - fallback
        r'([1-3][0-9])FHD',
        # PATTERN BARU: xx.xOLED (tanpa spasi) - fallback
        r'([1-3][0-9](?:[\.,]\d{1,2})?)OLED',
        # PATTERN BARU: xxOLED (tanpa spasi) - fallback
        r'([1-3][0-9])OLED',
        # PATTERN BARU: xx.xIPS (tanpa spasi)
        r'([1-3][0-9](?:[\.,]\d{1,2})?)IPS',
        # PATTERN BARU: xxIPS (tanpa spasi)
        r'([1-3][0-9])IPS',
    ]

    for pattern in fallback_patterns:
        matches = list(re.finditer(pattern, product_name, re.IGNORECASE))
        if matches:
            for match in matches:
                size = match.group(1).replace(',', '.')
                try:
                    fsize = float(size)
                    if 10 <= fsize <= 39:
                        score = 50
                        if '.' in size:
                            score += 3
                        # Tambah skor untuk konteks yang kuat
                        context_text = product_name[match.start():match.end()+20].upper()
                        if any(ctx in context_text for ctx in ['WQXGA', '2.5K', '2.8K', 'IPS', 'OLED', 'HD', 'FHD', '2K', 'TOUCHSCREEN', 'UHD', '4K', 'WQUXGA', 'WUXGA', 'QHD+', 'QHD', '144HZ', '240HZ']):
                            score += 5
                        # Tambah skor lebih tinggi untuk konteks resolusi yang jelas
                        if any(ctx in context_text for ctx in ['UHD', '4K', 'FHD', 'HD', 'WQUXGA', 'WUXGA', 'OLED', 'TOUCHSCREEN', 'QHD+', 'QHD']):
                            score += 3
                        # Tambah skor khusus untuk konteks refresh rate
                        if any(ctx in context_text for ctx in ['144HZ', '240HZ', '120HZ']):
                            score += 4
                        # Tambah skor khusus untuk pola model produk
                        if any(model in product_name[max(0, match.start()-20):match.start()].upper() 
                               for model in ['TRANSCEND', 'OMEN', 'YOGA', 'THINKPAD', 'IDEAPAD', 'SURFACE', 'MACBOOK']):
                            score += 8
                        # Tambah skor khusus untuk konteks "Graphics" yang diikuti HD
                        if 'GRAPHICS' in product_name[max(0, match.start()-30):match.start()].upper():
                            score += 5
                        candidates.append((size, match.start(), score))
                except:
                    continue

    if candidates:
        # Pilih kandidat dengan skor tertinggi, jika skor sama pilih yang memiliki desimal
        # Jika masih sama, pilih yang paling awal di string
        best_candidate = max(candidates, key=lambda x: (x[2], '.' in x[0], -x[1]))
        size = best_candidate[0]
        if size.endswith('.0'):
            size = size[:-2]
        return f'{size}"'

    return 'Unknown'


# ---- cell 15 ----
# Menjalankan fungsi ekstraksi dan standardisasi yang sudah didefinisikan

brand_list = get_brands()
df['Brand'] = df['Product_Name'].apply(lambda x: extract_brand(x, brand_list))
df['Processor_Detail'] = df['Product_Name'].apply(extract_processor)
df['Processor_Category'] = df['Processor_Detail'].apply(standardize_processor)
df['GPU'] = df['Product_Name'].apply(extract_gpu)
df['GPU_Category'] = df['GPU'].apply(standardize_gpu)
df['RAM'] = df['Product_Name'].apply(extract_ram)
df['Storage'] = df['Product_Name'].apply(extract_storage)
df['Display'] = df['Product_Name'].apply(extract_display)



# ---- cell 16 ----
# Menampilkan unique value dari kolom Display
df['GPU_Category'].unique()


# ---- cell 17 ----
# Membuat variable untuk menyimpan salah satu unique value pada GPU_Category
gpu_category_example = 'Other GPU'

# Menampilkan jumlah produk yang memiliki GPU_Category sesuai dengan variable gpu_category_example
gpu_products = df[df['GPU_Category'] == gpu_category_example]
print(f"Total produk dengan GPU_Category {gpu_category_example}:", len(gpu_products))
print(f"\nContoh produk dengan GPU_Category {gpu_category_example}:")
gpu_products[['Product_Name', 'GPU', 'GPU_Category']]

# # Membuat variable untuk menyimpan salah satu unique value pada Processor_Category
# processor_category_example = 'AMD Ryzen 7'

# # Menampilkan jumlah produk yang memiliki Processor_Category sesuai dengan variable processor_category_example
# category_products = df[df['Processor_Category'] == processor_category_example]
# print(f"Total produk dengan Processor_Category {processor_category_example}:", len(category_products))
# print(f"\nContoh produk dengan Processor_Category {processor_category_example}:")
# category_products[['Product_Name', 'Processor_Detail', 'Processor_Category']]

# # Membuat variable untuk menyimpan salah satu unique value pada Processor_Detail
# processor_example = 'AMD Ryzen 9 5980HX'

# # Menampilkan jumlah produk yang memiliki Processor_Detail sesuai dengan variable processor_example
# processor_products = df[df['Processor_Detail'] == processor_example]
# print(f"Total produk dengan Processor_Detail {processor_example}:", len(processor_products))
# print(f"\nContoh produk dengan Processor_Detail {processor_example}:")
# processor_products[['Product_Name', 'Processor_Detail']]

# Membuat variable untuk menyimpan salah satu unique value pada Display
# display_example = '14.4"'

# Menampilkan jumlah produk yang memiliki Display sesuai dengan variable display_example
# failed_products = df[df['Display'] == display_example]
# print(f"Total produk dengan Display {display_example}:", len(failed_products))
# print(f"\nContoh produk dengan Display {display_example}:")
# failed_products[['Product_Name', 'Display']]



# Membuat variable untuk mnyimpan salah satu unique value pada Brand
# brand_example = 'Zyrex'

# # Menampilkan jumlah produk yang memiliki Brand sesuai dengan variable brand_example
# brand_products = df[df['Brand'] == brand_example]
# print(f"Total produk dengan Brand {brand_example}:", len(brand_products))
# print(f"\nContoh produk dengan Brand {brand_example}:")
# brand_products[['Product_Name', 'Brand']]


# ---- cell 18 ----
# Menjalankan semua fungsi yang sudah di buat
# df['Product_Name'] = df[]
df.head()


