# 💻 Laptop Market Analytics — End-to-End Data & AI Pipeline

**Author:** [Wira Dhana Putra](https://wiradp.github.io)  
**Status:** Public Preview (Active Development)  
**Live Demo:** _Coming Soon via Streamlit Cloud_

---

## 🌍 Overview

This project is an **end-to-end data pipeline** that automatically collects and analyzes laptop product information from online marketplaces such as [Viraindo.com](https://viraindo.com/notebook.html).  
The system extracts key specifications (brand, processor, GPU, RAM, storage, etc.), tracks price changes over time, and visualizes insights through an interactive dashboard.

It is built to be:
- ⚙️ **Automated** – one command runs scraping, data cleaning, and dashboard update.
- 📈 **Scalable** – easily handles thousands of products and updates.
- 🧠 **Insightful** – enables analytics, forecasting, and future AI-driven recommendations.

---

## 🏗️ Architecture


- **scraper.py** → Fetches product names and raw prices from marketplace pages.  
- **etl.py** → Cleans and enriches data with extracted columns such as:
  - Brand (`brand`)
  - Series (`series`)
  - Processor details & category (`processor_detail`, `processor_category`)
  - GPU & GPU category (`gpu`, `gpu_category`)
  - RAM, storage, display size, and price normalization.  
- **dashboard.py** → Visualizes and analyzes market trends interactively (via Streamlit).  
- **Database** → Stores historical price and product updates for long-term insights.

---

## 🔍 Example Data (after ETL)

| raw_product_name | brand | series | processor_category | gpu_category | ram | storage | display | price_raw | 
|---------------|--------|--------|--------------------|---------------|------|----------|----------|----------------|
| ASUS Vivobook Go 14 E410KA | ASUS | Vivobook Go | Intel N-Series | Integrated | 4 GB | 256 GB SSD | 14" | 4.5 |
| Lenovo LOQ 15AHP9 | Lenovo | LOQ | AMD Ryzen 7 | RTX 4050 | 16 GB | 512 GB SSD | 15.6" | 15.9 |

---

## 📊 Key Features

### Core Pipeline
✅ Automated web scraping and incremental updates  
✅ Historical price tracking in database  
✅ Feature engineering (brand, processor, GPU, RAM, storage, display)  
✅ Streamlit dashboard for market visualization  

### Future Enhancements
🚀 **AI-powered insights** – "Find the best laptop under 8 million IDR"  
🧩 **Semantic search** – similar product recommendation using embeddings  
📉 **Price anomaly detection** – alert when a product price drops unusually  
📆 **Trend forecasting** – using Prophet or ARIMA for future price predictions  
🧱 **Migration to PostgreSQL / Cloud DB** – for larger-scale deployments  
🌐 **API endpoint (FastAPI)** – expose analytics and product search via REST API  

---
