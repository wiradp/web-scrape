"""ETL module: cleaning and feature extraction for scraped laptop data.
Input: product_raw(dari database)
Output: product_enriched (ke database)
Provides functions to normalize price, extract RAM/storage/display, and canonicalize brand.
"""
import sqlite3
import re
import logging
import os
import pandas as pd
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler

# === Konfigurasi logging profesional dengan Rotating File Handler ===
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# File log utama (tidak perlu pakai timestamp lagi karena sudah rotasi otomatis)
log_file = os.path.join(LOG_DIR, "etl.log")

# Format log
log_formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")

# Handler untuk file log dengan rotasi otomatis
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=5_000_000,   # 5 MB sebelum rotasi
    backupCount=3,        # simpan hingga 3 versi lama (etl.log.1, etl.log.2, dst)
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Handler tambahan agar log tampil di terminal juga
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Buat logger utama
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def get_brands():
    """
    Menyediakan daftar merek laptop populer untuk ekstraksi fitur.
    """
    return [
        'Acer', 'Apple', 'Asus', 'Dell', 'HP', 'Lenovo', 'MSI', 'Samsung', 'Toshiba', 
        'Microsoft', 'Sony', 'ADVAN', 'Zyrex', 'Axioo', 'Advan', 'Xiaomi', 'Avita', 'Tecno', 'Huawei',
        'Infinix', 'Jumper', 'SPC'
    ]

def extract_brand(product_name, brand_list):
    """
    Mengekstrak merek dari nama produk berdasarkan daftar merek yang diberikan.
    """
    # Memastikan product_name adalah string
    if not isinstance(product_name, str):
        return 'Other'
    
    # Normalisasi teks untuk pencarian yang lebih baik
    product_text = product_name.strip()
    
     # Pengecekan khusus untuk model Lenovo Legion
    if re.search(r'\bLegion\s*\d', product_text, re.IGNORECASE):
        return 'Lenovo'

    for brand in brand_list:
        if re.search(r'\b' + re.escape(brand) + r'\b', product_text, re.IGNORECASE):
            return brand
    return 'Other'

