"""Change detector for tracking data changes between snapshots."""
from datetime import datetime, date, timedelta
from pathlib import Path
import pandas as pd
import json
from typing import Optional, List, Dict, Tuple
from config.settings import Settings
from src.processors.snapshot_manager import SnapshotManager
from src.database.operations import DatabaseOperations
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChangeDetector:
    """Detect and track changes between data snapshots."""
    
    def __init__(self):
        """Initialize change detector."""
        self.changes_dir = Settings.CHANGES_DIR
        self.snapshot_manager = SnapshotManager()
        self.db_ops = DatabaseOperations()
        self.key_column = 'cin'
        
        # Ensure changes directory exists
        self.changes_dir.mkdir(parents=True, exist_ok=True)
    
    def get_changes_filename(self, change_date: Optional[date] = None) -> Path:
        """
        Get changes filename for a given date.
        
        Args:
            change_date: Date for changes file (default: today)
        
        Returns:
            Path to changes file
        """
        if change_date is None:
            change_date = datetime.now().date()
        
        filename = f"changes_{change_date.strftime('%Y-%m-%d')}.csv"
        return self.changes_dir / filename
    
    def detect_changes(self) -> bool:
        """
        Detect changes between today and yesterday's snapshot.
        
        Returns:
            Success status
        """
        try:
            logger.info("=" * 60)
            logger.info("CHANGE DETECTION")
            logger.info("=" * 60)
            
            # Get today's snapshot
            today = datetime.now().date()
            today_df = self.snapshot_manager.get_snapshot_by_date(today)
            
            if today_df is None or today_df.empty:
                logger.error("Today's snapshot not found or empty")
                logger.info("Run 'python main.py snapshot' first")
                return False
            
            logger.info(f"Today's snapshot: {len(today_df):,} records")
            
            # Get yesterday's snapshot
            yesterday = today - timedelta(days=1)
            yesterday_df = self.snapshot_manager.get_snapshot_by_date(yesterday)
            
            if yesterday_df is None or yesterday_df.empty:
                logger.warning("Yesterday's snapshot not found, treating all as new")
                changes_df = self._mark_all_as_new(today_df)
            else:
                logger.info(f"Yesterday's snapshot: {len(yesterday_df):,} records")
                # Compare snapshots
                changes_df = self._compare_snapshots(yesterday_df, today_df)
            
            if changes_df.empty:
                logger.info("No changes detected")
                return True
            
            logger.info(f"Detected {len(changes_df):,} changes")
            
            # Save changes to CSV
            changes_file = self.get_changes_filename()
            changes_df.to_csv(changes_file, index=False)
            logger.info(f"[OK] Changes saved to {changes_file}")
            
            # Save to database
            change_logs = self._prepare_change_logs(changes_df, today)
            success, saved_count = self.db_ops.save_changes(change_logs)
            
            if success:
                logger.info(f"[OK] Saved {saved_count} changes to database")
            
            logger.info("=" * 60)
            logger.info("[OK] CHANGE DETECTION COMPLETED")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Error detecting changes: {e}", exc_info=True)
            return False
    
    def _mark_all_as_new(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mark all records as new.
        
        Args:
            df: DataFrame with company data
        
        Returns:
            DataFrame with change_type column
        """
        df = df.copy()
        df['change_type'] = 'NEW'
        df['changed_fields'] = None
        df['old_values'] = None
        df['new_values'] = None
        
        logger.info(f"Marked {len(df):,} records as NEW")
        return df
    
    def _compare_snapshots(self, old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compare two snapshots and identify changes.
        
        Args:
            old_df: Yesterday's dataframe
            new_df: Today's dataframe
        
        Returns:
            DataFrame with changes
        """
        changes = []
        
        # Ensure CIN column exists
        if self.key_column not in old_df.columns or self.key_column not in new_df.columns:
            logger.error(f"Key column '{self.key_column}' not found in snapshots")
            return pd.DataFrame()
        
        # Create sets for quick lookup
        old_cins = set(old_df[self.key_column].dropna())
        new_cins = set(new_df[self.key_column].dropna())
        
        logger.info("Analyzing changes...")
        
        # Find new companies
        new_companies = new_cins - old_cins
        for cin in new_companies:
            try:
                record = new_df[new_df[self.key_column] == cin].iloc[0].to_dict()
                record['change_type'] = 'NEW'
                record['changed_fields'] = None
                record['old_values'] = None
                record['new_values'] = None
                changes.append(record)
            except Exception as e:
                logger.warning(f"Error processing new company {cin}: {e}")
        
        logger.info(f"Found {len(new_companies):,} new companies")
        
        # Find deleted companies
        deleted_companies = old_cins - new_cins
        for cin in deleted_companies:
            try:
                record = old_df[old_df[self.key_column] == cin].iloc[0].to_dict()
                record['change_type'] = 'DELETED'
                record['changed_fields'] = None
                record['old_values'] = None
                record['new_values'] = None
                changes.append(record)
            except Exception as e:
                logger.warning(f"Error processing deleted company {cin}: {e}")
        
        logger.info(f"Found {len(deleted_companies):,} deleted companies")
        
        # Find modified companies
        common_cins = old_cins & new_cins
        modified_count = 0
        
        # Process in batches to show progress
        batch_size = 10000
        total_batches = (len(common_cins) + batch_size - 1) // batch_size
        
        logger.info(f"Checking {len(common_cins):,} companies for modifications...")
        
        common_cins_list = list(common_cins)
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(common_cins_list))
            batch_cins = common_cins_list[start_idx:end_idx]
            
            for cin in batch_cins:
                try:
                    old_record = old_df[old_df[self.key_column] == cin].iloc[0]
                    new_record = new_df[new_df[self.key_column] == cin].iloc[0]
                    
                    changed_fields = []
                    old_values = {}
                    new_values = {}
                    
                    # Compare all columns except metadata
                    for column in new_df.columns:
                        if column in [self.key_column, 'snapshot_date', 'snapshot_timestamp']:
                            continue
                        
                        old_value = old_record.get(column)
                        new_value = new_record.get(column)
                        
                        # Compare values (handling NaN)
                        if pd.isna(old_value) and pd.isna(new_value):
                            continue
                        
                        if old_value != new_value:
                            changed_fields.append(column)
                            old_values[column] = str(old_value) if not pd.isna(old_value) else None
                            new_values[column] = str(new_value) if not pd.isna(new_value) else None
                    
                    if changed_fields:
                        record = new_record.to_dict()
                        record['change_type'] = 'MODIFIED'
                        record['changed_fields'] = json.dumps(changed_fields)
                        record['old_values'] = json.dumps(old_values)
                        record['new_values'] = json.dumps(new_values)
                        changes.append(record)
                        modified_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error comparing company {cin}: {e}")
            
            if (batch_idx + 1) % 10 == 0:
                logger.info(f"Processed {end_idx:,} / {len(common_cins):,} companies...")
        
        logger.info(f"Found {modified_count:,} modified companies")
        
        return pd.DataFrame(changes) if changes else pd.DataFrame()
    
    def _prepare_change_logs(self, changes_df: pd.DataFrame, change_date: date) -> List[Dict]:
        """
        Prepare change logs for database insertion.
        
        Args:
            changes_df: Changes dataframe
            change_date: Date of changes
        
        Returns:
            List of change log dictionaries
        """
        logs = []
        
        for _, row in changes_df.iterrows():
            try:
                # Parse JSON fields if they exist and are strings
                changed_fields = None
                old_values = None
                new_values = None
                
                if pd.notna(row.get('changed_fields')):
                    try:
                        changed_fields = json.loads(row['changed_fields']) if isinstance(row['changed_fields'], str) else row['changed_fields']
                    except:
                        pass
                
                if pd.notna(row.get('old_values')):
                    try:
                        old_values = json.loads(row['old_values']) if isinstance(row['old_values'], str) else row['old_values']
                    except:
                        pass
                
                if pd.notna(row.get('new_values')):
                    try:
                        new_values = json.loads(row['new_values']) if isinstance(row['new_values'], str) else row['new_values']
                    except:
                        pass
                
                log = {
                    'cin': str(row.get(self.key_column, '')),
                    'company_name': str(row.get('company_name', ''))[:500] if pd.notna(row.get('company_name')) else None,
                    'change_type': str(row.get('change_type', 'UNKNOWN')),
                    'change_date': change_date,
                    'changed_fields': changed_fields,
                    'old_values': old_values,
                    'new_values': new_values
                }
                logs.append(log)
                
            except Exception as e:
                logger.warning(f"Error preparing change log: {e}")
                continue
        
        return logs
    
    def get_changes_summary(self, days: int = 7) -> Dict:
        """
        Get summary of changes for the last N days.
        Uses CSV files directly if database is empty.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Summary dictionary with change statistics
        """
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            end_date = datetime.now().date()
            
            logger.info(f"Getting changes summary for {days} days ({start_date} to {end_date})")
            
            # Try database first
            changes = self.db_ops.get_changes_by_date_range(start_date, end_date)
            
            # If database is empty, load from CSV files
            if not changes:
                logger.info("Database empty, loading changes from CSV files")
                changes = self._load_changes_from_csv(start_date, end_date)
            
            # Build summary
            summary = {
                'total_changes': len(changes),
                'new': 0,
                'modified': 0,
                'deleted': 0,
                'by_date': {}
            }
            
            for change in changes:
                change_type = str(change.get('change_type', 'UNKNOWN'))
                
                # Count by type
                if change_type == 'NEW':
                    summary['new'] += 1
                elif change_type == 'MODIFIED':
                    summary['modified'] += 1
                elif change_type == 'DELETED':
                    summary['deleted'] += 1
                
                # Count by date
                change_date = change.get('change_date')
                if change_date:
                    # Handle both string and datetime objects
                    if hasattr(change_date, 'date'):
                        date_str = str(change_date.date())
                    elif hasattr(change_date, 'strftime'):
                        date_str = change_date.strftime('%Y-%m-%d')
                    else:
                        date_str = str(change_date).split()[0] if change_date else ''
                    
                    if date_str:
                        if date_str not in summary['by_date']:
                            summary['by_date'][date_str] = {'NEW': 0, 'MODIFIED': 0, 'DELETED': 0}
                        summary['by_date'][date_str][change_type] = summary['by_date'][date_str].get(change_type, 0) + 1
            
            logger.info(f"[OK] Changes summary: {summary['total_changes']:,} total changes")
            return summary
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting changes summary: {e}", exc_info=True)
            return {
                'total_changes': 0,
                'new': 0,
                'modified': 0,
                'deleted': 0,
                'by_date': {}
            }
    
    def _load_changes_from_csv(self, start_date: date, end_date: date) -> List[Dict]:
        """
        Load changes from CSV files within date range.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            List of change dictionaries
        """
        all_changes = []
        
        try:
            change_files = list(self.changes_dir.glob("changes_*.csv"))
            
            if not change_files:
                logger.warning("No change files found")
                return []
            
            logger.info(f"Loading changes from {len(change_files)} CSV file(s)")
            
            for file in change_files:
                try:
                    # Extract date from filename (format: changes_YYYY-MM-DD.csv)
                    date_str = file.stem.replace('changes_', '')
                    file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Skip files outside date range
                    if file_date < start_date or file_date > end_date:
                        continue
                    
                    # Read CSV
                    df = pd.read_csv(file, low_memory=False)
                    
                    if df.empty:
                        continue
                    
                    # Convert to dictionaries
                    for _, row in df.iterrows():
                        change = {
                            'change_date': file_date,
                            'change_type': row.get('change_type', 'UNKNOWN'),
                            'company_name': row.get('company_name'),
                            'cin': row.get('cin'),
                            'changed_fields': row.get('changed_fields'),
                            'old_values': row.get('old_values'),
                            'new_values': row.get('new_values')
                        }
                        all_changes.append(change)
                    
                    logger.info(f"Loaded {len(df):,} changes from {file.name}")
                    
                except Exception as e:
                    logger.error(f"Error reading {file.name}: {e}")
                    continue
            
            logger.info(f"[OK] Loaded {len(all_changes):,} total changes from CSV")
            return all_changes
            
        except Exception as e:
            logger.error(f"Error loading changes from CSV: {e}")
            return []
    
    def get_changes_by_company(self, cin: str) -> List[Dict]:
        """
        Get all changes for a specific company.
        
        Args:
            cin: Company CIN
        
        Returns:
            List of changes for the company
        """
        try:
            # Try database first
            changes = self.db_ops.get_changes_by_cin(cin)
            
            if changes:
                return changes
            
            # Fallback to CSV files
            logger.info(f"Loading changes for {cin} from CSV files")
            return self._load_changes_for_cin_from_csv(cin)
            
        except Exception as e:
            logger.error(f"Error getting changes for company: {e}")
            return []
    
    def _load_changes_for_cin_from_csv(self, cin: str) -> List[Dict]:
        """
        Load changes for specific CIN from CSV files.
        
        Args:
            cin: Company CIN
        
        Returns:
            List of changes
        """
        company_changes = []
        
        try:
            change_files = list(self.changes_dir.glob("changes_*.csv"))
            
            for file in change_files:
                try:
                    df = pd.read_csv(file, low_memory=False)
                    
                    # Filter by CIN
                    matches = df[df['cin'] == cin]
                    
                    if not matches.empty:
                        date_str = file.stem.replace('changes_', '')
                        file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        for _, row in matches.iterrows():
                            company_changes.append({
                                'change_date': file_date,
                                'change_type': row.get('change_type'),
                                'company_name': row.get('company_name'),
                                'cin': row.get('cin'),
                                'changed_fields': row.get('changed_fields'),
                                'old_values': row.get('old_values'),
                                'new_values': row.get('new_values')
                            })
                except:
                    continue
            
            return company_changes
            
        except Exception as e:
            logger.error(f"Error loading changes for CIN from CSV: {e}")
            return []
    
    def get_latest_changes(self, limit: int = 50) -> List[Dict]:
        """
        Get most recent changes.
        
        Args:
            limit: Maximum number of changes to return
        
        Returns:
            List of recent changes
        """
        try:
            # Try database first
            changes = self.db_ops.get_recent_changes(limit)
            
            if changes:
                return changes
            
            # Fallback to latest CSV file
            change_files = sorted(self.changes_dir.glob("changes_*.csv"), reverse=True)
            
            if not change_files:
                return []
            
            latest_file = change_files[0]
            df = pd.read_csv(latest_file, low_memory=False)
            
            return df.head(limit).to_dict('records')
            
        except Exception as e:
            logger.error(f"Error getting latest changes: {e}")
            return []
    
    def clear_old_changes(self, keep_days: int = 30) -> int:
        """
        Delete old change files.
        
        Args:
            keep_days: Number of days to keep
        
        Returns:
            Number of files deleted
        """
        try:
            cutoff_date = datetime.now().date() - timedelta(days=keep_days)
            deleted = 0
            
            for file in self.changes_dir.glob("changes_*.csv"):
                try:
                    date_str = file.stem.replace('changes_', '')
                    file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    if file_date < cutoff_date:
                        file.unlink()
                        deleted += 1
                        logger.info(f"Deleted old change file: {file.name}")
                        
                except Exception as e:
                    logger.warning(f"Error processing {file.name}: {e}")
                    continue
            
            logger.info(f"[OK] Deleted {deleted} old change files")
            return deleted
            
        except Exception as e:
            logger.error(f"Error clearing old changes: {e}")
            return 0
    
    def __repr__(self) -> str:
        """String representation."""
        change_files = list(self.changes_dir.glob("changes_*.csv"))
        return f"ChangeDetector(change_files={len(change_files)})"