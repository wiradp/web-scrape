# 💻 Laptop Market Analytics — Automated Data Pipeline

---

## 🌍 What is this?
We're working on an automated system designed to track laptop prices across Indonesia. It pulls data from online marketplaces, cleans it up, and presents it on a public dashboard for everyone to see.

This system is more advanced than simple scrapers because it remembers history. When a laptop's price changes today, it saves the old price instead of deleting it. This feature enables users to see price trends and quickly identify new product arrivals.

---

## 🚀 Key Features (What's Done)
**1. Smart Data Collection**
- **Automated Scraping:** Collects thousands of laptop data points automatically.
- **Data Cleaning:** Converts messy text (e.g., "16gb ddr4") into clean data columns (RAM: 16 GB).

**2. Historical Tracking (SCD Type 2)**
- **Price History:** If a price changes, the old data is archived, not deleted.
- **Change Logging:** The system records exactly when a price changed or when a new product was added.

**3. Hybrid Database System**
- **Local Processing:** Uses **SQLite** for fast, safe data processing on the local machine.
- **Cloud Sync:** Automatically syncs clean data to **Supabase (PostgreSQL)** so the public dashboard is always up-to-date.

**4. Interactive Dashboard**
- **"What's New" Tab:** A special feature that shows New Arrivals and Price Drops/Hikes from the latest update.
- **Filters:** Filter by Brand, RAM, Processor, and GPU.
- **Analytics:** Visualizes price distributions and spec trends.

---

## 🏗️ Architecture: How it Works
The system runs on a pipeline called `run_pipeline.sh` which executes these steps in order:

1. `scraper.py` Visits the website and downloads raw data into a local database.
2. `etl.py` **(Extract, Transform, Load)** * Cleans the raw data.
  - Extracts specs (Brand, CPU, GPU).
  - Compares new data vs. old data to detect price changes.
5. `seeder.py` Uploads the processed data from the Local Database to the **Supabase Cloud**.
6. `dashboard.py` The user interface (built with Streamlit) fetches data from Supabase and displays it to the user.

---

## 🛠️ Tech Stack
- **Language**: Python 🐍
- **Automation**: Bash Script & Cron Job
- **Data Processing**: Pandas, NumPy
- **Database**: SQLite (Local) & Supabase (Cloud/PostgreSQL)
- **Visualization**: Streamlit, Plotly, Matplotlib

---

## 🔮 Future Roadmap
- 🧠 **AI Semantic Search:** "Find me a cheap laptop for video editing" (Using Vector Embeddings).
- 📆 **Price Forecasting:** Predict when prices might drop using Machine Learning.
- 🔔 **Email Alerts:** Notify users when their favorite laptop gets a discount.

---

## 📂 Project Structure

```
├── data/               # Local database storage
├── logs/               # Automation logs
├── src/
│   ├── scraper.py      # Grabs data from web
│   ├── etl.py          # Cleans & processes history
│   ├── seeder.py       # Syncs local DB to Cloud
│   ├── dashboard.py    # The Streamlit App
│   └── ...
├── run_pipeline.sh     # Main automation script
└── requirements.txt    # Python dependencies
```

---

**Author**: [Wira Dhana Putra](https://wiradp.github.io)

**Status**: Live Production 🚀

**Live Demo**: [Click Here to View Dashboard](https://web-scrape-dashboard.streamlit.app/)

_Created with ❤️ by Wira_
