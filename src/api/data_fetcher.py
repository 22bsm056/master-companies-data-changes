"""Data fetcher for government API."""
import asyncio
import aiohttp
import pandas as pd
from typing import Optional, List
from io import StringIO
from config.settings import Settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class DataFetcher:
    """Fetch data from government API."""
    
    def __init__(self):
        """Initialize data fetcher."""
        self.api_key = Settings.DATA_GOV_API_KEY
        self.base_url = Settings.DATA_GOV_BASE_URL
        self.batch_size = Settings.BATCH_SIZE
    
    def _build_url(self, offset: int, limit: int) -> str:
        """Build API URL with parameters."""
        return (
            f"{self.base_url}?"
            f"api-key={self.api_key}&"
            f"format=csv&"
            f"offset={offset}&"
            f"limit={limit}"
        )
    
    async def fetch_batch_async(self, session: aiohttp.ClientSession, offset: int) -> Optional[pd.DataFrame]:
        """
        Fetch a single batch asynchronously.
        
        Args:
            session: Aiohttp session
            offset: Record offset
        
        Returns:
            DataFrame or None
        """
        url = self._build_url(offset, self.batch_size)
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    df = pd.read_csv(StringIO(text))
                    logger.info(f"Fetched batch at offset {offset}: {len(df)} records")
                    return df
                else:
                    logger.error(f"Error fetching batch at offset {offset}: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception fetching batch at offset {offset}: {e}")
            return None
    
    async def fetch_all_data_async(self, max_records: Optional[int] = None) -> pd.DataFrame:
        """
        Fetch all data asynchronously.
        
        Args:
            max_records: Maximum records to fetch (None for all)
        
        Returns:
            Combined DataFrame
        """
        max_records = max_records or Settings.MAX_RECORDS
        all_dataframes = []
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for offset in range(0, max_records, self.batch_size):
                task = self.fetch_batch_async(session, offset)
                tasks.append(task)
                
                # Process in chunks to avoid overwhelming the API
                if len(tasks) >= 10:
                    results = await asyncio.gather(*tasks)
                    all_dataframes.extend([df for df in results if df is not None and not df.empty])
                    tasks = []
            
            # Process remaining tasks
            if tasks:
                results = await asyncio.gather(*tasks)
                all_dataframes.extend([df for df in results if df is not None and not df.empty])
        
        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)
            logger.info(f"Total records fetched: {len(combined_df)}")
            return combined_df
        else:
            logger.warning("No data fetched")
            return pd.DataFrame()
    
    def fetch_all_data(self, max_records: Optional[int] = None) -> pd.DataFrame:
        """
        Synchronous wrapper for fetch_all_data_async.
        
        Args:
            max_records: Maximum records to fetch
        
        Returns:
            DataFrame
        """
        return asyncio.run(self.fetch_all_data_async(max_records))
    
    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize dataframe column names to match database schema.
        
        Args:
            df: Input dataframe
        
        Returns:
            Normalized dataframe
        """
        column_mapping = {
            'CIN': 'cin',
            'CompanyName': 'company_name',
            'CompanyROCcode': 'company_roc_code',
            'CompanyCategory': 'company_category',
            'CompanySubCategory': 'company_sub_category',
            'CompanyClass': 'company_class',
            'AuthorizedCapital': 'authorized_capital',
            'PaidupCapital': 'paidup_capital',
            'CompanyRegistrationdate_date': 'registration_date',
            'Registered_Office_Address': 'registered_office_address',
            'Listingstatus': 'listing_status',
            'CompanyStatus': 'company_status',
            'CompanyStateCode': 'company_state_code',
            'CompanyIndian/Foreign Company': 'company_type',
            'nic_code': 'nic_code',
            'CompanyIndustrialClassification': 'industrial_classification',
            'SNAPSHOT_DATE': 'snapshot_date',
            'SNAPSHOT_TIMESTAMP': 'snapshot_timestamp'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Convert date columns
        if 'registration_date' in df.columns:
            df['registration_date'] = pd.to_datetime(df['registration_date'], errors='coerce')
        
        if 'snapshot_date' in df.columns:
            df['snapshot_date'] = pd.to_datetime(df['snapshot_date'], errors='coerce')
        
        if 'snapshot_timestamp' in df.columns:
            df['snapshot_timestamp'] = pd.to_datetime(df['snapshot_timestamp'], errors='coerce')
        
        return df