def extract_series(product_name: str) -> str:
    """
    Extracts laptop series from product_name (Final v15 - Auto Enhanced from Suggestions)
    """
    
    if not isinstance(product_name, str) or product_name.strip() == "":
        return "Unknown"

    name_lower = product_name.lower()
    name_norm = re.sub(r"[\-_/]+", " ", name_lower)

    # === Deteksi brand (mendeteksi brand yang muncul paling awal dalam string) ===
    brands = ["advan", "acer", "asus", "apple", "avita", "axioo", "dell", "hp",
              "huawei", "infinix", "lenovo", "msi", "microsoft", "samsung",
              "spc", "tecno", "toshiba", "xiaomi", "zyrex", "jumper"]
    
    first_match_pos = float('inf')
    detected_brand = None
    for b in brands:
        pos = name_lower.find(b)
        if pos != -1 and pos < first_match_pos:
            first_match_pos = pos
            detected_brand = b

    # === Jika brand tidak ditemukan, cek apakah mengandung kata kunci lenovo YANG EKSKLUSIF ===
    if not detected_brand:
        # Cek apakah mengandung kata kunci lenovo
        lenovo_keywords = ["legion", "thinkpad", "thinkbook", "yoga", "ideapad", "flex", "v series", "v14", "v15", "loq"]
        found_lenovo_kw = None
        for kw in lenovo_keywords:
            if kw in name_lower:
                found_lenovo_kw = kw
                break
        
        if found_lenovo_kw:
            # Cek apakah mengandung brand lain (selain lenovo_keywords)
            found_other_brand = False
            for b in brands:
                if b != "lenovo" and b in name_lower:
                    found_other_brand = True
                    break

            if not found_other_brand:
                detected_brand = "lenovo"

    if not detected_brand:
        return "Unknown"

    # === ASUS Handling ===
    if detected_brand == "asus":
        # --- PRIORITY 1: Chromebook ---
        if "chromebook" in name_lower:
            return "Chromebook"

        # --- PRIORITY 2: Zenbook ---
        if "zenbook" in name_lower:
            return "Zenbook"

        # --- PRIORITY 3: Asus Gaming ---
        if "asus gaming" in name_lower:
            return "Asus Gaming"

        # --- PRIORITY 4: Vivobook S (dengan model kode khusus) ---
        if (
            "vivobook s" in name_lower
            or re.search(r"\bs\d{3}|um\d{3}", name_lower)
            or re.search(r"k413f[aeq]|k413eq", name_lower)  # Tambahkan k413eq
        ):
            return "Vivobook S"

        # --- PRIORITY 5: Advantage Edition ---
        if "advantage edition" in name_lower:
            if "tuf" in name_lower or re.search(r"fa617", name_lower):
                return "TUF Gaming"
            if "rog" in name_lower or re.search(r"g513qy", name_lower):
                return "ROG Strix"
        
        # --- PRIORITY 6: ROG Strix ---
        if (
            re.search(r"\brog\b", name_lower)
            or "zephyrus" in name_lower
            or re.search(r"\bg5\d{2}|g7\d{2}|gx\d{3}|gz\d{3}", name_lower)
        ):
            return "ROG Strix"

        # --- PRIORITY 7: TUF Gaming ---
        if (
            re.search(r"\btuf\b", name_lower)
            or re.search(r"\btu\b", name_lower)
            or re.search(r"fx\d{3}|fa\d{3}|fx6\d{2}|fa6\d{2}", name_lower)
        ):
            return "TUF Gaming"

        # --- PRIORITY 8: ProArt Studiobook ---
        if "creator" in name_lower or "proart" in name_lower or "pz" in name_lower:
            return "ProArt Studiobook"

        # --- PRIORITY 9: ExpertBook P & B ---
        if re.search(r"\bp1\d{3}|expertbook p", name_lower):
            return "ExpertBook P"
        if re.search(r"\bbu\d{3}|b9|expertbook b", name_lower):
            return "ExpertBook B"

        # --- PRIORITY 10: Pro Series ---
        if re.search(r"asus pro|pro y\d{3}|pro p\d{3}", name_lower):
            return "Pro Series"

        # --- PRIORITY 11: Vivobook Pro, Go, Flip ---
        if "vivobook pro" in name_lower or re.search(r"\bv\d{4}", name_lower):
            return "Vivobook Pro"
        if "vivobook go" in name_lower or re.search(r"\bl\d{3,4}|e\d{3,4}", name_lower):
            return "Vivobook Go"
        if "vivobook flip" in name_lower or re.search(r"\btp\d{3}", name_lower):
            return "Vivobook Flip"
        if "vivobook" in name_lower:
            return "Vivobook"

        # --- PRIORITY 12: A-Series, X Series, M-Series, E-Series, BR Series ---
        if re.search(r"\ba\d{3,4}", name_lower):
            return "Vivobook (A-Series)"
        if re.search(r"\bx\d{3,4}", name_lower):
            return "X Series"
        if re.search(r"\bm\d{3,4}", name_lower):
            return "Vivobook (M-Series)"
        if re.search(r"\be\d{3,4}", name_lower):
            return "Vivobook (E-Series)"
        if re.search(r"\bbr\d{3}", name_lower):
            return "BR Series"

        # --- ADVANTAGE EDITION FIXES ---
        if "advantage edition" in name_lower:
            if re.search(r"fa617", name_lower) or "a16" in name_lower:
                return "TUF Gaming"
            if re.search(r"g513qy", name_lower) or "g15" in name_lower:
                return "ROG Strix"

        # --- NEW: Specific model code detection ---
        if re.search(r"fa617", name_lower):
            return "TUF Gaming"
        if re.search(r"g513qy", name_lower):
            return "ROG Strix"

        # --- EXPERTBOOK & PROART ---
        if "expertbook" in name_lower:
            return "ExpertBook"
        if "proart" in name_lower:
            return "ProArt Studiobook"

        # --- AUTO-ADDED (SAFE PATCH) ---
        if re.search(r"advantage|fa617ns|r7x2j6s|r7x2j6t|r7x2c6t", name_lower):
            return "TUF Gaming"
        if re.search(r"g513qy|advantage edition", name_lower):
            return "ROG Strix"

        return "Unknown"

    # === Acer ===
    elif detected_brand == "acer":
        if "aspire" in name_lower: return "Aspire"
        if "swift" in name_lower: return "Swift"
        if "nitro" in name_lower: return "Nitro"
        if "predator" in name_lower: return "Predator"
        if "spin" in name_lower: return "Spin"
        if "concept" in name_lower: return "Concept"
        if "switch" in name_lower: return "Switch"
        if "travelmate" in name_lower: return "TravelMate"
        if "one" in name_lower: return "One"
        if "mate" in name_lower: return "Mate"
        if "chromebook" in name_lower: return "Chromebook"
        return "Unknown"

    # === Lenovo (Revisi Final - Logika Jelas & Efektif) ===
    elif detected_brand == "lenovo":
        # 1. Normalisasi nama
        raw = product_name
        name_lower = raw.lower()
        name_clean = re.sub(r'[_/\\\(\)\[\]\.,:"]', ' ', name_lower)
        name_clean = re.sub(r'[^a-z0-9\s\-]', ' ', name_clean)
        name_clean = re.sub(r'\s+', ' ', name_clean).strip()

        # 2. Daftar prioritas tinggi: Seri yang paling spesifik dulu
        priority_patterns = [
            # Yoga Pro
            (r'\byoga\s+pro\b', "Yoga Pro"),
            # Yoga
            (r'\byoga\b', "Yoga"),
            # Legion Pro
            (r'\blegion\s+pro\b', "Legion Pro"),
            # Legion Slim
            (r'\blegion\s+slim\b', "Legion Slim"),
            # Legion
            (r'\blegion\b', "Legion"),  # <-- Ini harus cocok
            # ThinkBook
            (r'\bthinkbook\b', "ThinkBook"),
            # ThinkPad
            (r'\bthinkpad\b', "ThinkPad"),
            # IdeaPad Pro
            (r'\bideapad\s+pro\b', "IdeaPad Pro"),
            # IdeaPad 5 2in1
            (r'\bideapad\s+5\s+2in1\b', "IdeaPad Slim"),  # Diasumsikan Slim karena "5 2in1"
            # IdeaPad D330 (series khusus)
            (r'\bideapad\s+d330\b', "IdeaPad"),
            # IdeaPad Slim 5, 3, 7, 1, dll (versi fleksibel)
            (r'\bideapad\s+slim\s+5\b', "IdeaPad Slim"),
            (r'\bideapad\s+slim\s+3\b', "IdeaPad Slim"),
            (r'\bideapad\s+slim\s+7\b', "IdeaPad Slim"),
            (r'\bideapad\s+slim\s+1\b', "IdeaPad Slim"),
            # IdeaPad Slim generik (ini untuk kasus seperti "ideapad slim 1 11 05id")
            (r'\bideapad\s+slim\s+\d', "IdeaPad Slim"),
            # IdeaPad Slim generik (fallback setelah spesifik)
            (r'\bideapad\s+slim\b', "IdeaPad Slim"),
            # IdeaPad Slim Xi (misal: slim 3i, slim 5i)
            (r'\bideapad\s+slim\s+\d+i\b', "IdeaPad Slim"),
            # Slim 1, 3, 5, 7 (tanpa "ideapad" di depan)
            (r'\bslim\s+1\b', "IdeaPad Slim"),
            (r'\bslim\s+3\b', "IdeaPad Slim"),
            (r'\bslim\s+5\b', "IdeaPad Slim"),
            (r'\bslim\s+7\b', "IdeaPad Slim"),
            # Slim Xi (misal: slim 3i, slim 5i)
            (r'\bslim\s+\d+i\b', "IdeaPad Slim"),
            # IdeaPad Xi (misal: IP 5i, IP 3i)
            (r'\bip\s+\d+i\b', "IdeaPad"),
            # IdeaPad Flex (baru - untuk "Flex 5", "Flex 7", dll)
            (r'\bflex\s+5\b', "IdeaPad Flex"),
            (r'\bflex\s+7\b', "IdeaPad Flex"),
            # IdeaPad 1, 3 (tanpa "slim")
            (r'\bideapad\s+1\b', "IdeaPad"),
            (r'\bideapad\s+3\b', "IdeaPad"),
            # IdeaPad Flex (fallback umum)
            (r'\bideapad\s+flex\b', "IdeaPad Flex"),
            # IdeaPad
            (r'\bideapad\b', "IdeaPad"),
            # LOQ
            (r'\bloq\b', "LOQ"),
            # Chromebook
            (r'\bchromebook\b', "Chromebook"),
            # V Series (baru)
            (r'\bv14\s+g2\b', "V Series"),
            (r'\bv15\s+g2\b', "V Series"),
            (r'\bv16\s+g2\b', "V Series"),
            # V Series (fallback untuk v14, v15, v16, dll)
            (r'\bv\d{2}\b', "V Series"),
            # IdeaPad (fallback umum untuk model seperti v14-01id, d330, dsb)
            (r'\b\d{2,}[a-z]{2,}\d+\b', "IdeaPad"),
        ]

        for pattern, series in priority_patterns:
            if re.search(pattern, name_clean, re.IGNORECASE):
                return series

        # 3. Jika tidak ada yang cocok, kembalikan "Unknown"
        return "Unknown"
        
    # === HP ===
    elif detected_brand == "hp":
        # Chromebook Series - High Priority
        if "chromebook" in name_lower: return "Chromebook"
        
        # Premium & Business Series
        if "elite dragonfly" in name_lower: return "Elite Series"
        if "elite folio" in name_lower: return "Elite Series"
        if "dragonfly folio" in name_lower: return "Elite Series"
        if "elitebook" in name_lower: return "EliteBook"
        if "probook" in name_lower: return "ProBook"
        if "zbook" in name_lower: return "ZBook"
        
        # Gaming Series
        if "omen" in name_lower: return "OMEN"
        if "victus" in name_lower: return "Victus"
        if "pav gaming" in name_lower or re.search(r"pav.*gaming", name_lower): return "Pavilion Gaming"
        
        # Consumer Premium Series
        if "spectre" in name_lower: return "Spectre"
        if "envy" in name_lower: return "Envy"
        
        # Mainstream Consumer Series
        if "pavilion" in name_lower: return "Pavilion"
        
        # HP Essential Series (200 Series) - Business Entry Level
        if re.search(r"\b(?:240r|250|255)\s+g[0-9]", name_lower): return "HP 200 Series"
        if "240r g9" in name_lower: return "HP 200 Series"
        if "250 g8" in name_lower: return "HP 200 Series"
        if "255 g8" in name_lower: return "HP 200 Series"
        
        # HP Laptop Series (Mainstream) - Enhanced patterns
        if re.search(r"hp\s+15s", name_lower): return "HP Laptop"
        if re.search(r"hp\s+15\s+(?:core|fd1)", name_lower): return "HP Laptop"
        
        # NEW: Enhanced HP 14 Series detection
        if re.search(r"hp\s+14[-]\w{2}\d+", name_lower): return "HP Laptop"
        if re.search(r"hp\s+14[-](?:ep|em|cf|fq)", name_lower): return "HP Laptop"
        if "14-ep" in name_lower: return "HP Laptop"
        if "14-em" in name_lower: return "HP Laptop"
        if "14-cf" in name_lower: return "HP Laptop"
        if "14-fq" in name_lower: return "HP Laptop"
        
        # Essential Series fallback patterns
        if re.search(r"hp\s?14s|240 g\d|245 g\d", name_lower): return "Essential Series"
        if re.search(r"hp\s+14\s+[a-z]", name_lower): return "Essential Series"
        
        # Omnibook Series
        if "omnibook" in name_lower: return "OmniBook"
        
        return "Unknown"

    # === MSI ===
    elif detected_brand == "msi":
        # Gaming Series - Entry Level
        if "katana" in name_lower: return "Katana"
        if "cyborg" in name_lower: return "Cyborg"
        if "bravo" in name_lower: return "Bravo"
        if "thin" in name_lower: return "Thin"
        
        # Gaming Series - Mid Range
        if "pulse" in name_lower: return "Pulse"
        if "crosshair" in name_lower: return "Crosshair"
        if "sword" in name_lower: return "Sword"
        
        # Gaming Series - High Performance
        if "leopard" in name_lower: return "Leopard"
        if "raider" in name_lower: return "Raider"
        if "vector" in name_lower: return "Vector"
        if "stealth" in name_lower: return "Stealth"
        
        # Gaming Series - Flagship
        if "titan" in name_lower: return "Titan"
        
        # Content Creation & Workstation
        if "creator" in name_lower: return "Creator"
        if "workstation" in name_lower: return "Workstation"
        
        # Commercial/Business Series
        if "commercial" in name_lower: return "Commercial"
        if "modern" in name_lower: return "Modern"
        if "prestige" in name_lower: return "Prestige"
        if "summit" in name_lower: return "Summit"
        
        # Enhanced pattern matching untuk model codes
        if re.search(r"\bgf\d{2}", name_lower): return "Katana"  # GF series = Katana/Thin
        if re.search(r"\bgl\d{2}", name_lower): return "Pulse"   # GL series = Pulse
        if re.search(r"\bgp\d{2}", name_lower): return "Leopard" # GP series = Leopard
        if re.search(r"\bge\d{2}", name_lower): return "Raider"  # GE series = Raider
        if re.search(r"\bgs\d{2}", name_lower): return "Stealth" # GS series = Stealth
        if re.search(r"\bgt\d{2}", name_lower): return "Titan"   # GT series = Titan
        
        # Specific model pattern matching
        if re.search(r"ws\d{2}", name_lower): return "Workstation"  # WS series
        if re.search(r"wf\d{2}", name_lower): return "Workstation"  # WF series
        
        # Fallback untuk model codes yang umum
        if re.search(r"b13v|b14v|a13v", name_lower): return "Pulse"  # Pulse series models
        if re.search(r"b12u|a12u", name_lower): return "Crosshair"   # Crosshair series models
        if re.search(r"d7w|d2x", name_lower): return "Crosshair"     # Crosshair AI models
        if re.search(r"c1v", name_lower): return "Pulse"             # Pulse AI models
        
        return "Unknown"

    # === Axioo ===
    elif detected_brand == "axioo":
        if "mybook" in name_lower: return "MyBook"
        if "hype" in name_lower: return "Hype"
        if "pongo" in name_lower: return "Pongo"
        if "slimbook" in name_lower: return "SlimBook"
        if "neon" in name_lower: return "Neon"
        return "Unknown"

    # === Advan ===
    elif detected_brand == "advan":
        # NEW: AI Series - High Performance
        if "ai gen" in name_lower: return "AI Gen"
        
        # NEW: Gaming Series
        if "pixwar" in name_lower: return "Pixwar"
        
        # NEW: 2-in-1 Convertible Series
        if "360" in name_lower: return "360 Stylus"
        if "2in1 evo-x" in name_lower or "evo-x" in name_lower: return "2in1 Evo-X"
        
        # Existing series
        if "soulmate" in name_lower: return "Soulmate"
        if "chromebook" in name_lower: return "Chromebook"
        if "workmate" in name_lower: return "Workmate"
        if "tbook" in name_lower: return "Tbook"
        if "workpro" in name_lower: return "Workpro"
        if "workplus" in name_lower: return "Workplus"
        return "Unknown"

    # === Avita ===
    elif detected_brand == "avita":
        if "magus" in name_lower: return "Magus"
        if "essential" in name_lower: return "Essential"
        if "liber" in name_lower: return "Liber"
        if "admiror" in name_lower: return "Admiror"
        return "Unknown"

    # === Huawei ===
    elif detected_brand == "huawei":
        if "matebook" in name_lower: return "MateBook"
        return "Unknown"

    # === Infinix ===
    elif detected_brand == "infinix":
        if "xbook" in name_lower: return "Xbook"
        if "inbook" in name_lower: return "INbook"
        if "gtbook" in name_lower: return "GTbook"
        return "Unknown"

    # === Microsoft ===
    elif detected_brand == "microsoft":
        if "surface" in name_lower: return "Surface"
        return "Unknown"

    # === SPC ===
    elif detected_brand == "spc":
        if "style" in name_lower: return "Style"
        if "life" in name_lower: return "Life"
        return "Unknown"

    # === Tecno ===
    elif detected_brand == "tecno":
        if "megabook" in name_lower: return "Megabook"
        return "Unknown"

    # === Toshiba ===
    elif detected_brand == "toshiba":
        if "dynabook" in name_lower: return "Dynabook"
        if "satellite" in name_lower: return "Satellite"
        if "tecra" in name_lower: return "Tecra"
        return "Unknown"

    # === Xiaomi ===
    elif detected_brand == "xiaomi":
        if "redmibook" in name_lower: return "RedmiBook"
        return "Unknown"

    # === Zyrex ===
    elif detected_brand == "zyrex":
        if "confidante" in name_lower: return "Confidante"
        if "bunaken" in name_lower: return "Bunaken"
        if "sky" in name_lower: return "Sky"
        if "kintamani" in name_lower: return "Kintamani"
        if "lifebook" in name_lower: return "Lifebook"
        if "ultra" in name_lower: return "Ultra"
        if re.search(r"d.?tech", name_lower): return "D-Tech"
        if "blaze" in name_lower: return "Blaze"
        return "Unknown"

    # === Jumper ===
    elif detected_brand == "jumper":
        if "ezbook" in name_lower: return "Ezbook"
        return "Unknown"

    # === Samsung ===
    elif detected_brand == "samsung":
        if "galaxy book" in name_lower: return "Galaxy Book"
        if "chromebook" in name_lower: return "Chromebook"
        return "Unknown"

    # === Dell ===
    elif detected_brand == "dell":
        # Gaming Series - Priority Order
        if "alienware" in name_lower: return "Alienware"
        if "g15" in name_lower or "g series" in name_lower: return "G Series"
        if "g16" in name_lower: return "G Series"
        
        # Business & Productivity Series
        if "inspiron" in name_lower: return "Inspiron"
        if "vostro" in name_lower: return "Vostro"
        if "xps" in name_lower: return "XPS"
        if "precision" in name_lower: return "Precision"
        if "latitude" in name_lower: return "Latitude"
        if "chromebook" in name_lower: return "Chromebook"
        
        # NEW: Enhanced Dell pattern matching
        if re.search(r"dell\s+[a-z]+\s+[0-9]", name_lower): return "Inspiron"
        return "Unknown"

    # === Apple ===
    elif detected_brand == "apple":
        if "macbook air" in name_lower: return "Macbook Air"
        if "macbook pro" in name_lower: return "Macbook Pro"
        if "macbook" in name_lower: return "Macbook"
        # NEW: Enhanced Apple detection
        if re.search(r"mgn\d{2,3}", name_lower): return "Macbook Air"
        return "Unknown"
    
    return "Unknown"

