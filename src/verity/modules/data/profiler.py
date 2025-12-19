"""
Verity Data Engine - Dataset Profiler

Generates rich metadata about datasets for LLM context.
Runs automatically on ingest and update.
"""
import logging
import pandas as pd
from pathlib import Path
from typing import Optional

from .schemas import DatasetProfile

logger = logging.getLogger(__name__)


class DatasetProfiler:
    """
    Generates comprehensive profiles of tabular datasets.
    
    Profile includes:
    - Shape and columns
    - Data types
    - Sample rows (head + random)
    - Column analysis (cardinality, top values)
    """
    
    # Thresholds
    SAMPLE_THRESHOLD = 1000  # Rows above which we include random sample
    SAMPLE_SIZE = 200
    HEAD_SIZE = 20
    TOP_VALUES_LIMIT = 30
    CATEGORICAL_CARDINALITY_THRESHOLD = 100
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
    
    def profile(self, dataset_id: str, file_path: str) -> DatasetProfile:
        """
        Generate a complete profile for the dataset.
        
        Prefers canonical (normalized) files if available.
        
        Args:
            dataset_id: Unique identifier for the dataset
            file_path: Relative path to file within base_path (or canonical/)
            
        Returns:
            DatasetProfile with all metadata
        """
        # Check for canonical file first
        canonical_path = self.base_path / "canonical" / Path(file_path).name
        if not canonical_path.exists():
            # Try with dataset_id prefix
            matches = list((self.base_path / "canonical").glob(f"{dataset_id}_*"))
            if matches:
                canonical_path = matches[0]
        
        if canonical_path.exists():
            full_path = canonical_path
            logger.info(f"Using canonical file: {canonical_path}")
        else:
            full_path = self.base_path / file_path
            logger.info(f"Using original file (no canonical): {full_path}")
        
        df = self._load_dataframe(full_path)
        
        # Basic metadata
        profile = DatasetProfile(
            dataset_id=dataset_id,
            filename=file_path,
            shape=df.shape,
            columns=list(df.columns),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            head=df.head(self.HEAD_SIZE).to_dict(orient='records'),
            sample=self._get_sample(df),
            column_analysis=self._analyze_columns(df)
        )
        
        logger.info(f"Profiled dataset {dataset_id}: {df.shape[0]} rows, {df.shape[1]} columns")
        return profile
    
    def _load_dataframe(self, path: Path) -> pd.DataFrame:
        """Load DataFrame with encoding fallback and quote cleaning."""
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            try:
                df = pd.read_csv(path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding='latin-1')
        elif suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")
        
        # Clean string values - remove surrounding quotes
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].apply(lambda x: x.strip("'\"") if isinstance(x, str) else x)
        
        return df
    
    def _get_sample(self, df: pd.DataFrame) -> Optional[list]:
        """Get random sample if dataset is large enough."""
        if len(df) > self.SAMPLE_THRESHOLD:
            sample_size = min(self.SAMPLE_SIZE, len(df))
            return df.sample(n=sample_size, random_state=42).to_dict(orient='records')
        return None
    
    def _analyze_columns(self, df: pd.DataFrame) -> dict:
        """
        Analyze each column for cardinality and top values.
        
        This is critical for the Value Index to work correctly.
        """
        analysis = {}
        
        for col in df.columns:
            try:
                col_data = df[col]
                nunique = col_data.nunique()
                
                # Determine column type
                is_categorical = (
                    col_data.dtype == 'object' or 
                    col_data.dtype.name == 'category' or
                    (pd.api.types.is_numeric_dtype(col_data) and nunique <= self.CATEGORICAL_CARDINALITY_THRESHOLD)
                )
                
                if is_categorical:
                    # Get top values with counts
                    value_counts = col_data.value_counts().head(self.TOP_VALUES_LIMIT)
                    analysis[col] = {
                        "type": "categorical",
                        "nunique": int(nunique),
                        "top_values": value_counts.index.tolist(),
                        "top_counts": value_counts.tolist(),
                        "null_count": int(col_data.isna().sum())
                    }
                else:
                    # Numeric column
                    analysis[col] = {
                        "type": "numeric",
                        "nunique": int(nunique),
                        "min": self._safe_value(col_data.min()),
                        "max": self._safe_value(col_data.max()),
                        "mean": self._safe_value(col_data.mean()),
                        "null_count": int(col_data.isna().sum())
                    }
            except Exception as e:
                logger.warning(f"Failed to analyze column {col}: {e}")
                analysis[col] = {"type": "unknown", "error": str(e)}
        
        return analysis
    
    def _safe_value(self, val) -> Optional[float]:
        """Convert to JSON-safe value."""
        try:
            if pd.isna(val):
                return None
            return float(val)
        except (TypeError, ValueError):
            return None
