# 🧠 Web Scrape Laptop Analytics — End-to-End Data & AI Project

**Author:** [Wira Dhana Putra](https://wiradp.github.io)  
**Live Portfolio Page:** [https://wiradp.github.io/web-scrape](https://wiradp.github.io/web-scrape)  
**Status:** In Development (Public Preview)

---

## 🌐 Project Overview

This is an **end-to-end data project** that automatically scrapes laptop product data from an online marketplace ([viraindo.com](https://viraindo.com/notebook.html)), cleans and processes the data, extracts key product features (brand, processor, GPU, RAM, etc.), and then makes the data available through APIs and dashboards.

The project is designed to be:

- **Automated** – runs scheduled web scraping and ETL jobs.
- **Scalable** – supports large datasets (>10K products).
- **Monitored** – detects changes in product price, stock, or new arrivals.
- **AI-integrated** – includes semantic search, similarity matching, and anomaly detection.
- **Public-accessible** – deployable as an interactive web app and API for portfolio demonstration.

---

## 🏗️ Project Architecture

            ┌────────────────────────────┐
            │   Target Website (HTML)    │
            └────────────┬───────────────┘
                         │
                         ▼
                ┌───────────────────┐
                │  Web Scraper      │
                │ (Scrapy/Playwright) │
                └─────────┬─────────┘
                          │
                          ▼
                  ┌──────────────┐
                  │ Raw Storage  │ (CSV / S3)
                  └──────┬───────┘
                         ▼
                ┌──────────────────┐
                │ ETL & Feature Eng │
                │ (Python / Pandas) │
                └────────┬─────────┘
                         ▼
             ┌───────────────────────────┐
             │ Database / Data Warehouse │
             │ (PostgreSQL / ClickHouse) │
             └────────┬──────────────────┘
                      ▼
           ┌─────────────────────────────┐
           │  FastAPI / RESTful API Layer │
           └────────┬────────────────────┘
                    ▼
      ┌──────────────────────────────┐
      │  Frontend (React + Tailwind) │
      └──────────────────────────────┘

---

## ⚙️ Features

### ✅ Core Features
- Web scraping laptop product listings from online marketplace.  
- Data cleaning, normalization, and feature extraction:
  - Brand
  - Processor details & category
  - GPU & GPU category
  - RAM capacity
  - Storage capacity
  - Display size
- Automatic deduplication and timestamp tracking.
- Price normalization and numeric conversion.

### ⚡ Advanced / Scalable Features
- Automated scheduling (Airflow / Prefect / cron jobs).
- Continuous scraping & data refresh pipeline.
- Monitoring dashboard (Grafana + Prometheus).
- Alerts when:
  - A new product appears.
  - A product price changes significantly.
  - Scraper fails or data anomaly detected.

### 🤖 AI & Analytics Features
- **Semantic product search** (embedding-based, similarity search).  
- **Anomaly detection** for price fluctuation (e.g., Isolation Forest / Prophet).  
- **Recommendation system** – “similar laptops” based on specs.  
- **Price trend forecasting** using ML models.  
- **Natural language insights**: “Find best value laptops under 6 million.”

---

## 🧩 Data Example (Post-Feature Engineering)

| Product_Name | Price | Brand | Processor_Detail | Processor_Category | GPU | GPU_Category | RAM | Storage | Display |
|---------------|-------|--------|------------------|--------------------|-----|---------------|------|----------|----------|
| ADVAN CHROMEBOOK N4020 4GB 32GB | 2800000 | ADVAN | Intel N4020 | Intel N-Series | Intel Graphics | Integrated | 4GB | 32GB | 11.6" |
| ADVAN Soulmate N4020 4GB 128GB Win 11 | 2300000 | ADVAN | Intel N4020 | Intel N-Series | Intel Graphics | Integrated | 4GB | 128GB | 14" |

---

## 🧮 Tech Stack

| Layer | Technology | Description |
|-------|-------------|-------------|
| **Scraping** | Scrapy / Playwright | Data extraction & crawling |
| **Data Processing** | Pandas / Python | Cleaning, feature extraction |
| **Storage** | PostgreSQL / ClickHouse | Structured product & price history |
| **API** | FastAPI | REST/GraphQL endpoints |
| **Frontend** | React + Tailwind CSS | Interactive dashboard |
| **AI / ML** | OpenAI Embeddings / Scikit-learn / Prophet | Semantic search & analytics |
| **Monitoring** | Prometheus / Grafana | Metrics & alerting |
| **Orchestration** | Airflow / Prefect | Task scheduling & automation |
| **Deployment** | Docker / Cloud Run / GitHub Pages | Public hosting & scalability |

---


