"""Populate database from CSV files."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from tqdm import tqdm
from config.settings import Settings
from config.database import db_config
from src.database.operations import DatabaseOperations
from src.utils.logger import setup_logger

logger = setup_logger("populate_db")


def populate_from_csv():
    """Populate database from CSV snapshots."""
    logger.info("=" * 60)
    logger.info("POPULATING DATABASE FROM CSV FILES")
    logger.info("=" * 60)
    
    # Initialize database
    db_config.create_tables()
    db_ops = DatabaseOperations()
    
    # Get latest snapshot
    snapshot_files = sorted(Settings.SNAPSHOT_DIR.glob("snapshot_*.csv"))
    
    if not snapshot_files:
        logger.error("No snapshot files found!")
        return
    
    latest_file = snapshot_files[-1]
    logger.info(f"Loading from: {latest_file.name}")
    
    # Read CSV in chunks
    chunk_size = 1000
    total_inserted = 0
    total_updated = 0
    
    for chunk in tqdm(pd.read_csv(latest_file, chunksize=chunk_size, low_memory=False), desc="Processing"):
        # Normalize column names
        chunk_dict = chunk.to_dict('records')
        
        success, inserted, updated = db_ops.save_companies_bulk(chunk_dict)
        
        if success:
            total_inserted += inserted
            total_updated += updated
    
    logger.info("=" * 60)
    logger.info(f"[OK] DATABASE POPULATED")
    logger.info(f"Inserted: {total_inserted:,}")
    logger.info(f"Updated: {total_updated:,}")
    logger.info("=" * 60)
    
    # Show statistics
    stats = db_ops.get_statistics(30)
    logger.info(f"Total companies in DB: {stats['total_companies']:,}")
    logger.info(f"Active companies: {stats['active_companies']:,}")


if __name__ == "__main__":
    try:
        populate_from_csv()
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)