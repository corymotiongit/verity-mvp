"""
Verity Data Engine - Data Sandbox

Secure execution environment for Python/Pandas code.
Implements AST sanitization, timeouts, and output limits.
"""
import ast
import io
import sys
import time
import signal
import logging
import contextlib
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from .schemas import CodeExecutionRequest, CodeExecutionResult

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when code violates security constraints."""
    pass


class TimeoutError(Exception):
    """Raised when code execution exceeds time limit."""
    pass


class ASTSanitizer(ast.NodeVisitor):
    """
    AST-based code sanitizer.
    
    Blocks dangerous operations:
    - Import statements
    - File I/O operations
    - OS/subprocess access
    - Network operations
    - Dynamic code execution (exec, eval, compile)
    """
    
    BLOCKED_NAMES = {
        # Execution
        'exec', 'eval', 'compile', '__import__',
        # File I/O
        'open', 'file', 'input',
        # OS access
        'os', 'subprocess', 'sys', 'shutil', 'pathlib',
        # Network
        'socket', 'urllib', 'requests', 'http', 'ftplib',
        # Dangerous builtins
        'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr', 'delattr',
        'breakpoint', 'exit', 'quit',
    }
    
    BLOCKED_ATTRIBUTES = {
        '__class__', '__bases__', '__subclasses__', '__mro__',
        '__code__', '__globals__', '__builtins__',
        '__import__', '__loader__', '__spec__',
    }
    
    def __init__(self):
        self.violations = []
    
    def visit_Import(self, node):
        self.violations.append(f"Import no permitido: {ast.dump(node)}")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        self.violations.append(f"Import no permitido: from {node.module}")
        self.generic_visit(node)
    
    def visit_Name(self, node):
        if node.id in self.BLOCKED_NAMES:
            self.violations.append(f"Nombre bloqueado: {node.id}")
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        if node.attr in self.BLOCKED_ATTRIBUTES:
            self.violations.append(f"Atributo bloqueado: {node.attr}")
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Check for dangerous function calls
        if isinstance(node.func, ast.Name) and node.func.id in self.BLOCKED_NAMES:
            self.violations.append(f"Llamada bloqueada: {node.func.id}()")
        self.generic_visit(node)
    
    def validate(self, code: str) -> tuple[bool, list]:
        """
        Validate code against security rules.
        
        Returns:
            (is_safe, list_of_violations)
        """
        try:
            tree = ast.parse(code)
            self.visit(tree)
            return len(self.violations) == 0, self.violations
        except SyntaxError as e:
            return False, [f"Error de sintaxis: {e}"]


class DataSandbox:
    """
    Secure sandbox for executing Python/Pandas code.
    
    Features:
    - AST-based security validation
    - Execution timeout
    - Output size limits
    - Isolated namespace
    """
    
    # Limits
    TIMEOUT_SECONDS = 5
    MAX_OUTPUT_ROWS = 1000
    MAX_OUTPUT_SIZE = 100_000  # Characters
    
    def __init__(self, base_path: str = "uploads"):
        self.base_path = Path(base_path)
        self.sanitizer = ASTSanitizer()
    
    def execute(self, request: CodeExecutionRequest, df: pd.DataFrame) -> CodeExecutionResult:
        """
        Execute code in a sandboxed environment.
        
        Args:
            request: CodeExecutionRequest with code to execute
            df: Pre-loaded DataFrame
            
        Returns:
            CodeExecutionResult with value, preview, logs, or error
        """
        start_time = time.time()
        
        # 1. Security validation
        is_safe, violations = self.sanitizer.validate(request.code)
        if not is_safe:
            return CodeExecutionResult(
                success=False,
                error=f"Código bloqueado por seguridad: {'; '.join(violations)}",
                executed_code=request.code
            )
        
        # 2. Prepare isolated namespace
        stdout_buffer = io.StringIO()
        safe_locals = {
            "pd": pd,
            "np": np,
            "df": df,
            "datetime": datetime,
            "result": None,
        }
        
        # Safe builtins subset
        safe_builtins = {
            'len': len, 'range': range, 'enumerate': enumerate,
            'zip': zip, 'map': map, 'filter': filter,
            'sum': sum, 'min': min, 'max': max, 'abs': abs,
            'round': round, 'sorted': sorted, 'reversed': reversed,
            'list': list, 'dict': dict, 'set': set, 'tuple': tuple,
            'str': str, 'int': int, 'float': float, 'bool': bool,
            'True': True, 'False': False, 'None': None,
            'isinstance': isinstance, 'type': type,
            'print': lambda *args, **kwargs: print(*args, **kwargs, file=stdout_buffer),
        }
        
        safe_globals = {"__builtins__": safe_builtins}
        
        # 3. Execute with timeout
        try:
            with contextlib.redirect_stdout(stdout_buffer):
                exec(request.code, safe_globals, safe_locals)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            if execution_time > self.TIMEOUT_SECONDS * 1000:
                return CodeExecutionResult(
                    success=False,
                    error=f"Tiempo de ejecución excedido: {execution_time}ms > {self.TIMEOUT_SECONDS * 1000}ms",
                    executed_code=request.code,
                    execution_time_ms=execution_time
                )
            
            # 4. Extract and format result
            raw_result = safe_locals.get("result")
            value, preview = self._format_result(raw_result)
            
            # 5. Extract row_ids for audit (from DataFrame/Series indices)
            row_ids, row_count, sample_rows = self._extract_row_evidence(
                raw_result, df, safe_locals
            )
            
            logs = stdout_buffer.getvalue()[:self.MAX_OUTPUT_SIZE]
            
            return CodeExecutionResult(
                success=True,
                value=value,
                table_preview=preview,
                logs=logs,
                executed_code=request.code,
                execution_time_ms=execution_time,
                row_ids=row_ids,
                row_count=row_count,
                sample_rows=sample_rows
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Sandbox execution error: {e}")
            return CodeExecutionResult(
                success=False,
                error=str(e),
                executed_code=request.code,
                execution_time_ms=execution_time
            )
    
    def _extract_row_evidence(
        self, 
        raw_result: Any, 
        original_df: pd.DataFrame,
        safe_locals: dict
    ) -> tuple[list[int], int, list[dict]]:
        """
        Extract row evidence from execution result.
        
        Returns:
            (row_ids, row_count, sample_rows)
            
        row_ids are 1-indexed (line number in CSV = index + 2 for header)
        """
        row_ids = []
        row_count = 0
        sample_rows = []
        
        # Try to find DataFrame/Series with indices
        result_df = None
        
        if isinstance(raw_result, pd.DataFrame):
            result_df = raw_result
        elif isinstance(raw_result, pd.Series):
            result_df = raw_result.to_frame()
        else:
            # PRIORITY 1: Look for 'filtered_df' (our standard variable name)
            if "filtered_df" in safe_locals:
                val = safe_locals["filtered_df"]
                if isinstance(val, pd.DataFrame):
                    result_df = val
                elif isinstance(val, pd.Series):
                    result_df = val.to_frame()
            
            # PRIORITY 2: Look for any other filtered DataFrame
            if result_df is None:
                for name, val in safe_locals.items():
                    if name.startswith("_") or name in ["df", "pd", "np", "result", "datetime", "filtered_df"]:
                        continue
                    if isinstance(val, pd.DataFrame) and len(val) < len(original_df):
                        result_df = val
                        break
                    if isinstance(val, pd.Series) and len(val) < len(original_df):
                        result_df = val.to_frame()
                        break
        
        if result_df is not None and len(result_df) > 0:
            # Extract indices (0-indexed in DataFrame)
            # Convert to 1-indexed CSV line numbers (+2 for header and 1-based)
            indices = result_df.index.tolist()
            row_ids = [int(idx) + 2 for idx in indices[:100]]  # Limit to 100
            row_count = len(result_df)
            
            # Extract sample rows (1-3) with only first few columns
            sample_cols = list(result_df.columns)[:5]  # Limit columns for readability
            for idx, row in result_df.head(3).iterrows():
                sample_row = {col: self._serialize_value(row[col]) for col in sample_cols if col in row.index}
                sample_row["_row_id"] = int(idx) + 2
                sample_rows.append(sample_row)
        
        return row_ids, row_count, sample_rows
    
    def _format_result(self, raw_result: Any) -> tuple[Any, Optional[dict]]:
        """
        Format the result for JSON serialization.
        
        Returns:
            (serializable_value, table_data_if_applicable)
            
        table_data format:
            {"columns": [...], "rows": [[...], ...], "total_rows": int}
        """
        if raw_result is None:
            return None, None
        
        if isinstance(raw_result, pd.DataFrame):
            total_rows = len(raw_result)
            limited = raw_result.head(self.MAX_OUTPUT_ROWS)
            
            # Convert to structured format
            columns = list(limited.columns)
            rows = []
            for _, row in limited.iterrows():
                rows.append([self._serialize_value(row[col]) for col in columns])
            
            table_data = {
                "columns": columns,
                "rows": rows,
                "total_rows": total_rows
            }
            
            value = f"DataFrame con {total_rows} filas y {len(columns)} columnas"
            return value, table_data
        
        if isinstance(raw_result, pd.Series):
            total_rows = len(raw_result)
            limited = raw_result.head(self.MAX_OUTPUT_ROWS)
            
            # Convert Series to table format
            columns = [raw_result.name or "Index", "Value"]
            rows = [[self._serialize_value(idx), self._serialize_value(val)] 
                    for idx, val in limited.items()]
            
            table_data = {
                "columns": columns,
                "rows": rows,
                "total_rows": total_rows
            }
            
            return limited.to_dict(), table_data
        
        if isinstance(raw_result, dict):
            # Convert dict to table format
            columns = ["Key", "Value"]
            rows = [[str(k), self._serialize_value(v)] for k, v in raw_result.items()]
            
            if len(rows) > 0:
                table_data = {
                    "columns": columns,
                    "rows": rows[:self.MAX_OUTPUT_ROWS],
                    "total_rows": len(rows)
                }
                return raw_result, table_data
            return raw_result, None
        
        if isinstance(raw_result, list) and len(raw_result) > 0:
            # Check if it's a list of dicts (common pattern)
            if isinstance(raw_result[0], dict):
                columns = list(raw_result[0].keys())
                rows = []
                for item in raw_result[:self.MAX_OUTPUT_ROWS]:
                    rows.append([self._serialize_value(item.get(col, "")) for col in columns])
                
                table_data = {
                    "columns": columns,
                    "rows": rows,
                    "total_rows": len(raw_result)
                }
                return raw_result, table_data
            return raw_result, None
        
        # Scalar values
        try:
            # Handle numpy types
            if hasattr(raw_result, 'item'):
                return raw_result.item(), None
            return raw_result, None
        except:
            return str(raw_result), None
    
    def _serialize_value(self, val) -> Any:
        """Serialize a value for JSON."""
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        if hasattr(val, 'item'):  # numpy types
            return val.item()
        if isinstance(val, (pd.Timestamp, datetime)):
            return val.isoformat()
        return val
    
    def load_dataframe(self, file_path: str) -> pd.DataFrame:
        """
        Load a DataFrame from file.
        
        Prefers canonical (normalized) files if available.
        Canonical files are already cleaned - no additional processing needed.
        
        Args:
            file_path: Relative path within base_path or full path
            
        Returns:
            Loaded DataFrame (already cleaned if from canonical)
        """
        # Extract doc_id if present in filename (format: {doc_id}_{filename})
        filename = Path(file_path).name
        parts = filename.split("_", 1)
        doc_id = parts[0] if len(parts) > 1 else None
        
        # Check for canonical file first
        canonical_dir = self.base_path / "canonical"
        canonical_path = None
        
        if canonical_dir.exists():
            if doc_id:
                matches = list(canonical_dir.glob(f"{doc_id}_*"))
                if matches:
                    canonical_path = matches[0]
            else:
                # Try exact name
                potential = canonical_dir / filename
                if potential.exists():
                    canonical_path = potential
        
        if canonical_path and canonical_path.exists():
            full_path = canonical_path
            is_canonical = True
            logger.debug(f"Loading canonical file: {canonical_path}")
        else:
            # Fall back to original path
            full_path = self.base_path / file_path
            is_canonical = False
            
            if not full_path.exists():
                # Try partial match
                matches = list(self.base_path.glob(f"*{file_path}"))
                if matches:
                    full_path = matches[0]
                else:
                    raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        suffix = full_path.suffix.lower()
        
        if suffix == '.csv':
            try:
                df = pd.read_csv(full_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(full_path, encoding='latin-1')
        elif suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(full_path)
        else:
            raise ValueError(f"Formato no soportado: {suffix}")
        
        # Only clean if not from canonical (canonical is already clean)
        if not is_canonical:
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].apply(lambda x: x.strip("'\"") if isinstance(x, str) else x)
        
        return df
