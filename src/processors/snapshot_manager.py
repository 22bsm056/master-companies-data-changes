"""Snapshot manager for daily data snapshots."""
from datetime import datetime, date
from pathlib import Path
import pandas as pd
from typing import Optional
from config.settings import Settings
from src.api.data_fetcher import DataFetcher
from src.database.operations import DatabaseOperations
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class SnapshotManager:
    """Manage daily snapshots of company data."""
    
    def __init__(self):
        """Initialize snapshot manager."""
        self.snapshot_dir = Settings.SNAPSHOT_DIR
        self.data_fetcher = DataFetcher()
        self.db_ops = DatabaseOperations()
    
    def get_snapshot_filename(self, snapshot_date: Optional[date] = None) -> Path:
        """
        Get snapshot filename for a given date.
        
        Args:
            snapshot_date: Date for snapshot (default: today)
        
        Returns:
            Path to snapshot file
        """
        if snapshot_date is None:
            snapshot_date = datetime.now().date()
        
        filename = f"snapshot_{snapshot_date.strftime('%Y-%m-%d')}.csv"
        return self.snapshot_dir / filename
    
    def create_snapshot(self, max_records: Optional[int] = None) -> bool:
        """
        Create daily snapshot.
        
        Args:
            max_records: Maximum records to fetch
        
        Returns:
            Success status
        """
        try:
            logger.info("Starting snapshot creation...")
            
            # Fetch data
            df = self.data_fetcher.fetch_all_data(max_records)
            
            if df.empty:
                logger.error("No data fetched for snapshot")
                return False
            
            # Normalize dataframe
            df = self.data_fetcher.normalize_dataframe(df)
            
            # Save to CSV
            snapshot_file = self.get_snapshot_filename()
            df.to_csv(snapshot_file, index=False)
            logger.info(f"Snapshot saved to {snapshot_file}")
            
            # Save to database
            companies_data = df.to_dict('records')
            self.db_ops.save_companies_bulk(companies_data)
            
            # Create snapshot record
            self.db_ops.create_snapshot(
                snapshot_date=datetime.now().date(),
                file_path=str(snapshot_file),
                total_records=len(df)
            )
            
            logger.info(f"Snapshot created successfully with {len(df)} records")
            return True
            
        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")
            return False
    
    def get_latest_snapshot(self) -> Optional[pd.DataFrame]:
        """
        Get the latest snapshot.
        
        Returns:
            DataFrame or None
        """
        try:
            snapshot_files = sorted(self.snapshot_dir.glob("snapshot_*.csv"), reverse=True)
            
            if not snapshot_files:
                logger.warning("No snapshot files found")
                return None
            
            latest_file = snapshot_files[0]
            logger.info(f"Loading latest snapshot: {latest_file}")
            return pd.read_csv(latest_file)
            
        except Exception as e:
            logger.error(f"Error loading latest snapshot: {e}")
            return None
    
    def get_snapshot_by_date(self, snapshot_date: date) -> Optional[pd.DataFrame]:
        """
        Get snapshot by date.
        
        Args:
            snapshot_date: Date of snapshot
        
        Returns:
            DataFrame or None
        """
        try:
            snapshot_file = self.get_snapshot_filename(snapshot_date)
            
            if not snapshot_file.exists():
                logger.warning(f"Snapshot file not found: {snapshot_file}")
                return None
            
            return pd.read_csv(snapshot_file)
            
        except Exception as e:
            logger.error(f"Error loading snapshot: {e}")
            return None