"""Tools for agentic system - Updated to prioritize HybridSearch."""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from src.database.operations import DatabaseOperations
from src.agents.hybrid_search import HybridSearch
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AgentTools:
    """Tools available to the agent - using HybridSearch as primary source."""
    
    def __init__(self):
        """Initialize agent tools."""
        self.db_ops = DatabaseOperations()
        self.search_system = HybridSearch()
        logger.info("[OK] Agent tools initialized with Hybrid Search")
    
    def search_company_by_name(self, company_name: str) -> List[Dict]:
        """
        Search company by name (uses HybridSearch).
        
        Args:
            company_name: Company name to search
        
        Returns:
            List of matching companies
        """
        logger.info(f"Searching company by name: {company_name}")
        return self.search_system.search_companies(company_name, limit=10)
    
    def search_company_by_cin(self, cin: str) -> Optional[Dict]:
        """
        Search company by CIN (uses HybridSearch).
        
        Args:
            cin: Company CIN
        
        Returns:
            Company data or None
        """
        logger.info(f"Searching company by CIN: {cin}")
        return self.search_system.get_company_by_cin(cin)
    
    def get_company_changes(self, cin: str) -> List[Dict]:
        """
        Get all changes for a company (uses HybridSearch).
        
        Args:
            cin: Company CIN
        
        Returns:
            List of changes
        """
        logger.info(f"Getting changes for CIN: {cin}")
        return self.search_system.get_changes_by_cin(cin)
    
    def query_rag_companies(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Query companies (uses HybridSearch).
        
        Args:
            query: Search query
            top_k: Number of results
        
        Returns:
            List of results
        """
        logger.info(f"Querying companies: {query}")
        return self.search_system.search_companies(query, limit=top_k)
    
    def query_rag_changes(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Query changes (uses HybridSearch).
        
        Args:
            query: Search query
            top_k: Number of results
        
        Returns:
            List of results
        """
        logger.info(f"Querying changes: {query}")
        return self.search_system.search_changes(query, limit=top_k)
    
    def web_search(self, query: str) -> str:
        """
        Perform web search (using DuckDuckGo).
        
        Args:
            query: Search query
        
        Returns:
            Search results as string
        """
        logger.info(f"Performing web search: {query}")
        
        try:
            # Using DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant information
                results = []
                
                if data.get('Abstract'):
                    results.append(f"Abstract: {data['Abstract']}")
                
                if data.get('RelatedTopics'):
                    results.append("Related Topics:")
                    for topic in data['RelatedTopics'][:3]:
                        if 'Text' in topic:
                            results.append(f"- {topic['Text']}")
                
                return "\n".join(results) if results else "No results found"
            else:
                return f"Search failed with status code: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return f"Error performing search: {str(e)}"
    
    def get_statistics(self, days: int = 30) -> Dict:
        """
        Get statistics - uses HybridSearch data.
        
        Args:
            days: Number of days
        
        Returns:
            Statistics dictionary
        """
        logger.info(f"Getting statistics for last {days} days")
        
        try:
            # Get from HybridSearch (CSV data)
            search_stats = self.search_system.get_statistics()
            
            # Calculate changes within date range from CSV
            stats = {
                'total_companies': search_stats.get('total_companies', 0),
                'active_companies': search_stats.get('active_companies', 0),
                'total_changes': search_stats.get('total_changes', 0),
                'changes_by_type': search_stats.get('changes_by_type', {
                    'NEW': 0,
                    'MODIFIED': 0,
                    'DELETED': 0
                })
            }
            
            # If we have changes data, filter by date
            if self.search_system.changes_df is not None and not self.search_system.changes_df.empty:
                try:
                    # Calculate date range
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=days)
                    
                    # Convert change_date column to datetime
                    if 'change_date' in self.search_system.changes_df.columns:
                        changes_df = self.search_system.changes_df.copy()
                        changes_df['change_date'] = pd.to_datetime(changes_df['change_date'], errors='coerce')
                        
                        # Filter by date range
                        mask = (changes_df['change_date'].dt.date >= start_date) & (changes_df['change_date'].dt.date <= end_date)
                        filtered_changes = changes_df[mask]
                        
                        # Count by type
                        if 'change_type' in filtered_changes.columns:
                            stats['total_changes'] = len(filtered_changes)
                            stats['changes_by_type'] = {
                                'NEW': len(filtered_changes[filtered_changes['change_type'] == 'NEW']),
                                'MODIFIED': len(filtered_changes[filtered_changes['change_type'] == 'MODIFIED']),
                                'DELETED': len(filtered_changes[filtered_changes['change_type'] == 'DELETED'])
                            }
                except Exception as e:
                    logger.warning(f"Could not filter changes by date: {e}")
            
            logger.info(f"[OK] Statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_companies': 0,
                'active_companies': 0,
                'total_changes': 0,
                'changes_by_type': {'NEW': 0, 'MODIFIED': 0, 'DELETED': 0}
            }