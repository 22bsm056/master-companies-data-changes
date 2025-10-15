"""Enhanced data indexing script with progress tracking."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from tqdm import tqdm
from src.agents.rag_system import RAGSystem
from src.utils.logger import setup_logger
from config.settings import Settings

logger = setup_logger("indexing")

def index_with_progress():
    """Index data with progress bars."""
    logger.info("Starting enhanced indexing...")
    
    rag = RAGSystem()
    
    # Index snapshots
    logger.info("Indexing snapshots...")
    snapshot_files = sorted(Settings.SNAPSHOT_DIR.glob("snapshot_*.csv"))
    
    for snapshot_file in tqdm(snapshot_files, desc="Snapshots"):
        try:
            logger.info(f"Processing {snapshot_file.name}")
            df = pd.read_csv(snapshot_file, low_memory=False)
            
            # Process in chunks for large files
            chunk_size = 1000
            for i in tqdm(range(0, len(df), chunk_size), desc=f"  {snapshot_file.name}", leave=False):
                chunk = df.iloc[i:i+chunk_size]
                rag._index_dataframe(chunk, rag.companies_collection, 'snapshot')
                
            logger.info(f"✓ Indexed {len(df)} records from {snapshot_file.name}")
            
        except Exception as e:
            logger.error(f"✗ Error indexing {snapshot_file.name}: {e}")
    
    # Index changes
    logger.info("Indexing changes...")
    change_files = sorted(Settings.CHANGES_DIR.glob("changes_*.csv"))
    
    for change_file in tqdm(change_files, desc="Changes"):
        try:
            logger.info(f"Processing {change_file.name}")
            df = pd.read_csv(change_file, low_memory=False)
            rag._index_dataframe(df, rag.changes_collection, 'change')
            logger.info(f"✓ Indexed {len(df)} changes from {change_file.name}")
            
        except Exception as e:
            logger.error(f"✗ Error indexing {change_file.name}: {e}")
    
    logger.info("✓ Indexing completed successfully!")

if __name__ == "__main__":
    try:
        index_with_progress()
    except KeyboardInterrupt:
        logger.warning("Indexing interrupted by user")
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)