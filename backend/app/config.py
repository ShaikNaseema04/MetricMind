import os
from pathlib import Path
from pydantic import BaseModel

# Project Root Directory
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseModel):
    PROJECT_NAME: str = "MetricMind — Agentic Semantic BI Engine"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # Priority: Env var -> Downloads folder -> Workspace data/raw folder
    METRICMIND_DATA_DIR: str = os.getenv(
        "METRICMIND_DATA_DIR",
        r"C:\Users\VENKATA BALAJI\Downloads\MetricMind_Raw_Dataset"
    )
    
    # Local fallback path inside workspace if Downloads folder is not reachable
    FALLBACK_DATA_DIR: str = str(WORKSPACE_ROOT / "data" / "raw")
    
    # Processed data & reports directory
    PROCESSED_DATA_DIR: str = str(WORKSPACE_ROOT / "data" / "processed")
    REPORTS_DIR: str = str(WORKSPACE_ROOT / "data" / "reports")
    
    # SQLite Database File
    DB_PATH: str = os.getenv(
        "METRICMIND_DB_PATH",
        str(WORKSPACE_ROOT / "database" / "metricmind.db")
    )
    
    # Optional LLM API Keys
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    def get_effective_data_dir(self) -> Path:
        """Returns the primary data directory if it exists and has files, otherwise fallback."""
        primary = Path(self.METRICMIND_DATA_DIR)
        if primary.exists() and any(primary.glob("*.csv")):
            return primary
        fallback = Path(self.FALLBACK_DATA_DIR)
        if fallback.exists() and any(fallback.glob("*.csv")):
            return fallback
        return primary

settings = Settings()
