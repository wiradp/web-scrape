# analysis.py
# Digunakan untuk analisis data produk, khususnya untuk mengevaluasi produk dengan Series 'Unknown'
# dan memberikan saran pola regex untuk memperbaiki fungsi extract_series().

from collections import Counter
import re
import pandas as pd

def evaluate_unknown_series_with_suggestions(df, brand_col: str, series_col: str, product_col: str, top_n: int = 5):
    """
    Evaluasi produk dengan Series='Unknown' dan memberikan saran pola regex
    untuk memperluas fungsi extract_series() per brand.
    
    Parameter:
        df: DataFrame berisi kolom brand, series, dan nama produk
        brand_col: nama kolom brand
        series_col: nama kolom hasil extract_series
        product_col: nama kolom nama produk
        top_n: jumlah kandidat pola per brand untuk ditampilkan
    """

    # === FILTER PRODUK UNKNOWN ===
    unknown_df = df[df[series_col].str.lower() == "unknown"]
    total_unknown = len(unknown_df)
    if total_unknown == 0:
        print("Semua produk sudah memiliki Series yang terdeteksi dengan benar.")
        return None

    print(f"Ditemukan {total_unknown} produk dengan Series 'Unknown'.\n")

    # === RINGKASAN JUMLAH UNKNOWN PER BRAND ===
    summary = (
        unknown_df.groupby(brand_col)
        .size()
        .reset_index(name="Unknown_Count")
        .sort_values(by="Unknown_Count", ascending=False)
    )
    print("Ringkasan jumlah produk Unknown per brand:\n")
    print(summary.to_string(index=False))
    print("\n")

    # === SAMPEL PRODUK PER BRAND ===
    print("Contoh produk Unknown per brand:\n")
    for brand, group in unknown_df.groupby(brand_col):
        examples = group[product_col].head(3).tolist()
        print(f" {brand} ({len(group)} produk):")
        for e in examples:
            print(f"   - {e[:150]}{'...' if len(e) > 150 else ''}")
        print()

    # === ANALISIS SUGGESTION UNTUK extract_series ===
    print("Analisis frasa dan saran regex untuk penambahan di extract_series():\n")

    brand_suggestions = {}

    for brand, group in unknown_df.groupby(brand_col):
        # Ambil semua nama produk dan normalisasi seperti di extract_series
        phrases = []
        for name in group[product_col]:
            name_lower = name.lower()
            # Proses normalisasi seperti di extract_series
            name_clean = re.sub(r'[_/\\\(\)\[\]\.,:"]', ' ', name_lower)
            name_clean = re.sub(r'[^a-z0-9\s\-]', ' ', name_clean)
            name_clean = re.sub(r'\s+', ' ', name_clean).strip()
            
            # Ambil frasa umum yang mungkin menjadi series
            # Misalnya: "ideapad slim 5", "thinkpad x1", "legion 5", dll.
            # Cari frasa dengan pola: [kata] [kata] [angka atau kata tambahan]
            # Kita gunakan regex untuk menangkap pola seperti ini
            # Misal: "ideapad slim 5", "yoga 7", "thinkpad x1", "legion 5"
            
            # Pola umum: [kata] [angka atau kata] [angka atau kata]
            matches = re.findall(r'\b([a-z]+)\s+([a-z0-9]+)\s+([a-z0-9]+)\b', name_clean)
            for m in matches:
                phrases.append(' '.join(m))
            
            # Pola umum: [kata] [angka atau kata]
            matches = re.findall(r'\b([a-z]+)\s+([a-z0-9]+)\b', name_clean)
            for m in matches:
                phrases.append(' '.join(m))

        if not phrases:
            continue

        # Hitung frekuensi frasa
        phrase_counts = Counter(phrases)
        most_common_phrases = [p for p, _ in phrase_counts.most_common(top_n)]

        brand_suggestions[brand] = most_common_phrases

    # === CETAK HASIL SUGGESTION ===
    if not brand_suggestions:
        print("Tidak ada frasa umum yang bisa disarankan dari produk Unknown.")
        return summary

    for brand, phrases in brand_suggestions.items():
        print(f"Brand: {brand}")
        for phrase in phrases:
            # Ubah frasa menjadi pola regex yang bisa ditambahkan ke extract_series
            # Misal: "ideapad slim 5" -> r'\bideapad\s+slim\s+5\b'
            regex_pattern = r'\b' + r'\s+'.join(re.escape(p) for p in phrase.split()) + r'\b'
            print(f"   🔸 Frasa kandidat: '{phrase}'")
            print(f"   🔹 Pola regex potensial: (r'{regex_pattern}', 'Series Baru')")
        print()

    print("Selesai. Gunakan pola di atas untuk memperluas deteksi series di extract_series().")
    return summary, brand_suggestions