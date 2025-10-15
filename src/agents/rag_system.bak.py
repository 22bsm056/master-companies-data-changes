"""RAG (Retrieval Augmented Generation) system for querying company data."""
import os
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from sentence_transformers import SentenceTransformer
import chromadb
from config.settings import Settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class RAGSystem:
    """RAG system for document retrieval and querying."""
    
    def __init__(self):
        """Initialize RAG system."""
        self.embeddings_dir = Settings.EMBEDDINGS_DIR
        self.snapshot_dir = Settings.SNAPSHOT_DIR
        self.changes_dir = Settings.CHANGES_DIR
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
            self.embedding_model = None
        
        # Initialize ChromaDB with new API
        try:
            # Use PersistentClient instead of Client with deprecated settings
            self.client = chromadb.PersistentClient(
                path=str(self.embeddings_dir)
            )
            logger.info(f"ChromaDB initialized at {self.embeddings_dir}")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            # Fallback to ephemeral client (in-memory)
            self.client = chromadb.EphemeralClient()
            logger.warning("Using ephemeral ChromaDB client (data will not persist)")
        
        # Create or get collections
        try:
            self.companies_collection = self.client.get_or_create_collection(
                name="companies",
                metadata={"description": "Company data embeddings"}
            )
            
            self.changes_collection = self.client.get_or_create_collection(
                name="changes",
                metadata={"description": "Change logs embeddings"}
            )
            logger.info("Collections created/loaded successfully")
        except Exception as e:
            logger.error(f"Error creating collections: {e}")
            self.companies_collection = None
            self.changes_collection = None
    
    def index_snapshots(self):
        """Index all snapshot files."""
        if not self.companies_collection:
            logger.error("Companies collection not initialized")
            return
            
        try:
            logger.info("Starting snapshot indexing...")
            
            snapshot_files = sorted(self.snapshot_dir.glob("snapshot_*.csv"))
            
            if not snapshot_files:
                logger.warning("No snapshot files found")
                return
            
            for snapshot_file in snapshot_files:
                logger.info(f"Indexing {snapshot_file.name}")
                try:
                    df = pd.read_csv(snapshot_file)
                    self._index_dataframe(df, self.companies_collection, 'snapshot')
                except Exception as e:
                    logger.error(f"Error indexing {snapshot_file.name}: {e}")
            
            logger.info("Snapshot indexing completed")
            
        except Exception as e:
            logger.error(f"Error indexing snapshots: {e}")
    
    def index_changes(self):
        """Index all change files."""
        if not self.changes_collection:
            logger.error("Changes collection not initialized")
            return
            
        try:
            logger.info("Starting changes indexing...")
            
            change_files = sorted(self.changes_dir.glob("changes_*.csv"))
            
            if not change_files:
                logger.warning("No change files found")
                return
            
            for change_file in change_files:
                logger.info(f"Indexing {change_file.name}")
                try:
                    df = pd.read_csv(change_file)
                    self._index_dataframe(df, self.changes_collection, 'change')
                except Exception as e:
                    logger.error(f"Error indexing {change_file.name}: {e}")
            
            logger.info("Changes indexing completed")
            
        except Exception as e:
            logger.error(f"Error indexing changes: {e}")
    
    def _index_dataframe(self, df: pd.DataFrame, collection, doc_type: str):
        """Index a dataframe into a collection."""
        if collection is None:
            logger.error("Collection is None, cannot index")
            return
            
        try:
            documents = []
            metadatas = []
            ids = []
            
            for idx, row in df.iterrows():
                # Create document text
                doc_text = self._row_to_text(row)
                documents.append(doc_text)
                
                # Create metadata (ensure all values are strings or numbers)
                metadata = {
                    'type': str(doc_type),
                    'cin': str(row.get('cin', '')),
                    'company_name': str(row.get('company_name', ''))[:500],  # Limit length
                    'change_type': str(row.get('change_type', 'N/A'))
                }
                metadatas.append(metadata)
                
                # Create unique ID
                ids.append(f"{doc_type}_{row.get('cin', idx)}_{idx}")
            
            if documents:
                # Add to collection in batches
                batch_size = 100
                for i in range(0, len(documents), batch_size):
                    batch_docs = documents[i:i+batch_size]
                    batch_metas = metadatas[i:i+batch_size]
                    batch_ids = ids[i:i+batch_size]
                    
                    try:
                        collection.add(
                            documents=batch_docs,
                            metadatas=batch_metas,
                            ids=batch_ids
                        )
                    except Exception as e:
                        logger.error(f"Error adding batch {i}-{i+batch_size}: {e}")
                
                logger.info(f"Indexed {len(documents)} documents")
                
        except Exception as e:
            logger.error(f"Error indexing dataframe: {e}")
    
    def _row_to_text(self, row: pd.Series) -> str:
        """Convert dataframe row to text for embedding."""
        text_parts = []
        
        for column, value in row.items():
            if pd.notna(value) and value != '':
                # Convert to string and limit length
                value_str = str(value)[:500]
                text_parts.append(f"{column}: {value_str}")
        
        return " | ".join(text_parts)
    
    def query_companies(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Query companies collection.
        
        Args:
            query: Search query
            top_k: Number of results
        
        Returns:
            List of results
        """
        if not self.companies_collection:
            logger.error("Companies collection not initialized")
            return []
            
        try:
            results = self.companies_collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            return self._format_results(results)
            
        except Exception as e:
            logger.error(f"Error querying companies: {e}")
            return []
    
    def query_changes(self, query: str, top_k: int = 5) -> List[Dict]:
        """Query changes collection."""
        if not self.changes_collection:
            logger.error("Changes collection not initialized")
            return []
            
        try:
            results = self.changes_collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
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
                    'distance': results['distances'][0][i] if 'distances' in results else 0
                })
        
        return formatted
    
    def get_company_context(self, cin: str) -> Optional[str]:
        """
        Get company context by CIN.
        
        Args:
            cin: Company CIN
        
        Returns:
            Company context string
        """
        if not self.companies_collection:
            logger.error("Companies collection not initialized")
            return None
            
        try:
            results = self.companies_collection.get(
                where={"cin": cin}
            )
            
            if results and results['documents']:
                return results['documents'][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting company context: {e}")
            return None
    
    def reset_collections(self):
        """Reset (delete) all collections."""
        try:
            self.client.delete_collection("companies")
            self.client.delete_collection("changes")
            logger.info("Collections deleted")
            
            # Recreate
            self.companies_collection = self.client.get_or_create_collection(
                name="companies",
                metadata={"description": "Company data embeddings"}
            )
            
            self.changes_collection = self.client.get_or_create_collection(
                name="changes",
                metadata={"description": "Change logs embeddings"}
            )
            logger.info("Collections recreated")
            
        except Exception as e:
            logger.error(f"Error resetting collections: {e}")