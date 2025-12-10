# main.py
"""
Main orchestrator for the full pipeline:
1. Scrape website → save snapshot DB
2. Run ETL → create current + history DB (with feature extraction)
3. Export current DB to CSV
4. Upload CSV to Supabase (Seeder)

Pipeline stages:
  STAGE 1: Raw Data Acquisition (Scraper)
  STAGE 2: Feature Extraction & ETL Processing (ETL with SCD-2)
  STAGE 3: Data Export (DB → CSV)
  STAGE 4: Data Warehouse Seeding (CSV → Supabase)
"""

import subprocess
import sys
import os
import time
from pathlib import Path

# Ensure the module can be imported from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.logger_setup import setup_logger

logger = setup_logger("pipeline")

# Pipeline configuration
PIPELINE_CONFIG = {
    "raw_db": "data/database/raw/laptops_data_raw.db",
    "current_db": "data/database/current/laptops_current.db",
    "history_db": "data/database/history/laptops_history.db",
    "meta_db": "data/database/meta/laptops_meta.db",
    "csv_export": "data/csv/laptops_current_export.csv",
}

def ensure_directories():
    """Pastikan semua direktori yang diperlukan ada."""
    dirs = [
        "data/database/raw",
        "data/database/current",
        "data/database/history",
        "data/database/meta",
        "data/csv",
        "logs",
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    logger.info("✓ All required directories verified.")

def verify_step_prerequisites(step_num: int) -> bool:
    """Verifikasi bahwa file yang diharapkan ada sebelum step berikutnya."""
    if step_num == 2:  # Sebelum ETL, raw DB harus ada
        if not os.path.exists(PIPELINE_CONFIG["raw_db"]):
            logger.error(f"❌ Raw DB not found: {PIPELINE_CONFIG['raw_db']}")
            return False
    elif step_num == 3:  # Sebelum Export, current DB harus ada
        if not os.path.exists(PIPELINE_CONFIG["current_db"]):
            logger.error(f"❌ Current DB not found: {PIPELINE_CONFIG['current_db']}")
            return False
    elif step_num == 4:  # Sebelum Seeder, CSV harus ada
        if not os.path.exists(PIPELINE_CONFIG["csv_export"]):
            logger.error(f"❌ CSV export not found: {PIPELINE_CONFIG['csv_export']}")
            return False
    return True

def run_step(step_num: int, step_name: str, command: list, check_prerequisites: bool = True):
    """
    Run a pipeline step dengan timing dan error handling.
    
    Args:
        step_num: Nomor step (1-4)
        step_name: Nama deskriptif step
        command: Command untuk dijalankan
        check_prerequisites: Apakah check file prerequisites sebelum run
    """
    logger.info(f"")
    logger.info(f"{'='*60}")
    logger.info(f"STEP {step_num}/4: {step_name}")
    logger.info(f"{'='*60}")
    
    # Verifikasi prerequisites
    if check_prerequisites and not verify_step_prerequisites(step_num):
        raise RuntimeError(f"Prerequisites check failed for step {step_num}")
    
    try:
        start_time = time.time()
        logger.info(f"Command: python {' '.join(command)}")
        logger.info(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
        
        result = subprocess.run(
            [sys.executable] + command,
            check=True,
            capture_output=False,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ STEP {step_num} SUCCESS (completed in {elapsed:.2f}s)")
        return True
        
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ STEP {step_num} FAILED (failed after {elapsed:.2f}s)")
        logger.exception(f"Error details: {e}")
        raise RuntimeError(f"Pipeline failed at step {step_num}: {step_name}")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ STEP {step_num} FAILED (unexpected error after {elapsed:.2f}s)")
        logger.exception(f"Unexpected error: {e}")
        raise

def print_pipeline_summary(success: bool, elapsed_total: float):
    """Print summary report dari pipeline execution."""
    logger.info(f"")
    logger.info(f"{'#'*60}")
    logger.info(f"#{'PIPELINE SUMMARY':^58}#")
    logger.info(f"{'#'*60}")
    
    if success:
        logger.info(f"✅ STATUS: COMPLETED SUCCESSFULLY")
        logger.info(f"⏱️  TOTAL TIME: {elapsed_total:.2f}s")
        logger.info(f"")
        logger.info(f"📊 GENERATED OUTPUTS:")
        logger.info(f"   • Raw DB: {PIPELINE_CONFIG['raw_db']}")
        logger.info(f"   • Current DB: {PIPELINE_CONFIG['current_db']}")
        logger.info(f"   • History DB: {PIPELINE_CONFIG['history_db']}")
        logger.info(f"   • Meta DB: {PIPELINE_CONFIG['meta_db']}")
        logger.info(f"   • CSV Export: {PIPELINE_CONFIG['csv_export']}")
        logger.info(f"   • Logs: logs/pipeline.log")
        logger.info(f"")
        logger.info(f"🎯 NEXT STEPS:")
        logger.info(f"   1. Review logs in 'logs/pipeline.log'")
        logger.info(f"   2. Check Supabase 'products_current' table for data")
        logger.info(f"   3. Run dashboard.py to visualize results")
    else:
        logger.error(f"❌ STATUS: FAILED")
        logger.error(f"⏱️  TIME ELAPSED: {elapsed_total:.2f}s")
        logger.error(f"📋 Please check logs above for details")
    
    logger.info(f"{'#'*60}")
    logger.info(f"")


if __name__ == "__main__":
    pipeline_start = time.time()
    
    logger.info("")
    logger.info("###############################################")
    logger.info("###  LAPTOP MARKETPLACE ETL PIPELINE START  ###")
    logger.info("###############################################")
    logger.info(f"Pipeline Start: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pipeline_start))}")
    logger.info("")
    
    try:
        # Pre-flight checks
        logger.info("🔧 RUNNING PRE-FLIGHT CHECKS...")
        ensure_directories()
        logger.info("")
        
        # STAGE 1: SCRAPER
        run_step(
            step_num=1,
            step_name="Scraper: Fetch Raw Laptop Data from Viraindo.com",
            command=["src/scraper.py"],
            check_prerequisites=False
        )

        # STAGE 2: ETL (with Feature Extraction + SCD-2)
        run_step(
            step_num=2,
            step_name="ETL: Feature Extraction & SCD-2 Processing",
            command=["src/etl.py"],
            check_prerequisites=True
        )

        # STAGE 3: EXPORT to CSV
        run_step(
            step_num=3,
            step_name="Export: Current DB → CSV",
            command=["src/export_db_to_csv.py"],
            check_prerequisites=True
        )

        # STAGE 4: SEED to SUPABASE
        run_step(
            step_num=4,
            step_name="Seeder: CSV → Supabase PostgreSQL",
            command=["src/seeder.py"],
            check_prerequisites=True
        )

        # Pipeline completed successfully
        pipeline_end = time.time()
        total_elapsed = pipeline_end - pipeline_start
        print_pipeline_summary(success=True, elapsed_total=total_elapsed)
        logger.info("###############################################")
        logger.info("###  PIPELINE EXECUTION COMPLETED SUCCESSFULLY ###")
        logger.info("###############################################\n")

    except Exception as e:
        pipeline_end = time.time()
        total_elapsed = pipeline_end - pipeline_start
        
        logger.error("")
        logger.error("=" * 60)
        logger.error("❌ PIPELINE EXECUTION FAILED")
        logger.error("=" * 60)
        logger.exception(f"Root cause: {e}")
        
        print_pipeline_summary(success=False, elapsed_total=total_elapsed)
        logger.error("###############################################")
        logger.error("###  PIPELINE EXECUTION FAILED  ###")
        logger.error("###############################################\n")
        
        sys.exit(1)
