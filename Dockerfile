# Gunakan image Python resmi
FROM python:3.10-slim

# Install dependensi sistem yang dibutuhkan oleh numpy, pandas, dll.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory di dalam container
WORKDIR /app

# Salin file requirements.txt terlebih dahulu (untuk efisiensi caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --timeout 300 --retries 3 -r requirements.txt

# Salin seluruh kode ke dalam container
COPY . .

# Expose port yang digunakan oleh Streamlit
EXPOSE 8501

# Perintah untuk menjalankan dashboard
CMD ["streamlit", "run", "src/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]