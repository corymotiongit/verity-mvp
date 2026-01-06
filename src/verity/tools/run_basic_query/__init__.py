"""
run_basic_query@1.0 - Operaciones básicas sin Data Dictionary ni DIA

Responsabilidad:
- Ejecutar operaciones determinísticas simples sobre cualquier CSV/DataFrame
- NO requiere metadatos (Data Dictionary o DIA schema)
- Detecta intent básico mediante keywords exactos
- Soporte: COUNT, DISTINCT, TOP N, SUM, AVG, MIN, MAX

Input: question + table_name
Output: data + operation_detected + confidence

REGLAS:
1. Solo keywords exactos (no fuzzy matching)
2. Retornar confidence bajo (0.6-0.8) para señalar que es fallback
3. Fail loudly si operación no soportada
4. NUNCA inventar columnas (usar user input exacto)
"""

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

from verity.exceptions import InvalidFilterException, ValidationException
from verity.tools.base import BaseTool, ToolDefinition

logger = logging.getLogger(__name__)


class RunBasicQueryTool(BaseTool):
    """
    Tool determinista para operaciones básicas sin metadatos.
    
    Soporte:
    - COUNT: "count", "cuantos", "how many", "total rows"
    - DISTINCT: "unique", "distinct", "diferentes"
    - TOP N: "top N", "first N", "limit N"
    - SUM: "sum", "suma", "total"
    - AVG: "average", "avg", "promedio"
    - MIN/MAX: "min", "max", "minimum", "maximum"
    """

    @property
    def definition(self) -> ToolDefinition:
        """Carga definición desde schema.json"""
        schema_path = Path(__file__).parent / "schema.json"
        import json

        with schema_path.open(encoding="utf-8") as f:
            schema_dict = json.load(f)
        return ToolDefinition(
            name=schema_dict["name"],
            version=schema_dict["version"],
            description=schema_dict["description"],
            input_schema=schema_dict["input_schema"],
            output_schema=schema_dict["output_schema"],
        )

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta operación básica sobre tabla.
        
        Proceso:
        1. Detectar operación mediante keywords exactos
        2. Extraer columna target (si aplica)
        3. Cargar datos
        4. Ejecutar operación
        5. Retornar resultado con confidence bajo
        """
        question = input_data["question"]
        table_name = input_data["table_name"]
        
        q_lower = question.lower().strip()
        
        # Detectar operación (keywords exactos)
        operation, target_column, limit_n = self._detect_operation(q_lower)
        
        if not operation:
            raise ValidationException(
                message="No se pudo detectar operación básica soportada.",
                errors=[{
                    "code": "UNSUPPORTED_BASIC_OPERATION",
                    "question": question,
                    "supported": ["COUNT", "DISTINCT", "TOP N", "SUM", "AVG", "MIN", "MAX"],
                }],
            )
        
        # Cargar datos
        from verity.config import get_settings
        settings = get_settings()
        
        # PR2: Cargar desde uploads/canonical/
        canonical_dir = Path("uploads") / "canonical"
        if not canonical_dir.exists():
            raise ValidationException(
                message=f"Directorio canonical no existe: {canonical_dir}",
            )
        
        # Buscar archivo que coincida con table_name
        csv_path = None
        for file in canonical_dir.glob("*.csv"):
            if file.stem.lower() == table_name.lower():
                csv_path = file
                break
        
        if not csv_path or not csv_path.exists():
            raise ValidationException(
                message=f"Tabla no encontrada: {table_name}",
                errors=[{"table": table_name, "searched_in": str(canonical_dir)}],
            )
        
        logger.info(f"[run_basic_query] Loading table '{table_name}' from {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"[run_basic_query] Loaded {len(df)} rows")
        
        # Ejecutar operación
        result_data, operation_detail = self._execute_operation(
            df=df,
            operation=operation,
            target_column=target_column,
            limit_n=limit_n,
        )
        
        # Confidence bajo para señalar que es fallback
        confidence = 0.7 if operation == "COUNT" else 0.6
        
        return {
            "data": result_data,
            "operation": operation,
            "operation_detail": operation_detail,
            "table_name": table_name,
            "confidence": confidence,
            "is_fallback": True,
            "data_source": "basic_query_fallback",
        }
    
    def _detect_operation(self, question: str) -> tuple[str | None, str | None, int | None]:
        """
        Detecta operación básica mediante keywords exactos.
        
        Returns:
            (operation, target_column, limit_n)
        """
        # COUNT
        if any(k in question for k in ["count", "cuantos", "cuántos", "how many", "total rows", "number of rows"]):
            return "COUNT", None, None
        
        # DISTINCT (con columna)
        distinct_match = re.search(
            r"(unique|distinct|diferentes|distintos)\s+(?:values?\s+(?:in|of|for)\s+)?([a-z0-9_]+)",
            question,
            re.IGNORECASE,
        )
        if distinct_match:
            column = distinct_match.group(2)
            return "DISTINCT", column, None
        
        # TOP N (con límite y opcionalmente columna)
        top_match = re.search(
            r"(top|first|limit)\s+(\d+)(?:\s+(?:by|order\s+by)\s+([a-z0-9_]+))?",
            question,
            re.IGNORECASE,
        )
        if top_match:
            limit_n = int(top_match.group(2))
            order_column = top_match.group(3) if top_match.group(3) else None
            return "TOP_N", order_column, limit_n
        
        # SUM (con columna)
        sum_match = re.search(
            r"(sum|suma|total)\s+(?:of\s+)?([a-z0-9_]+)",
            question,
            re.IGNORECASE,
        )
        if sum_match:
            column = sum_match.group(2)
            return "SUM", column, None
        
        # AVG (con columna)
        avg_match = re.search(
            r"(average|avg|promedio)\s+(?:of\s+)?([a-z0-9_]+)",
            question,
            re.IGNORECASE,
        )
        if avg_match:
            column = avg_match.group(2)
            return "AVG", column, None
        
        # MIN (con columna)
        min_match = re.search(
            r"(min|minimum|menor|mínimo)\s+(?:of\s+)?([a-z0-9_]+)",
            question,
            re.IGNORECASE,
        )
        if min_match:
            column = min_match.group(2)
            return "MIN", column, None
        
        # MAX (con columna)
        max_match = re.search(
            r"(max|maximum|mayor|máximo)\s+(?:of\s+)?([a-z0-9_]+)",
            question,
            re.IGNORECASE,
        )
        if max_match:
            column = max_match.group(2)
            return "MAX", column, None
        
        return None, None, None
    
    def _execute_operation(
        self,
        df: pd.DataFrame,
        operation: str,
        target_column: str | None,
        limit_n: int | None,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        Ejecuta operación sobre DataFrame.
        
        Returns:
            (result_data, operation_detail)
        """
        # Normalizar nombres de columnas para matching case-insensitive
        column_mapping = {col.lower(): col for col in df.columns}
        
        # Helper para resolver columna case-insensitive
        def resolve_column(col_name: str | None) -> str | None:
            if not col_name:
                return None
            col_lower = col_name.lower()
            return column_mapping.get(col_lower, None)
        
        if operation == "COUNT":
            count = len(df)
            return [{"count": count}], f"COUNT(*) = {count}"
        
        elif operation == "DISTINCT":
            if not target_column:
                raise ValidationException("DISTINCT requiere especificar columna")
            
            actual_col = resolve_column(target_column)
            if not actual_col:
                raise InvalidFilterException(
                    message=f"Columna no encontrada: {target_column}",
                    details={"column": target_column, "available": list(df.columns)},
                )
            
            unique_values = df[actual_col].dropna().unique().tolist()
            result = [{"value": v} for v in unique_values[:100]]  # Limitar a 100
            return result, f"DISTINCT {actual_col} ({len(unique_values)} values)"
        
        elif operation == "TOP_N":
            if not limit_n:
                limit_n = 10
            
            if target_column:
                # TOP N ordenado por columna
                actual_col = resolve_column(target_column)
                if not actual_col:
                    raise InvalidFilterException(
                        message=f"Columna no encontrada: {target_column}",
                        details={"column": target_column, "available": list(df.columns)},
                    )
                
                df_sorted = df.sort_values(by=actual_col, ascending=False)
                result = df_sorted.head(limit_n).to_dict(orient="records")
                return result, f"TOP {limit_n} ORDER BY {actual_col} DESC"
            else:
                # TOP N sin orden (primeras N filas)
                result = df.head(limit_n).to_dict(orient="records")
                return result, f"LIMIT {limit_n}"
        
        elif operation in ["SUM", "AVG", "MIN", "MAX"]:
            if not target_column:
                raise ValidationException(f"{operation} requiere especificar columna")
            
            actual_col = resolve_column(target_column)
            if not actual_col:
                raise InvalidFilterException(
                    message=f"Columna no encontrada: {target_column}",
                    details={"column": target_column, "available": list(df.columns)},
                )
            
            # Convertir a numérico si es posible
            series = pd.to_numeric(df[actual_col], errors="coerce")
            
            if series.isna().all():
                raise ValidationException(
                    f"Columna '{actual_col}' no contiene valores numéricos",
                )
            
            if operation == "SUM":
                value = float(series.sum())
                return [{"sum": value}], f"SUM({actual_col}) = {value}"
            elif operation == "AVG":
                value = float(series.mean())
                return [{"avg": value}], f"AVG({actual_col}) = {value}"
            elif operation == "MIN":
                value = float(series.min())
                return [{"min": value}], f"MIN({actual_col}) = {value}"
            elif operation == "MAX":
                value = float(series.max())
                return [{"max": value}], f"MAX({actual_col}) = {value}"
        
        raise ValidationException(f"Operación no implementada: {operation}")


__all__ = ["RunBasicQueryTool"]
