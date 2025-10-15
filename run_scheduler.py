"""Scheduler for automated tasks."""
import schedule
import time
from datetime import datetime
from src.processors.snapshot_manager import SnapshotManager
from src.processors.change_detector import ChangeDetector
from src.agents.rag_system import RAGSystem
from src.utils.logger import setup_logger
from config.settings import Settings

logger = setup_logger("scheduler")

def daily_snapshot_job():
    """Daily snapshot creation job."""
    logger.info("Starting daily snapshot job...")
    
    snapshot_manager = SnapshotManager()
    success = snapshot_manager.create_snapshot()
    
    if success:
        logger.info("Daily snapshot completed successfully")
    else:
        logger.error("Daily snapshot failed")

def daily_change_detection_job():
    """Daily change detection job."""
    logger.info("Starting daily change detection job...")
    
    change_detector = ChangeDetector()
    success = change_detector.detect_changes()
    
    if success:
        logger.info("Change detection completed successfully")
        
        # Index changes in RAG system
        rag_system = RAGSystem()
        rag_system.index_changes()
        rag_system.index_snapshots()
    else:
        logger.error("Change detection failed")

def main():
    """Main scheduler function."""
    logger.info("Scheduler started")
    
    # Schedule jobs
    schedule.every().day.at(Settings.SNAPSHOT_TIME).do(daily_snapshot_job)
    schedule.every().day.at(Settings.CHANGE_DETECTION_TIME).do(daily_change_detection_job)
    
    logger.info(f"Snapshot scheduled at: {Settings.SNAPSHOT_TIME}")
    logger.info(f"Change detection scheduled at: {Settings.CHANGE_DETECTION_TIME}")
    
    # Run immediately on start (optional)
    # daily_snapshot_job()
    # daily_change_detection_job()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")