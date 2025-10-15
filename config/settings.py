"""Application settings and configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    """Application settings."""
    
    # Base directories
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    SNAPSHOT_DIR = DATA_DIR / "snapshots"
    CHANGES_DIR = DATA_DIR / "changes"
    LOGS_DIR = DATA_DIR / "logs"
    EMBEDDINGS_DIR = DATA_DIR / "embeddings"
    
    # API Configuration
    DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY")
    DATA_GOV_BASE_URL = os.getenv("DATA_GOV_BASE_URL")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "company_data_db")
    
    # Application Settings
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", 1000))
    MAX_RECORDS = int(os.getenv("MAX_RECORDS", 1000000))
    
    # Scheduler Settings
    SNAPSHOT_TIME = os.getenv("SNAPSHOT_TIME", "02:00")
    CHANGE_DETECTION_TIME = os.getenv("CHANGE_DETECTION_TIME", "03:00")
    
    # Flask Settings
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # Streamlit Settings
    STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", 8501))
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories if they don't exist."""
        for directory in [cls.SNAPSHOT_DIR, cls.CHANGES_DIR, cls.LOGS_DIR, cls.EMBEDDINGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_database_url(cls):
        """Get database connection URL."""
        return f"mysql+mysqlconnector://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

# Create directories on import
Settings.create_directories()