# dashboard.py
import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sqlite3


# Set page config
st.set_page_config(
    page_title="Laptop Market Analysis Dashboard",
    page_icon="💻",
    layout="wide"
)

# Custom CSS to improve table formatting
st.markdown("""
    <style>
    .dataframe {
        font-size: 12px;
        text-align: left;
    }
    .st-emotion-cache-1y4p8pa {
        max-width: 100%;
    }
    .st-emotion-cache-1wrcr25 {
        margin-bottom: 0rem;
    }
    .st-af {
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# --- INISIALISASI KONEKSI SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        return create_client(supabase_url=url, supabase_key=key)
    
    except Exception as e:
        st.error(f"Failed to connect to Supabase:: {e}. Ensure that secrets are set.")
        return None

supabase = init_connection()

# --- LOAD DATA DARI SUPABASE ---
@st.cache_data(ttl=600) # Cache data selama 10 menit
def load_data():
    if supabase is None:
        return pd.DataFrame() # Keluar jika koneksi gagal
    
    st.info("☁️ Loading data from Supabase...")
    
    try:
        # Mengambil data dari tabel 'products_current' di Supabase
        # Gunakan 1 (integer) bukan True (boolean) untuk filter is_active
        # Pastikan setting 'Max Rows' di Supabase API Settings sudah > 64000
        response = supabase.table('products_current').select('*').eq('is_active', 1).execute()
        
        # Supabase client mengembalikan dictionary, kita ubah ke DataFrame
        df = pd.DataFrame(response.data)

        # --- Pembersihan dan Konversi Tipe Data (Penting) ---
        # Supabase mengembalikan semuanya sebagai string, kita konversi tipe numerik
        if not df.empty:
            df['price_in_millions'] = pd.to_numeric(df['price_in_millions'], errors='coerce')
            # Konversi kolom tanggal ke format datetime
            df['valid_from'] = pd.to_datetime(df['valid_from'], errors='coerce')
            
        st.success(f"✅ Loaded successfully {len(df)} data rows from Supabase.")
        return df
        
    except Exception as e:
        st.error(f"Error loading data from Supabase: {e}")
        return pd.DataFrame() # Return empty DF biar gak crash

# Load data dari Supabase
df = load_data()

# Cek apakah data berhasil dimuat
if df.empty:
    st.warning("Data is missing or failed to load. Check the logs above")
    st.stop()

# --- Bersihkan dan validasi kolom harga final (price_in_millions) ---
# Kita tidak perlu memproses price_raw lagi, karena ini data bersih dari ETL
    
if 'price_in_millions' in df.columns:
    # 1. Pastikan nilai adalah numerik dan bukan NaN
    df['price_in_millions'] = pd.to_numeric(df['price_in_millions'], errors='coerce')
    df = df[df['price_in_millions'].notna()]
    
    # 2. Filter harga yang masuk akal (> 0 dan < 150 juta)
    df = df[df['price_in_millions'] > 0]
    df = df[df['price_in_millions'] < 150]  # Filter harga yang masuk akal (< 150 juta)
    
    # 3. Remove duplicates dan sort
    df = df.drop_duplicates(subset=['product_name', 'brand']).sort_values('price_in_millions')

else:
    st.error("Kolom price_in_millions tidak ditemukan dalam dataset")
    st.stop() # Hentikan eksekusi jika kolom utama harga hilang

# Main title with styling
st.title("🔍 Indonesian Laptop Market Analysis Dashboard")
st.markdown("---")

if not df.empty:
    # Tambahkan KPI di awal
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products", len(df))
    col2.metric("Avg. Price (Rp)", f"{df['price_in_millions'].mean():,.2f}M")
    col3.metric("Most Popular Brand", df['brand'].mode()[0])
    col4.metric("Most Common RAM", df['ram'].mode()[0])

    # Sidebar filters
    st.sidebar.header("📊 Filters")

    # Filter seperti sebelumnya
    all_brands = sorted(df['brand'].unique())
    selected_brands = st.sidebar.multiselect(
        "Select Brands:",
        options=all_brands,
        default=all_brands  # <-- Default ke semua brand
    )

    max_price = float(df['price_in_millions'].max())
    min_price = float(df['price_in_millions'].min())
    price_range = st.sidebar.slider(
        "Price Range (Million Rp):",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price),  # <-- Default ke semua rentang
        step=0.1
    )

    processor_categories = ['All'] + sorted(df['processor_category'].unique().tolist())
    selected_processor = st.sidebar.selectbox("Processor Category:", processor_categories)

    gpu_categories = ['All'] + sorted(df['gpu_category'].unique().tolist())
    selected_gpu = st.sidebar.selectbox("GPU Category:", gpu_categories)

    # Apply filters
    filtered_df = df.copy()  # Start from original df

    # Brand filter
    if selected_brands:
        filtered_df = filtered_df[filtered_df['brand'].isin(selected_brands)]

    # Price range filter
    filtered_df = filtered_df[
        (filtered_df['price_in_millions'] >= price_range[0]) & (filtered_df['price_in_millions'] <= price_range[1])
    ]

    # Pastikan tidak ada nilai NaN pada kolom price_in_millions
    filtered_df = filtered_df[filtered_df['price_in_millions'].notnull()]

    # Processor category filter
    if selected_processor != 'All':
        filtered_df = filtered_df[filtered_df['processor_category'] == selected_processor]

    # GPU category filter
    if selected_gpu != 'All':
        filtered_df = filtered_df[filtered_df['gpu_category'] == selected_gpu]
    
    # Tambahkan Tab
    tab1, tab2, tab3, tab4 = st.tabs(["Price Analysis", "Specifications", "Distribution", "Product List"])

    with tab1:
        st.subheader("📈 Laptop Price Distribution by Brand")
        if filtered_df.empty:
            st.warning("No data available for the selected filters.")
        else:
            # Create a more visually appealing box plot
            fig_price = px.box(
                filtered_df,
                x='brand',
                y='price_in_millions',
                color='brand',  # Color each brand differently
                labels={'price_in_millions': 'Price (in Millions)', 'brand': 'Brand'},
                points='outliers',
                height=500,
                width=1000  # Wider plot for better readability
            )

            # Customize the appearance
            fig_price.update_traces(
                marker=dict(size=4),  # Smaller outliers
                line=dict(width=2)   # Thicker box lines
            )

            # Update layout
            fig_price.update_layout(
                showlegend=False,
                xaxis=dict(tickangle=45),
                yaxis=dict(
                    title="Price (in Millions)",
                    gridcolor='rgba(255, 255, 255, 0.2)',
                    zeroline=False,
                    range=[
                        filtered_df['price_in_millions'].min() * 0.95,
                        filtered_df['price_in_millions'].max() * 1.05
                    ]
                ),
                plot_bgcolor='rgba(0, 0, 0, 0.8)',  # Dark background
                paper_bgcolor='rgba(0, 0, 0, 0.9)',  # Dark paper
                font=dict(color='white'),
                margin=dict(l=50, r=50, t=50, b=100)
            )

            st.plotly_chart(fig_price, width='stretch')  

            # Insight
            avg_price_by_brand = filtered_df.groupby('brand')['price_in_millions'].mean().sort_values(ascending=False)
            if not avg_price_by_brand.empty:
                top_brand = avg_price_by_brand.index[0]
                st.info(f"💡 Insight: {top_brand} has the highest average price.")

    with tab2:
        st.subheader("💾 RAM & Storage Distribution")
        if filtered_df.empty:
            st.warning("No data available for the selected filters.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                # Filter 'Unknown RAM'
                df_ram_filtered = filtered_df[filtered_df['ram'] != 'Unknown RAM'].copy()
                
                # Normalisasi: hapus spasi ekstra
                df_ram_filtered['ram'] = df_ram_filtered['ram'].str.strip()

                # Hitung value counts
                ram_counts = df_ram_filtered['ram'].value_counts().reset_index()
                ram_counts.columns = ['ram', 'count']

                # Urutan berdasarkan count (descending)
                ram_counts = ram_counts.sort_values('count', ascending=False)

                # Dapatkan urutan RAM berdasarkan count (descending) untuk mengunci plot
                ram_order = ram_counts['ram'].tolist()

                # Plot dengan Plotly
                fig_ram = px.bar(
                    ram_counts, # Gunakan DataFrame yang sudah dihitung dan diurutkan
                    x='ram',
                    y='count',
                    title='RAM Distribution',
                    labels={'ram': 'RAM', 'count': 'Count'},
                    category_orders={'ram': ram_order} # Kunci urutan sesuai count
                )
                fig_ram.update_xaxes(tickangle=45)
                # Tambahkan hover template
                fig_ram.update_traces(
                    hovertemplate="<b>RAM:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>"
                )
                st.plotly_chart(fig_ram, width='stretch')  

            with col2:
                # Filter 'Unknown Storage'
                df_storage_filtered = filtered_df[filtered_df['storage'] != 'Unknown Storage'].copy()
                # Normalisasi: hapus spasi ekstra
                df_storage_filtered['storage'] = df_storage_filtered['storage'].str.strip()

                # Hitung value counts
                storage_counts = df_storage_filtered['storage'].value_counts().reset_index()
                storage_counts.columns = ['storage', 'count']

                # Urutan berdasarkan count (descending)
                storage_counts = storage_counts.sort_values('count', ascending=False)

                # Dapatkan urutan RAM berdasarkan count (descending) untuk mengunci plot
                storage_order = storage_counts['storage'].tolist()

                # Plot
                fig_storage = px.bar(
                    storage_counts,  # Gunakan DataFrame yang sudah dihitung
                    x='storage',
                    y='count',        # Tambahkan y='count' secara eksplisit
                    title='Storage Distribution',
                    labels={'storage': 'Storage', 'count': 'Count'},
                    category_orders={'storage': storage_order}  # Kunci urutan
                )
                fig_storage.update_xaxes(tickangle=45)
                # Tambahkan hover template
                fig_storage.update_traces(
                    hovertemplate="<b>Storage:</b> %{x}<br><b>Count:</b> %{y}<extra></extra>"
                )
                st.plotly_chart(fig_storage, width='stretch') 

    with tab3:
        st.subheader("🔥 Processor vs GPU Category Distribution")
        if filtered_df.empty:
            st.warning("No data available for the selected filters.")
        else:
            # Filter out rows where either processor_category or gpu_category is NaN
            filtered_df_clean = filtered_df.dropna(subset=['processor_category', 'gpu_category'])

            if filtered_df_clean.empty:
                st.warning("No data available for Processor vs GPU after removing missing values.")
            else:
                # Create heatmap using px.density_heatmap (more robust)
                fig_heatmap = px.density_heatmap(
                    filtered_df_clean,
                    x='gpu_category',
                    y='processor_category',
                    labels={'gpu_category': 'GPU Category', 'processor_category': 'Processor Category'},
                    color_continuous_scale='Viridis',
                    text_auto=True,
                    height=600,  # Tingkatkan tinggi agar lebih lega
                    width=1000   # Lebar tetap lebar
                )
                fig_heatmap.update_xaxes(tickangle=45)
                # Tambahkan margin untuk memberi ruang pada label Y
                fig_heatmap.update_layout(
                    margin=dict(l=150, r=50, t=50, b=150),  # l=left, r=right, t=top, b=bottom
                    yaxis=dict(automargin=True),  # Biarkan Plotly mengatur margin Y secara otomatis
                    xaxis=dict(automargin=True)   # Biarkan Plotly mengatur margin X secara otomatis
                )
                st.plotly_chart(fig_heatmap, width='stretch') 

                # Insight
                top_proc_gpu = filtered_df_clean.groupby(['processor_category', 'gpu_category']).size().idxmax()
                st.info(f"💡 Most common pairing: {top_proc_gpu[0]} + {top_proc_gpu[1]}")

                # Optional: Add a bar chart of top processor-gpu combinations
                st.subheader("📊 Top 10 Processor-GPU Combinations")
                top_combos = filtered_df_clean.groupby(['processor_category', 'gpu_category']).size().reset_index(name='count').sort_values(by='count', ascending=False).head(10)
                fig_combo = px.bar(
                    top_combos,
                    x='count',
                    y=top_combos['processor_category'] + ' + ' + top_combos['gpu_category'],
                    orientation='h',
                    labels={'y': 'Processor + GPU', 'x': 'Count'}
                )
                fig_combo.update_layout(yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_combo, width='stretch') 

    with tab4:
        st.subheader("📋 Detailed Product List")
        st.markdown("*Scroll horizontally to see all columns. Pagination is applied below.*")

        if filtered_df.empty:
            st.warning("No data available for the selected filters.")
        else:
            # --- LOGIKA PAGINATION ---
            total_rows = len(filtered_df)
            
            # Pengaturan Baris per Halaman (Ditempatkan di dalam Tab 4)
            st.sidebar.markdown("---")
            st.sidebar.subheader("Display Settings")
            rows_per_page = st.sidebar.number_input(
                "Products per Page",
                min_value=10,
                max_value=1000,
                value=25,
                step=50,
                key='rows_per_page'
            )

            # Hitung jumlah halaman
            total_pages = int(np.ceil(total_rows / rows_per_page))
            
            # Pastikan current_page ada di session_state
            if 'page' not in st.session_state or st.session_state.page > total_pages:
                 st.session_state.page = 1
            
            # Kontrol navigasi halaman (diletakkan di bagian utama)
            col_info, col_nav = st.columns([3, 2])

            with col_nav:
                current_page = st.number_input(
                    f"Page (of {total_pages})",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.page,
                    step=1,
                    key='page_number'
                )
                st.session_state.page = current_page

            # Hitung index data yang akan ditampilkan
            start_row = (current_page - 1) * rows_per_page
            end_row = start_row + rows_per_page

            # Dataframe yang ditampilkan hanya sebagian
            display_df_raw = filtered_df.iloc[start_row:end_row].copy()
            
            with col_info:
                st.info(f"Showing **{len(display_df_raw)}** of a total of **{total_rows}** filtered data rows (Page {current_page} of {total_pages}).")


            # --- FORMATTING TAMPILAN DATAFRAME ---
            display_df_raw['price'] = display_df_raw['price_in_millions'].apply(lambda x: f"{x:,.2f}M")

            display_df = display_df_raw[[
                'product_name', 'brand', 'series', 'processor_detail', 'gpu', 'ram', 
                'storage', 'display', 'price'
            ]].rename(columns={
                'product_name': 'Product Name',
                'brand': 'Brand',
                'series': 'Series',
                'processor_detail': 'Processor',
                'gpu': 'GPU',
                'ram': 'RAM',
                'storage': 'Storage',
                'display': 'Display',
                'price': 'Price (Rp)'
            })

            # Tampilkan hanya data yang sudah dipaginasi
            st.dataframe(
                display_df,
                width='stretch',
                height=400
            )

    # Summary statistics
    st.subheader("📊 Summary Statistics")
    if not filtered_df.empty:
        col5, col6, col7 = st.columns(3)

        with col5:
            st.metric(
                "Average Price",
                f"Rp {filtered_df['price_in_millions'].mean():,.2f}M",
                f"{len(filtered_df)} products"
            )

        with col6:
            st.metric(
                "Most Common RAM",
                filtered_df['ram'].mode().iloc[0] if not filtered_df.empty else "N/A",
                f"{filtered_df['ram'].value_counts().iloc[0]} products" if not filtered_df.empty else "N/A"
            )

        with col7:
            st.metric(
                "Most Common Storage",
                filtered_df['storage'].mode().iloc[0] if not filtered_df.empty else "N/A",
                f"{filtered_df['storage'].value_counts().iloc[0]} products" if not filtered_df.empty else "N/A"
            )
    else:
        st.warning("No data available for the selected filters.")

    # Footer
    st.markdown("---")
    st.markdown("*Dashboard created for laptop market analysis in Indonesia*")
else:
    st.error("No data available. Please check the data source.")