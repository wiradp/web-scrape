# main.py
"""
Main orchestrator for the full pipeline:
1. Scrape website → save snapshot DB
2. Run ETL → create current + history DB
3. Export current DB to CSV
4. Upload CSV to Supabase (Seeder)
"""

import subprocess
import sys
import os
import logging

# Ensure the module can be imported from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.logger_setup import setup_logger

logger = setup_logger("pipeline")

def run_step(step_name: str, command: list):
    logger.info(f"=== START: {step_name} ===")
    try:
        subprocess.run([sys.executable] + command, check=True)
        logger.info(f"=== SUCCESS: {step_name} ===\n")
    except subprocess.CalledProcessError as e:
        logger.exception(f"FAILED at step: {step_name}")
        raise


if __name__ == "__main__":
    logger.info("###############################################")
    logger.info("##########  PIPELINE EXECUTION START ##########")
    logger.info("###############################################")

    try:
        # 1. SCRAPER
        run_step("Scraper: Fetch Raw Laptop Data", ["src/scraper.py"])

        # 2. ETL (Feature Extraction + SCD2 + load databases)
        run_step("ETL: Process Raw Data → Current + History DB", ["src/etl.py"])

        # 3. EXPORT CURRENT DB → CSV
        run_step("Export DB to CSV", ["src/export_db_to_csv.py"])

        # 4. SEED CSV → SUPABASE
        run_step("Seed Data to Supabase", ["src/seeder.py"])

        logger.info("##########  PIPELINE COMPLETED SUCCESSFULLY ##########\n")

    except Exception as e:
        logger.exception("PIPELINE FAILED — CHECK LOGS ABOVE FOR DETAILS.")

    logger.info("###############################################")
    logger.info("##########  PIPELINE EXECUTION END   ##########")
    logger.info("###############################################\n")