def extract_processor(product_name):
    """
    Mengekstrak dan menstandardisasi nama Processor dari nama produk.
    Versi revisi - lebih akurat untuk AMD Ryzen R-series dan FX series.
    """
    name_upper = product_name.upper()
    
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
    
def extract_gpu(gpu_name):
    """
    Mengekstrak dan menstandardisasi nama GPU dari nama produk.
    Versi revisi - lebih akurat untuk Apple Silicon dan AMD Integrated Graphics.
    """
    name_upper = gpu_name.upper()
    
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

def extract_ram(ram_size):
    """
    Mengekstrak dan menstandardisasi ukuran RAM dari nama produk.
    Versi revisi - lebih akurat untuk format Apple dan frekuensi RAM.
    """
    name_upper = str(ram_size).upper()
    
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

def extract_storage(storage_size):
    """
    Mengekstrak dan menstandardisasi spesifikasi storage dari nama produk.
    Versi revisi - lebih akurat untuk SSHD dan format storage lainnya.
    """
    name_upper = str(storage_size).upper()
    
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

def extract_display(display_size):
    # Pastikan input adalah string
    if not isinstance(display_size, str):
        return 'Unknown'
    
    # Normalisasi tanda kutip khusus - TAMBAHKAN LEBIH BANYAK VARIASI
    display = display_size.replace('″', '"').replace('′', '\'').replace('．', '.').replace('', '"').replace('', '"').replace('´', '\'').replace('`', '\'')

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
        matches = list(re.finditer(pattern, display, re.IGNORECASE))
        if matches:
            for match in matches:
                size = match.group(1).replace(',', '.')
                try:
                    fsize = float(size)
                    if 10 <= fsize <= 39:
                        score = 100 - priority * 5
                        if any(ctx in display[match.start():match.end()+20].upper() 
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
        matches = list(re.finditer(pattern, display, re.IGNORECASE))
        if matches:
            for match in matches:
                size = match.group(1).replace(',', '.')
                try:
                    fsize = float(size)
                    if 10 <= fsize <= 39:
                        score = 80 - priority * 5
                        if any(ctx in display[match.start():match.end()+20].upper() 
                               for ctx in ['WQHD', 'QHD+', 'QHD', '2.2K', '2.8K', '3K', 'IPS', 'OLED', 'WQXGA', '2.5K', '2K', 'TOUCHSCREEN', 'HD', 'WQUXGA', 'WUXGA', '4K', 'FHD', '144HZ', '240HZ']):
                            score += 8
                        if '.' in size:
                            score += 3
                        # Tambah skor khusus untuk pola model produk + ukuran
                        if any(model in display[max(0, match.start()-20):match.start()].upper() 
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
        matches = list(re.finditer(pattern, display, re.IGNORECASE))
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
                        context_text = display[match.start():match.end()+20].upper()
                        if any(ctx in context_text for ctx in ['WQXGA', '2.5K', '2.8K', 'IPS', 'OLED', 'HD', 'FHD', '2K', 'TOUCHSCREEN', 'UHD', '4K', 'WQUXGA', 'WUXGA', 'QHD+', 'QHD', '144HZ', '240HZ']):
                            score += 5
                        # Tambah skor lebih tinggi untuk konteks resolusi yang jelas
                        if any(ctx in context_text for ctx in ['UHD', '4K', 'FHD', 'HD', 'WQUXGA', 'WUXGA', 'OLED', 'TOUCHSCREEN', 'QHD+', 'QHD']):
                            score += 3
                        # Tambah skor khusus untuk konteks refresh rate
                        if any(ctx in context_text for ctx in ['144HZ', '240HZ', '120HZ']):
                            score += 4
                        # Tambah skor khusus untuk pola model produk
                        if any(model in display[max(0, match.start()-20):match.start()].upper() 
                               for model in ['TRANSCEND', 'OMEN', 'YOGA', 'THINKPAD', 'IDEAPAD', 'SURFACE', 'MACBOOK']):
                            score += 8
                        # Tambah skor khusus untuk konteks "Graphics" yang diikuti HD
                        if 'GRAPHICS' in display[max(0, match.start()-30):match.start()].upper():
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

def run_etl(
    input_db_path: str = 'data/database/laptop_data_raw.db',
    current_output_db_path: str = 'data/database/laptops_current.db',
    history_output_db_path: str = 'data/database/laptops_history.db'
):
    """
    Jalankan seluruh pipeline feature engineering.
    Membaca data hasil scraping dari database, melakukan ekstraksi fitur,
    dan menyimpan hasilnya ke database SQLite (current & history).
    """
    import os
    import sqlite3
    import pandas as pd
    from datetime import datetime

    logger.info("=" * 80)
    logger.info("Starting the Feature Engineering process")
    logger.info(f"Input database: {input_db_path}")
    logger.info(f"Current output database: {current_output_db_path}")
    logger.info(f"History output database: {history_output_db_path}")

    # Validasi keberadaan file database input
    if not os.path.exists(input_db_path):
        logger.error(f"Input database not found: {input_db_path}")
        return

    try:
        # --- BACA DARI DATABASE INTEGRASI (product_raw) ---
        conn = sqlite3.connect(input_db_path)
        # Ambil data mentah dari tabel product_raw
        query = "SELECT id AS raw_id, product_name, price_raw FROM product_raw ORDER BY id DESC;" # <-- Perbaiki nama tabel
        df = pd.read_sql_query(query, conn)
        conn.close()

        logger.info(f"Data successfully read from database. Number of rows: {len(df)}")
    except Exception as e:
        logger.exception(f"Failed to read from database: {e}")
        return

    # Pastikan kolom yang dibutuhkan ada
    required_cols = ['raw_id', 'product_name', 'price_raw']
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"❌ Column '{col}' not found in the dataset!")
            logger.error(f"Available columns: {list(df.columns)}")
            return

    # Run feature extraction
    logger.info("Performing feature engineering...")
    brand_list = get_brands()
    df['brand'] = df['product_name'].apply(lambda x: extract_brand(x, brand_list))
    df['series'] = df['product_name'].apply(extract_series)
    df['processor_detail'] = df['product_name'].apply(extract_processor)
    df['processor_category'] = df['processor_detail'].apply(standardize_processor)
    df['gpu'] = df['product_name'].apply(extract_gpu)
    df['gpu_category'] = df['gpu'].apply(standardize_gpu)
    df['ram'] = df['product_name'].apply(extract_ram)
    df['storage'] = df['product_name'].apply(extract_storage)
    df['display'] = df['product_name'].apply(extract_display)

    # Tambahkan kolom tambahan yang sering digunakan di dashboard
    df['price_in_millions'] = df['price_raw'] / 1_000_000

    # Tambahkan kolom untuk tracking
    df['processed_at'] = datetime.now()
    df['valid_from'] = datetime.now()
    df['valid_to'] = None  # Akan diisi nanti jika produk tidak aktif
    df['is_active'] = True  # Asumsikan semua produk baru adalah aktif

    # --- SIMPAN KE DATABASE HISTORY ---
    # Baca data lama dari current_db
    conn_current = sqlite3.connect(current_output_db_path)
    try:
        current_df = pd.read_sql_query("SELECT * FROM products_current WHERE is_active = 1;", conn_current)
    except pd.io.sql.DatabaseError:
        # Jika tabel belum ada, buat DataFrame kosong
        current_df = pd.DataFrame(columns=['raw_id', 'product_name', 'brand', 'series', 'processor_detail', 'processor_category', 'gpu', 'gpu_category', 'ram', 'storage', 'display', 'price_raw', 'price_in_millions', 'processed_at', 'valid_from', 'valid_to', 'is_active'])

    # Cek apakah produk sudah ada di current_db
    if not current_df.empty:
        # Temukan produk yang tidak lagi muncul di df baru (artinya sudah tidak aktif)
        inactive_products = current_df[~current_df['raw_id'].isin(df['raw_id'])]

        # Update valid_to dan is_active untuk produk yang tidak aktif
        if not inactive_products.empty:
            cursor_current = conn_current.cursor()
            for _, row in inactive_products.iterrows():
                cursor_current.execute("""
                    UPDATE products_current
                    SET valid_to = ?, is_active = 0
                    WHERE raw_id = ?
                """, (datetime.now(), row['raw_id']))
            conn_current.commit()

            # Pindahkan produk yang tidak aktif ke history_db
            # Buat direktori jika belum ada
            os.makedirs(os.path.dirname(history_output_db_path), exist_ok=True)

            conn_history = sqlite3.connect(history_output_db_path)
            # Buat tabel products_history jika belum ada
            conn_history.execute("""
                CREATE TABLE IF NOT EXISTS products_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
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
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
                    valid_to DATETIME NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    FOREIGN KEY (raw_id) REFERENCES products_raw(id)
                );
            """)
            inactive_products.to_sql('products_history', conn_history, if_exists='append', index=False)
            conn_history.close()
            logger.info(f"✅ {len(inactive_products)} items moved to history database.")
        else:
            logger.info("✅ No inactive products found. History database remains unchanged.")
    else:
        logger.info("✅ No previous data in current database. Creating fresh current and history databases.")

    # --- SIMPAN DATA BARU KE CURRENT DB ---
    # Buat direktori jika belum ada
    os.makedirs(os.path.dirname(current_output_db_path), exist_ok=True)

    # Buat tabel products_current jika belum ada
    cursor_current = conn_current.cursor()
    cursor_current.execute("""
        CREATE TABLE IF NOT EXISTS products_current (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
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
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_to DATETIME,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (raw_id) REFERENCES products_raw(id)
        );
    """)

    # Bulk insert/update ke products_current
    # Kita akan replace semua produk baru ke tabel current
    # Produk lama yang tidak muncul lagi akan di-update is_active dan valid_to
    df[['raw_id', 'product_name', 'brand', 'series', 'processor_detail', 'processor_category',
        'gpu', 'gpu_category', 'ram', 'storage', 'display', 'price_raw', 'price_in_millions',
        'processed_at', 'valid_from', 'valid_to', 'is_active']].to_sql(
            'products_current',
            conn_current,
            if_exists='replace',  # Ganti semua data, karena kita handle inaktivasi di atas
            index=False
        )

    conn_current.close()

    # --- PASTIKAN FILE HISTORY DIBUAT JUGA ---
    # Ini untuk mencegah error jika tidak ada produk lama
    os.makedirs(os.path.dirname(history_output_db_path), exist_ok=True)
    conn_history = sqlite3.connect(history_output_db_path)
    # Buat tabel products_history jika belum ada
    conn_history.execute("""
        CREATE TABLE IF NOT EXISTS products_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
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
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_from DATETIME DEFAULT CURRENT_TIMESTAMP,
            valid_to DATETIME NOT NULL,
            is_active BOOLEAN DEFAULT 0,
            FOREIGN KEY (raw_id) REFERENCES products_raw(id)
        );
    """)
    conn_history.close()
    logger.info(f"✅ History database initialized at: {history_output_db_path}")

    logger.info(f"✅ Feature engineering is complete. {len(df)} items saved to current database: {current_output_db_path}")

    logger.info("=" * 80)
    logger.info("The ETL process completed without critical errors.")

if __name__ == "__main__":
    # Path ke database hasil scraping
    input_db_path = "data/database/laptop_data_raw.db"
    # Path ke database hasil ETL
    current_output_db_path = "data/database/laptops_current.db"
    history_output_db_path = "data/database/laptops_history.db"               
    run_etl(input_db_path, current_output_db_path, history_output_db_path)
