"""Helper utilities."""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List
import pandas as pd

def calculate_hash(data: str) -> str:
    """Calculate MD5 hash of data."""
    return hashlib.md5(data.encode()).hexdigest()

def serialize_data(data: Any) -> str:
    """Serialize data to JSON string."""
    return json.dumps(data, default=str, sort_keys=True)

def get_date_range(days: int) -> tuple:
    """
    Get date range for last N days.
    
    Args:
        days: Number of days
    
    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date

def format_date(date: datetime, format: str = "%Y-%m-%d") -> str:
    """Format datetime to string."""
    return date.strftime(format)

def parse_date(date_str: str, format: str = "%Y-%m-%d") -> datetime:
    """Parse string to datetime."""
    return datetime.strptime(date_str, format)

def compare_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, key_column: str) -> pd.DataFrame:
    """
    Compare two dataframes and return differences.
    
    Args:
        df1: First dataframe (old data)
        df2: Second dataframe (new data)
        key_column: Column to use as key for comparison
    
    Returns:
        DataFrame with changes
    """
    changes = []
    
    # Merge dataframes
    merged = pd.merge(
        df1, df2,
        on=key_column,
        how='outer',
        suffixes=('_old', '_new'),
        indicator=True
    )
    
    for _, row in merged.iterrows():
        if row['_merge'] == 'right_only':
            # New company
            changes.append({
                'change_type': 'NEW',
                'key': row[key_column],
                **{col: row[f"{col}_new"] for col in df2.columns if col != key_column}
            })
        elif row['_merge'] == 'left_only':
            # Deleted company
            changes.append({
                'change_type': 'DELETED',
                'key': row[key_column],
                **{col: row[f"{col}_old"] for col in df1.columns if col != key_column}
            })
        else:
            # Check for modifications
            modified_fields = []
            for col in df1.columns:
                if col == key_column:
                    continue
                old_val = row.get(f"{col}_old")
                new_val = row.get(f"{col}_new")
                if old_val != new_val and not (pd.isna(old_val) and pd.isna(new_val)):
                    modified_fields.append({
                        'field': col,
                        'old_value': old_val,
                        'new_value': new_val
                    })
            
            if modified_fields:
                changes.append({
                    'change_type': 'MODIFIED',
                    'key': row[key_column],
                    'changes': modified_fields,
                    **{col: row[f"{col}_new"] for col in df2.columns if col != key_column}
                })
    
    return pd.DataFrame(changes) if changes else pd.DataFrame()