"""RAG (Retrieval Augmented Generation) system for querying company data."""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import pandas as pd
from sentence_transformers import SentenceTransformer
import chromadb
from tqdm import tqdm
from config.settings import Settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# ASCII-compatible symbols for Windows
SYMBOLS = {
    'success': '[OK]',
    'error': '[ERROR]',
    'warning': '[WARN]',
    'skip': '[SKIP]',
    'info': '[INFO]'
}


class RAGSystem:
    """RAG system for document retrieval and querying with ChromaDB."""
    
    def __init__(self):
        """Initialize RAG system."""
        self.embeddings_dir = Settings.EMBEDDINGS_DIR
        self.snapshot_dir = Settings.SNAPSHOT_DIR
        self.changes_dir = Settings.CHANGES_DIR
        
        # Ensure directories exist
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        self.embedding_model = None
        self._init_embedding_model()
        
        # Initialize ChromaDB client
        self.client = None
        self.companies_collection = None
        self.changes_collection = None
        self._init_chromadb()
        
        # Track indexed files
        self.indexed_files: Set[str] = set()
    
    def _init_embedding_model(self):
        """Initialize sentence transformer model."""
        try:
            logger.info("Loading embedding model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info(f"{SYMBOLS['success']} Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"{SYMBOLS['error']} Could not load embedding model: {e}")
            logger.warning("RAG system will work with reduced functionality")
    
    def _init_chromadb(self):
        """Initialize ChromaDB client and collections."""
        try:
            logger.info("Initializing ChromaDB...")
            
            # Use PersistentClient with new API
            self.client = chromadb.PersistentClient(
                path=str(self.embeddings_dir)
            )
            logger.info(f"{SYMBOLS['success']} ChromaDB initialized at {self.embeddings_dir}")
            
            # Create or get collections
            self.companies_collection = self.client.get_or_create_collection(
                name="companies",
                metadata={
                    "description": "Company data embeddings",
                    "created_at": datetime.now().isoformat()
                }
            )
            
            self.changes_collection = self.client.get_or_create_collection(
                name="changes",
                metadata={
                    "description": "Change logs embeddings",
                    "created_at": datetime.now().isoformat()
                }
            )
            
            logger.info(f"{SYMBOLS['success']} Collections created/loaded successfully")
            self._log_collection_stats()
            
        except Exception as e:
            logger.error(f"{SYMBOLS['error']} Error initializing ChromaDB: {e}")
            # Fallback to ephemeral client
            try:
                self.client = chromadb.EphemeralClient()
                logger.warning(f"{SYMBOLS['warning']} Using ephemeral ChromaDB client (data will not persist)")
                
                self.companies_collection = self.client.get_or_create_collection(
                    name="companies",
                    metadata={"description": "Company data embeddings"}
                )
                
                self.changes_collection = self.client.get_or_create_collection(
                    name="changes",
                    metadata={"description": "Change logs embeddings"}
                )
            except Exception as fallback_error:
                logger.error(f"{SYMBOLS['error']} Fallback initialization failed: {fallback_error}")
                self.companies_collection = None
                self.changes_collection = None
    
    def _log_collection_stats(self):
        """Log statistics about collections."""
        try:
            if self.companies_collection:
                companies_count = self.companies_collection.count()
                logger.info(f"  Companies collection: {companies_count:,} documents")
            
            if self.changes_collection:
                changes_count = self.changes_collection.count()
                logger.info(f"  Changes collection: {changes_count:,} documents")
        except Exception as e:
            logger.warning(f"Could not retrieve collection stats: {e}")
    
    def index_snapshots(self, force_reindex: bool = False, chunk_size: int = 1000):
        """
        Index all snapshot files.
        
        Args:
            force_reindex: If True, reindex even if already indexed
            chunk_size: Number of rows to process at once
        """
        if not self.companies_collection:
            logger.error(f"{SYMBOLS['error']} Companies collection not initialized")
            return
        
        try:
            logger.info("=" * 60)
            logger.info("SNAPSHOT INDEXING")
            logger.info("=" * 60)
            
            snapshot_files = sorted(self.snapshot_dir.glob("snapshot_*.csv"))
            
            if not snapshot_files:
                logger.warning(f"{SYMBOLS['warning']} No snapshot files found")
                return
            
            logger.info(f"Found {len(snapshot_files)} snapshot file(s)")
            
            total_indexed = 0
            
            for snapshot_file in snapshot_files:
                file_key = f"snapshot_{snapshot_file.name}"
                
                if file_key in self.indexed_files and not force_reindex:
                    logger.info(f"{SYMBOLS['skip']} Skipping {snapshot_file.name} (already indexed)")
                    continue
                
                logger.info(f"\nProcessing: {snapshot_file.name}")
                
                try:
                    # Read CSV with low_memory=False to avoid dtype warnings
                    df = pd.read_csv(snapshot_file, low_memory=False)
                    logger.info(f"  Loaded {len(df):,} records")
                    
                    # Index in chunks
                    indexed_count = self._index_dataframe_chunked(
                        df, 
                        self.companies_collection, 
                        'snapshot',
                        chunk_size=chunk_size,
                        file_name=snapshot_file.name
                    )
                    
                    total_indexed += indexed_count
                    self.indexed_files.add(file_key)
                    logger.info(f"  {SYMBOLS['success']} Indexed {indexed_count:,} documents")
                    
                except Exception as e:
                    logger.error(f"  {SYMBOLS['error']} Error indexing {snapshot_file.name}: {e}")
            
            logger.info("=" * 60)
            logger.info(f"{SYMBOLS['success']} SNAPSHOT INDEXING COMPLETED")
            logger.info(f"  Total indexed: {total_indexed:,} documents")
            logger.info("=" * 60)
            self._log_collection_stats()
            
        except Exception as e:
            logger.error(f"{SYMBOLS['error']} Error in snapshot indexing: {e}")
    
    def index_changes(self, force_reindex: bool = False, chunk_size: int = 500):
        """
        Index all change files.
        
        Args:
            force_reindex: If True, reindex even if already indexed
            chunk_size: Number of rows to process at once
        """
        if not self.changes_collection:
            logger.error(f"{SYMBOLS['error']} Changes collection not initialized")
            return
        
        try:
            logger.info("=" * 60)
            logger.info("CHANGES INDEXING")
            logger.info("=" * 60)
            
            change_files = sorted(self.changes_dir.glob("changes_*.csv"))
            
            if not change_files:
                logger.warning(f"{SYMBOLS['warning']} No change files found")
                return
            
            logger.info(f"Found {len(change_files)} change file(s)")
            
            total_indexed = 0
            
            for change_file in change_files:
                file_key = f"change_{change_file.name}"
                
                if file_key in self.indexed_files and not force_reindex:
                    logger.info(f"{SYMBOLS['skip']} Skipping {change_file.name} (already indexed)")
                    continue
                
                logger.info(f"\nProcessing: {change_file.name}")
                
                try:
                    # Read CSV with low_memory=False
                    df = pd.read_csv(change_file, low_memory=False)
                    logger.info(f"  Loaded {len(df):,} records")
                    
                    # Index in chunks
                    indexed_count = self._index_dataframe_chunked(
                        df, 
                        self.changes_collection, 
                        'change',
                        chunk_size=chunk_size,
                        file_name=change_file.name
                    )
                    
                    total_indexed += indexed_count
                    self.indexed_files.add(file_key)
                    logger.info(f"  {SYMBOLS['success']} Indexed {indexed_count:,} documents")
                    
                except Exception as e:
                    logger.error(f"  {SYMBOLS['error']} Error indexing {change_file.name}: {e}")
            
            logger.info("=" * 60)
            logger.info(f"{SYMBOLS['success']} CHANGES INDEXING COMPLETED")
            logger.info(f"  Total indexed: {total_indexed:,} documents")
            logger.info("=" * 60)
            self._log_collection_stats()
            
        except Exception as e:
            logger.error(f"{SYMBOLS['error']} Error in changes indexing: {e}")
    
    def _index_dataframe_chunked(
        self, 
        df: pd.DataFrame, 
        collection, 
        doc_type: str,
        chunk_size: int = 1000,
        file_name: str = ""
    ) -> int:
        """
        Index a dataframe in chunks to handle large files.
        
        Args:
            df: DataFrame to index
            collection: ChromaDB collection
            doc_type: Type of document ('snapshot' or 'change')
            chunk_size: Number of rows per chunk
            file_name: Name of source file for logging
        
        Returns:
            Number of documents indexed
        """
        if collection is None:
            logger.error(f"  {SYMBOLS['error']} Collection is None, cannot index")
            return 0
        
        total_indexed = 0
        total_chunks = (len(df) + chunk_size - 1) // chunk_size
        
        # Process in chunks with progress bar
        for i in tqdm(
            range(0, len(df), chunk_size), 
            desc=f"  Indexing {file_name}",
            unit="chunk",
            total=total_chunks,
            ncols=80,
            ascii=True  # Use ASCII characters for progress bar on Windows
        ):
            chunk = df.iloc[i:i + chunk_size]
            indexed = self._index_dataframe(chunk, collection, doc_type, start_idx=i)
            total_indexed += indexed
        
        return total_indexed
    
    def _index_dataframe(
        self, 
        df: pd.DataFrame, 
        collection, 
        doc_type: str,
        start_idx: int = 0
    ) -> int:
        """
        Index a dataframe into a collection.
        
        Args:
            df: DataFrame to index
            collection: ChromaDB collection
            doc_type: Type of document
            start_idx: Starting index for ID generation
        
        Returns:
            Number of documents successfully indexed
        """
        if collection is None:
            return 0
        
        try:
            documents = []
            metadatas = []
            ids = []
            
            for idx, row in df.iterrows():
                # Create document text
                doc_text = self._row_to_text(row)
                
                if not doc_text or len(doc_text.strip()) == 0:
                    continue
                
                documents.append(doc_text)
                
                # Create metadata (ensure all values are valid types)
                metadata = self._create_metadata(row, doc_type)
                metadatas.append(metadata)
                
                # Create unique ID using hash to avoid duplicates
                unique_id = self._generate_unique_id(row, doc_type, start_idx + idx)
                ids.append(unique_id)
            
            if not documents:
                return 0
            
            # Add to collection in batches
            batch_size = 100
            indexed_count = 0
            
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_metas = metadatas[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                
                try:
                    collection.upsert(  # Use upsert instead of add to handle duplicates
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    indexed_count += len(batch_docs)
                except Exception as e:
                    logger.error(f"    {SYMBOLS['error']} Error adding batch {i}-{i+batch_size}: {e}")
            
            return indexed_count
            
        except Exception as e:
            logger.error(f"  {SYMBOLS['error']} Error indexing dataframe: {e}")
            return 0
    
    def _row_to_text(self, row: pd.Series) -> str:
        """Convert dataframe row to text for embedding."""
        text_parts = []
        
        # Priority fields for better search
        priority_fields = ['cin', 'company_name', 'company_status', 'company_category']
        
        # Add priority fields first
        for field in priority_fields:
            if field in row.index and pd.notna(row[field]) and str(row[field]).strip():
                value_str = str(row[field])[:500]
                text_parts.append(f"{field}: {value_str}")
        
        # Add other fields
        for column, value in row.items():
            if column in priority_fields:
                continue
            
            if pd.notna(value) and str(value).strip():
                value_str = str(value)[:300]
                text_parts.append(f"{column}: {value_str}")
        
        return " | ".join(text_parts)
    
    def _create_metadata(self, row: pd.Series, doc_type: str) -> Dict:
        """Create metadata dictionary for ChromaDB."""
        metadata = {
            'type': str(doc_type),
            'indexed_at': datetime.now().isoformat()
        }
        
        # Add key fields as metadata
        key_fields = {
            'cin': str,
            'company_name': str,
            'change_type': str,
            'company_status': str,
            'company_category': str
        }
        
        for field, field_type in key_fields.items():
            if field in row.index:
                value = row[field]
                if pd.notna(value):
                    try:
                        if field_type == str:
                            metadata[field] = str(value)[:500]
                        else:
                            metadata[field] = field_type(value)
                    except:
                        pass
        
        return metadata
    
    def _generate_unique_id(self, row: pd.Series, doc_type: str, idx: int) -> str:
        """Generate unique ID for document."""
        key_data = f"{doc_type}_{row.get('cin', '')}_{idx}"
        hash_id = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"{doc_type}_{hash_id}"
    
    def query_companies(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """Query companies collection."""
        if not self.companies_collection:
            logger.error("Companies collection not initialized")
            return []
        
        try:
            query_params = {
                "query_texts": [query],
                "n_results": top_k
            }
            
            if filter_dict:
                query_params["where"] = filter_dict
            
            results = self.companies_collection.query(**query_params)
            return self._format_results(results)
            
        except Exception as e:
            logger.error(f"Error querying companies: {e}")
            return []
    
    def query_changes(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict]:
        """Query changes collection."""
        if not self.changes_collection:
            logger.error("Changes collection not initialized")
            return []
        
        try:
            query_params = {
                "query_texts": [query],
                "n_results": top_k
            }
            
            if filter_dict:
                query_params["where"] = filter_dict
            
            results = self.changes_collection.query(**query_params)
            return self._format_results(results)
            
        except Exception as e:
            logger.error(f"Error querying changes: {e}")
            return []
    
    def _format_results(self, results: Dict) -> List[Dict]:
        """Format ChromaDB results."""
        formatted = []
        
        if results and 'documents' in results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                formatted.append({
                    'document': doc,
                    'metadata': results['metadatas'][0][i] if 'metadatas' in results else {},
                    'distance': results['distances'][0][i] if 'distances' in results else 0,
                    'id': results['ids'][0][i] if 'ids' in results else None
                })
        
        return formatted
    
    def get_company_by_cin(self, cin: str) -> Optional[Dict]:
        """Get company by CIN."""
        if not self.companies_collection:
            logger.error("Companies collection not initialized")
            return None
        
        try:
            results = self.companies_collection.get(
                where={"cin": cin},
                limit=1
            )
            
            if results and results['documents']:
                return {
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0] if results['metadatas'] else {},
                    'id': results['ids'][0] if results['ids'] else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting company by CIN: {e}")
            return None
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about collections."""
        stats = {
            'companies_count': 0,
            'changes_count': 0,
            'indexed_files': len(self.indexed_files)
        }
        
        try:
            if self.companies_collection:
                stats['companies_count'] = self.companies_collection.count()
            
            if self.changes_collection:
                stats['changes_count'] = self.changes_collection.count()
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
        
        return stats
    
    def reset_collections(self):
        """Reset (delete and recreate) all collections."""
        try:
            logger.info("Resetting collections...")
            
            # Delete existing collections
            try:
                self.client.delete_collection("companies")
                logger.info(f"  {SYMBOLS['success']} Companies collection deleted")
            except:
                pass
            
            try:
                self.client.delete_collection("changes")
                logger.info(f"  {SYMBOLS['success']} Changes collection deleted")
            except:
                pass
            
            # Recreate collections
            self.companies_collection = self.client.get_or_create_collection(
                name="companies",
                metadata={
                    "description": "Company data embeddings",
                    "created_at": datetime.now().isoformat()
                }
            )
            
            self.changes_collection = self.client.get_or_create_collection(
                name="changes",
                metadata={
                    "description": "Change logs embeddings",
                    "created_at": datetime.now().isoformat()
                }
            )
            
            # Clear indexed files tracker
            self.indexed_files.clear()
            
            logger.info(f"{SYMBOLS['success']} Collections recreated successfully")
            
        except Exception as e:
            logger.error(f"{SYMBOLS['error']} Error resetting collections: {e}")
    
    def search_similar_companies(self, cin: str, top_k: int = 5) -> List[Dict]:
        """Find companies similar to the given CIN."""
        company = self.get_company_by_cin(cin)
        
        if not company:
            logger.warning(f"Company with CIN {cin} not found")
            return []
        
        return self.query_companies(company['document'], top_k=top_k + 1)[1:]
    
    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_collection_stats()
        return (
            f"RAGSystem(\n"
            f"  companies: {stats['companies_count']:,},\n"
            f"  changes: {stats['changes_count']:,},\n"
            f"  indexed_files: {stats['indexed_files']}\n"
            f")"
        )