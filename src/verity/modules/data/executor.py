import logging
import pandas as pd
import io
import contextlib
from typing import Any
from pathlib import Path
from .schemas import CodeExecutionRequest, CodeExecutionResult

logger = logging.getLogger(__name__)

class DataExecutor:
    """
    Code Interpreter Engine.
    Executes Python code on tabular data in a controlled environment.
    """
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        
    def _load_df(self, file_path: str) -> pd.DataFrame:
        """Load DataFrame from file path."""
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            # Try finding by partial match
            search = list(self.base_path.glob(f"*{file_path}"))
            if search:
                full_path = search[0]
            else:
                raise FileNotFoundError(f"File not found: {file_path}")
            
        suffix = full_path.suffix.lower()
        
        try:
            if suffix == '.csv':
                try:
                    df = pd.read_csv(full_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(full_path, encoding='latin-1')
            elif suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(full_path)
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
            
            return df
        except Exception as e:
            logger.error(f"Error loading file {full_path}: {e}")
            raise

    def _profile_data(self, file_path: str) -> dict:
        """
        Generate a rich profile of the data for the LLM.
        Includes dtypes, head samples, and top values for categoricals.
        """
        try:
            df = self._load_df(file_path)
            
            profile = {
                "columns": list(df.columns),
                "dtypes": {k: str(v) for k, v in df.dtypes.items()},
                "shape": df.shape,
                "head": df.head(5).to_dict(orient='records'),
                "column_analysis": {}
            }
            
            # Analyze columns for top values (cardinality)
            for col in df.columns:
                try:
                    # Check if column is categorical-like (object or category or low cardinality numeric)
                    is_categorical = False
                    if df[col].dtype == 'object' or df[col].dtype.name == 'category':
                        is_categorical = True
                    elif pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique() < 50:
                        is_categorical = True
                        
                    if is_categorical:
                        # Get top 20 most frequent values to give context
                        top_vals = df[col].value_counts().head(20).index.tolist()
                        profile["column_analysis"][col] = {
                            "type": "categorical",
                            "nunique": int(df[col].nunique()),
                            "top_values": top_vals
                        }
                    else:
                        # Numeric or high cardinality
                         profile["column_analysis"][col] = {
                            "type": "numeric/other",
                            "sample_min": str(df[col].min()) if not df[col].empty else None,
                            "sample_max": str(df[col].max()) if not df[col].empty else None
                        }
                except Exception as e:
                    logger.warning(f"Failed to profile column {col}: {e}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Profiling failed: {e}")
            raise

    def execute_code(self, request: CodeExecutionRequest) -> CodeExecutionResult:
        """
        Execute python code on the requested file.
        
        Environment:
        - `df`: The loaded pandas DataFrame
        - `pd`: pandas module
        - `result`: The variable where the script MUST store the final result
        """
        try:
            # 1. Load Data
            df = self._load_df(request.file_path)
            
            # 2. Prepare Environment
            stdout_buffer = io.StringIO()
            safe_locals = {
                "pd": pd,
                "df": df,
                "result": None # Placeholder for output
            }
            
            # 3. Execute Code
            with contextlib.redirect_stdout(stdout_buffer):
                exec(request.code, globals(), safe_locals)
                
            # 4. Extract Result
            final_result = safe_locals.get("result")
            stdout_output = stdout_buffer.getvalue()
            
            # 5. Format Result for Transport
            preview = None
            if isinstance(final_result, pd.DataFrame):
                # If result is a DF, convert to list of dicts for JSON serialization
                preview = final_result.head(20).to_dict(orient='records')
                # Keep it lightweight, maybe just descriptive text? 
                # For now let's actually return the data so frontend/agent can see it
                final_result = f"DataFrame with {len(final_result)} rows. Columns: {list(final_result.columns)}"
            elif isinstance(final_result, pd.Series):
                 # Convert Series to dict/list
                 final_result = final_result.head(20).to_dict()
                 
            return CodeExecutionResult(
                result=final_result,
                executed_code=request.code,
                preview=preview,
                stdout=stdout_output
            )

        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return CodeExecutionResult(
                result=None,
                executed_code=request.code,
                error=str(e)
            )
