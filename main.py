"""Main application entry point."""
import sys
import os
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.database import db_config
from config.settings import Settings
from src.processors.snapshot_manager import SnapshotManager
from src.processors.change_detector import ChangeDetector
from src.utils.logger import setup_logger

logger = setup_logger("main")

def initialize_database():
    """Initialize database tables."""
    logger.info("Initializing database...")
    db_config.create_tables()
    logger.info("Database initialized")

def create_snapshot():
    """Create a snapshot."""
    logger.info("Creating snapshot...")
    snapshot_manager = SnapshotManager()
    success = snapshot_manager.create_snapshot()
    
    if success:
        logger.info("Snapshot created successfully")
    else:
        logger.error("Snapshot creation failed")
        sys.exit(1)

def detect_changes():
    """Detect changes."""
    logger.info("Detecting changes...")
    change_detector = ChangeDetector()
    success = change_detector.detect_changes()
    
    if success:
        logger.info("Change detection completed")
    else:
        logger.error("Change detection failed")
        sys.exit(1)

def run_dashboard():
    """Run Streamlit dashboard."""
    import subprocess
    
    logger.info("Starting Streamlit dashboard...")
    logger.info("Note: Using Hybrid Search for instant performance")
    
    # Set environment variable for Python path
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    # Change to project directory
    os.chdir(project_root)
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(project_root / "src" / "dashboard" / "streamlit_app.py"),
        "--server.port", str(Settings.STREAMLIT_PORT)
    ], env=env)

def run_scheduler():
    """Run scheduler."""
    import subprocess
    logger.info("Starting scheduler...")
    
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)
    
    subprocess.run([sys.executable, "run_scheduler.py"], env=env, cwd=project_root)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Company Data Management System")
    parser.add_argument(
        "command",
        choices=["init", "snapshot", "changes", "dashboard", "scheduler", "all"],
        help="Command to execute"
    )
    
    args = parser.parse_args()
    
    # Create directories
    Settings.create_directories()
    
    if args.command == "init":
        initialize_database()
    
    elif args.command == "snapshot":
        create_snapshot()
    
    elif args.command == "changes":
        detect_changes()
    
    elif args.command == "dashboard":
        run_dashboard()
    
    elif args.command == "scheduler":
        run_scheduler()
    
    elif args.command == "all":
        initialize_database()
        create_snapshot()
        detect_changes()
        logger.info("=" * 60)
        logger.info("[OK] All tasks completed!")
        logger.info("Run 'python main.py dashboard' to start the dashboard")
        logger.info("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)