# main.py
"""
Main script to run the entire laptop data processing pipeline.
Executes: scrape -> etl -> (optionally) launch dashboard.
"""

import subprocess
import sys
import os
import logging

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),  # Log ke file
        logging.StreamHandler(sys.stdout)     # Log ke terminal
    ]
)

logger = logging.getLogger(__name__)

# --- Define Paths ---
SCRAPER_PATH = "src/scraper.py"
ETL_PATH = "src/etl.py"
DASHBOARD_PATH = "src/dashboard.py"

# --- Helper Function to Run Scripts ---
def run_script(script_path: str, description: str):
    """
    Runs a Python script using subprocess.
    Logs success or failure.
    """
    logger.info(f"🔄 Executing {description}...")
    logger.info(f"📄 Script path: {script_path}")
    
    try:
        # Pastikan path file valid
        if not os.path.exists(script_path):
            logger.error(f"❌ File not found: {script_path}")
            return False

        # Jalankan script
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)) # Jika kamu ingin menjalankan dari root proyek
        )

        # Cek apakah proses berhasil (return code 0)
        if result.returncode == 0:
            logger.info(f"✅ {description} executed successfully!")
            if result.stdout:
                logger.debug(f"--- STDOUT ---\n{result.stdout}")
            return True
        else:
            logger.error(f"❌ {description} failed with return code {result.returncode}")
            logger.error(f"--- STDERR ---\n{result.stderr}")
            return False

    except FileNotFoundError:
        logger.error(f"❌ Python interpreter not found when running {script_path}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error running {script_path}: {e}")
        return False

# --- Main Pipeline Execution ---
def run_pipeline(run_dashboard: bool = False):
    """
    Runs the full pipeline: scrape -> etl -> (dashboard).
    Args:
        run_dashboard (bool): If True, launches the Streamlit dashboard after ETL.
    """
    logger.info("=" * 80)
    logger.info("🚀 Starting Laptop Data Processing Pipeline")
    logger.info("=" * 80)

    # 1. Run Scraper
    success_scraper = run_script(SCRAPER_PATH, "Scraping Process (scraper.py)")
    if not success_scraper:
        logger.critical("🚨 Scraping failed. Stopping pipeline.")
        return

    # 2. Run ETL
    success_etl = run_script(ETL_PATH, "ETL Process (etl.py)")
    if not success_etl:
        logger.critical("🚨 ETL failed. Stopping pipeline.")
        return

    logger.info("✅ Pipeline execution completed successfully!")

    # 3. (Opsional) Run Dashboard
    if run_dashboard:
        logger.info("\n--- Launching Dashboard ---")
        logger.info("📌 Note: This will start the Streamlit server. Press Ctrl+C to stop.")
        try:
            logger.info(f"📄 Dashboard path: {DASHBOARD_PATH}")
            # Ganti dengan subprocess.run jika kamu ingin kontrol lebih
            subprocess.run([sys.executable, "-m", "streamlit", "run", DASHBOARD_PATH])
        except KeyboardInterrupt:
            logger.info("🛑 Dashboard stopped by user.")
        except Exception as e:
            logger.error(f"❌ Failed to launch dashboard: {e}")

    logger.info("=" * 80)
    logger.info("🎉 Pipeline finished.")
    logger.info("=" * 80)

# --- Entry Point ---
if __name__ == "__main__":
    # --- Opsi: Jalankan dashboard setelah pipeline selesai ---
    # Ubah menjadi True jika kamu ingin sekaligus membuka dashboard
    RUN_DASHBOARD_AFTER_PIPELINE = True

    # Jalankan pipeline
    run_pipeline(run_dashboard=RUN_DASHBOARD_AFTER_PIPELINE)
