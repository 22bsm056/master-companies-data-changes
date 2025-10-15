"""Hybrid search system - Fast pandas-based search with AI capabilities."""
import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from config.settings import Settings
from src.database.operations import DatabaseOperations
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class HybridSearch:
    """Fast hybrid search using pandas DataFrames + Database."""
    
    def __init__(self):
        """Initialize hybrid search system."""
        self.db_ops = DatabaseOperations()
        self.snapshot_dir = Settings.SNAPSHOT_DIR
        self.changes_dir = Settings.CHANGES_DIR
        
        # In-memory dataframes for fast searching
        self.companies_df: Optional[pd.DataFrame] = None
        self.changes_df: Optional[pd.DataFrame] = None
        
        # Load data
        self._load_data()
    
    def _load_data(self):
        """Load data into memory for fast searching."""
        try:
            logger.info("=" * 60)
            logger.info("LOADING DATA INTO MEMORY")
            logger.info("=" * 60)
            
            # Load latest snapshot
            snapshot_files = sorted(self.snapshot_dir.glob("snapshot_*.csv"))
            if snapshot_files:
                latest_file = snapshot_files[-1]
                logger.info(f"Loading: {latest_file.name}")
                
                self.companies_df = pd.read_csv(
                    latest_file,
                    low_memory=False
                )
                
                # Create search columns (lowercase for case-insensitive search)
                self.companies_df['search_name'] = self.companies_df['company_name'].fillna('').str.lower()
                self.companies_df['search_cin'] = self.companies_df['cin'].fillna('').str.lower()
                self.companies_df['search_category'] = self.companies_df['company_category'].fillna('').str.lower()
                
                logger.info(f"[OK] Loaded {len(self.companies_df):,} companies")
            else:
                logger.warning("[WARN] No snapshot files found")
            
            # Load all changes
            change_files = list(self.changes_dir.glob("changes_*.csv"))
            if change_files:
                logger.info(f"Loading {len(change_files)} change file(s)...")
                
                dfs = []
                for change_file in change_files:
                    df = pd.read_csv(change_file, low_memory=False)
                    dfs.append(df)
                
                self.changes_df = pd.concat(dfs, ignore_index=True)
                
                # Create search columns
                self.changes_df['search_name'] = self.changes_df['company_name'].fillna('').str.lower()
                self.changes_df['search_cin'] = self.changes_df['cin'].fillna('').str.lower()
                
                logger.info(f"[OK] Loaded {len(self.changes_df):,} changes")
            else:
                logger.warning("[WARN] No change files found")
            
            logger.info("=" * 60)
            logger.info("[OK] DATA LOADED SUCCESSFULLY")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"[ERROR] Error loading data: {e}")
    
    def search_companies(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Fast company search using pandas.
        
        Args:
            query: Search query
            limit: Maximum results
        
        Returns:
            List of matching companies
        """
        if self.companies_df is None or self.companies_df.empty:
            logger.warning("No company data available")
            return []
        
        try:
            query_lower = query.lower()
            
            # Multi-field search
            mask = (
                self.companies_df['search_name'].str.contains(query_lower, na=False) |
                self.companies_df['search_cin'].str.contains(query_lower, na=False) |
                self.companies_df['search_category'].str.contains(query_lower, na=False)
            )
            
            results_df = self.companies_df[mask].head(limit)
            
            # Format results
            results = []
            for _, row in results_df.iterrows():
                # Create readable document
                doc_text = self._format_company_document(row)
                
                results.append({
                    'document': doc_text,
                    'metadata': {
                        'cin': str(row.get('cin', '')),
                        'company_name': str(row.get('company_name', '')),
                        'company_status': str(row.get('company_status', '')),
                        'company_category': str(row.get('company_category', ''))
                    },
                    'distance': 0,
                    'raw_data': row.to_dict()
                })
            
            logger.info(f"Found {len(results)} companies for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []
    
    def search_changes(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Fast changes search using pandas.
        
        Args:
            query: Search query
            limit: Maximum results
        
        Returns:
            List of matching changes
        """
        if self.changes_df is None or self.changes_df.empty:
            logger.warning("No changes data available")
            return []
        
        try:
            query_lower = query.lower()
            
            # Search in name and CIN
            mask = (
                self.changes_df['search_name'].str.contains(query_lower, na=False) |
                self.changes_df['search_cin'].str.contains(query_lower, na=False)
            )
            
            results_df = self.changes_df[mask].head(limit)
            
            # Format results
            results = []
            for _, row in results_df.iterrows():
                doc_text = self._format_change_document(row)
                
                results.append({
                    'document': doc_text,
                    'metadata': {
                        'cin': str(row.get('cin', '')),
                        'company_name': str(row.get('company_name', '')),
                        'change_type': str(row.get('change_type', '')),
                        'change_date': str(row.get('change_date', ''))
                    },
                    'distance': 0,
                    'raw_data': row.to_dict()
                })
            
            logger.info(f"Found {len(results)} changes for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching changes: {e}")
            return []
    
    def get_company_by_cin(self, cin: str) -> Optional[Dict]:
        """
        Get company by exact CIN match.
        
        Args:
            cin: Company CIN
        
        Returns:
            Company data or None
        """
        if self.companies_df is None:
            return None
        
        try:
            # Try database first (more reliable)
            db_result = self.db_ops.get_company_by_cin(cin)
            if db_result:
                return db_result
            
            # Fallback to dataframe
            result = self.companies_df[self.companies_df['cin'] == cin]
            
            if not result.empty:
                row = result.iloc[0]
                doc_text = self._format_company_document(row)
                
                return {
                    'document': doc_text,
                    'metadata': {
                        'cin': str(row.get('cin', '')),
                        'company_name': str(row.get('company_name', ''))
                    },
                    'raw_data': row.to_dict()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting company by CIN: {e}")
            return None
    
    def get_changes_by_cin(self, cin: str) -> List[Dict]:
        """
        Get all changes for a specific company.
        
        Args:
            cin: Company CIN
        
        Returns:
            List of changes
        """
        # Try database first
        db_changes = self.db_ops.get_changes_by_cin(cin)
        if db_changes:
            return db_changes
        
        # Fallback to dataframe
        if self.changes_df is None or self.changes_df.empty:
            return []
        
        try:
            results = self.changes_df[self.changes_df['cin'] == cin]
            
            changes = []
            for _, row in results.iterrows():
                changes.append({
                    'cin': str(row.get('cin', '')),
                    'company_name': str(row.get('company_name', '')),
                    'change_type': str(row.get('change_type', '')),
                    'change_date': str(row.get('change_date', '')),
                    'changed_fields': row.get('changed_fields'),
                    'old_values': row.get('old_values'),
                    'new_values': row.get('new_values')
                })
            
            return changes
            
        except Exception as e:
            logger.error(f"Error getting changes by CIN: {e}")
            return []
    
    def _format_company_document(self, row: pd.Series) -> str:
        """Format company data as readable document."""
        parts = [
            f"Company Information:",
            f"- CIN: {row.get('cin', 'N/A')}",
            f"- Name: {row.get('company_name', 'N/A')}",
            f"- Status: {row.get('company_status', 'N/A')}",
            f"- Category: {row.get('company_category', 'N/A')}",
            f"- Sub-Category: {row.get('company_sub_category', 'N/A')}",
            f"- Class: {row.get('company_class', 'N/A')}",
            f"- Registration Date: {row.get('registration_date', 'N/A')}",
            f"- State: {row.get('company_state_code', 'N/A')}",
            f"- ROC: {row.get('company_roc_code', 'N/A')}"
        ]
        
        # Add capital info if available
        if pd.notna(row.get('authorized_capital')):
            parts.append(f"- Authorized Capital: {row.get('authorized_capital')}")
        if pd.notna(row.get('paidup_capital')):
            parts.append(f"- Paid-up Capital: {row.get('paidup_capital')}")
        
        return "\n".join(parts)
    
    def _format_change_document(self, row: pd.Series) -> str:
        """Format change data as readable document."""
        parts = [
            f"Change Record:",
            f"- Company: {row.get('company_name', 'N/A')} ({row.get('cin', 'N/A')})",
            f"- Change Type: {row.get('change_type', 'N/A')}",
            f"- Date: {row.get('change_date', 'N/A')}"
        ]
        
        # Add changed fields if available
        if pd.notna(row.get('changed_fields')):
            try:
                fields = json.loads(row['changed_fields']) if isinstance(row['changed_fields'], str) else row['changed_fields']
                parts.append(f"- Changed Fields: {', '.join(fields)}")
            except:
                pass
        
        return "\n".join(parts)
    
    def get_statistics(self) -> Dict:
        """Get quick statistics."""
        stats = {
            'total_companies': len(self.companies_df) if self.companies_df is not None else 0,
            'total_changes': len(self.changes_df) if self.changes_df is not None else 0
        }
        
        if self.companies_df is not None:
            stats['active_companies'] = len(
                self.companies_df[self.companies_df['company_status'] == 'Active']
            )
        
        return stats
    
    def reload_data(self):
        """Reload data from disk."""
        logger.info("Reloading data...")
        self._load_data()
    
    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_statistics()
        return (
            f"HybridSearch(\n"
            f"  companies: {stats['total_companies']:,},\n"
            f"  changes: {stats['total_changes']:,}\n"
            f")"
        )