"""
run_table_query@1.0 - Ejecución de queries sobre tablas

Responsabilidad:
- Ejecutar query estructurado sobre tabla
- Retornar resultado con table_id único
- Aplicar filtros, agregaciones, ordenamiento
- NO generar código
- NO decidir métricas (vienen del plan semántico)

Input: table + columns + metrics + filters + group_by + order_by + limit
Output: table_id + columns + rows + row_count + execution_time_ms
REGLA CRÍTICA: columns debe resolverse desde metrics map del Data Dictionary, NO del LLM.Ver schema.json para contrato completo.
"""

import logging
from verity.tools.base import BaseTool, ToolDefinition
from typing import Any, Iterable
import json
from pathlib import Path
from uuid import uuid4
import re

from verity.exceptions import EmptyResultException, InvalidFilterException, TypeMismatchException
from verity.core.table_store import TABLE_STORE, TableResult

import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache global simple para resultados de queries (MVP)
_QUERY_CACHE: dict[str, tuple[datetime, Any]] = {}
_CACHE_TTL_SECONDS = 120


class RunTableQueryTool(BaseTool):
    """
    Tool determinista para ejecutar queries sobre datos.
    
    NO genera código Python.
    NO usa LLM para decidir qué calcular.
    Solo ejecuta el plan que recibe.
    """
    
    @property
    def definition(self) -> ToolDefinition:
        """Carga definición desde schema.json"""
        schema_path = Path(__file__).parent / "schema.json"
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        
        return ToolDefinition(
            name="run_table_query",
            version="1.0",
            input_schema=schema["input"],
            output_schema=schema["output"],
            is_deterministic=True,
            execution_mode="local"
        )
    
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta query sobre tabla.
        
        Proceso:
        1. Cargar tabla desde data source
        2. Aplicar filtros
        3. Calcular métricas (usando SQL del Data Dictionary)
        4. Agrupar si hay group_by
        5. Ordenar si hay order_by
        6. Aplicar limit
        7. Retornar con table_id único
        """
        import pandas as pd
        import time
        
        table_name = input_data["table"]
        columns = input_data.get("columns", [])
        metrics = input_data.get("metrics", [])
        filters_spec = input_data.get("filters", [])
        group_by = input_data.get("group_by", [])
        order_by = input_data.get("order_by", [])
        limit = input_data.get("limit", 1000)  # Alineado con schema.json

        # Compare-periods (opcional)
        time_column = input_data.get("time_column")
        time_grain = input_data.get("time_grain")
        baseline_period = input_data.get("baseline_period")
        compare_period = input_data.get("compare_period")
        
        start_time = time.time()

        # 0. Verificar Cache (key incluye TODOS los parámetros que alteran resultados)
        cache_key_content = json.dumps({
            "table": table_name,
            "columns": columns,
            "metrics": metrics,
            "filters": filters_spec,
            "group_by": group_by,
            "order_by": order_by,
            "limit": limit,
            "time_column": time_column,
            "time_grain": time_grain,
            "baseline_period": baseline_period,
            "compare_period": compare_period
        }, sort_keys=True)
        cache_key = hashlib.sha256(cache_key_content.encode()).hexdigest()

        now = datetime.now()
        if cache_key in _QUERY_CACHE:
            expiry, cached_result = _QUERY_CACHE[cache_key]
            if now < expiry:
                # Cache Hit
                execution_time_ms = (time.time() - start_time) * 1000
                cached_result["execution_time_ms"] = execution_time_ms
                cached_result["cache_hit"] = True
                cached_result["result_metadata"] = input_data.get("result_metadata", {})
                return cached_result
        
        # Cargar tabla (buscar en uploads/canonical/ o fallback a Supabase)
        canonical_path = Path("uploads/canonical")
        table_file = None
        
        for file in canonical_path.glob(f"*{table_name}*.csv"):
            table_file = file
            break
        
        # Determinar y loguear data_source explícitamente
        data_source: str
        
        if table_file:
            data_source = "csv"
            logger.info(f"[run_table_query] Loading table '{table_name}' from CSV: {table_file}")
            df = pd.read_csv(table_file, encoding="utf-8")
            logger.info(f"[run_table_query] Loaded {len(df)} rows from CSV")
        else:
            # Fallback: cargar desde Supabase
            import os
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not supabase_url or not supabase_key:
                raise FileNotFoundError(
                    f"Table '{table_name}' not found in canonical storage and Supabase not configured"
                )
            
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            
            # Fetch all rows using pagination (Supabase limits to 1000 per request)
            all_data = []
            batch_size = 1000
            offset = 0
            while True:
                response = supabase.table(table_name).select("*").range(offset, offset + batch_size - 1).execute()
                if not response.data:
                    break
                all_data.extend(response.data)
                if len(response.data) < batch_size:
                    break
                offset += batch_size
            
            if not all_data:
                raise FileNotFoundError(f"Table '{table_name}' not found or empty in Supabase")
            
            data_source = "supabase"
            logger.info(f"[run_table_query] Loaded {len(all_data)} rows from Supabase")
            df = pd.DataFrame(all_data)

        def _ensure_datetime_column(local_df: "pd.DataFrame", column: str) -> "pd.Series":
            if column not in local_df.columns:
                raise KeyError(f"Missing columns in '{table_name}': ['{column}']")
            s = local_df[column]
            dt = pd.to_datetime(s, errors="coerce")
            bad = s.notna() & dt.isna()
            if bool(bad.any()):
                examples = s[bad].astype(str).head(5).tolist()
                raise TypeMismatchException(
                    message=f"Column '{column}' contains invalid date/time values.",
                    details={"column": column, "examples": examples},
                )
            return dt

        def _derive_time_bucket(local_df: "pd.DataFrame", source_col: str, grain: str) -> str:
            dt = _ensure_datetime_column(local_df, source_col)
            g = (grain or "").lower()
            derived = f"{source_col}__{g}"

            if g == "day":
                local_df[derived] = dt.dt.strftime("%Y-%m-%d")
                return derived
            if g == "month":
                local_df[derived] = dt.dt.to_period("M").astype(str)
                return derived
            if g == "week":
                # Semana representada por la fecha de inicio (lunes) ISO para estabilidad
                p = dt.dt.to_period("W-MON")
                local_df[derived] = p.apply(lambda x: x.start_time.strftime("%Y-%m-%d"))
                return derived

            raise InvalidFilterException(
                message=f"Unsupported time_grain: {grain}",
                details={"time_grain": grain},
            )

        # Derivar buckets temporales si group_by usa el patrón <col>__<grain>
        derived_group_by: list[str] = []
        for gb in (group_by or []):
            if not isinstance(gb, str):
                raise InvalidFilterException(message="group_by entries must be strings", details={"group_by": group_by})
            m = re.match(r"^([a-zA-Z0-9_]+)__(day|week|month)$", gb)
            if m:
                src_col, grain = m.group(1), m.group(2)
                derived = _derive_time_bucket(df, src_col, grain)
                derived_group_by.append(derived)
            else:
                derived_group_by.append(gb)
        group_by = derived_group_by

        allowed_ops = {"=", "!=", ">", "<", ">=", "<=", "IN", "LIKE"}

        def _is_group(node: Any) -> bool:
            return isinstance(node, dict) and "op" in node and "conditions" in node

        def _is_condition(node: Any) -> bool:
            return isinstance(node, dict) and "column" in node and "operator" in node and "value" in node

        def _flatten_conditions(node: Any) -> Iterable[dict[str, Any]]:
            if node is None:
                return []
            if isinstance(node, list):
                return node
            if _is_group(node):
                out: list[dict[str, Any]] = []
                for c in node.get("conditions", []):
                    out.extend(list(_flatten_conditions(c)))
                return out
            if _is_condition(node):
                return [node]
            return []

        def _validate_filters(spec: Any) -> None:
            if spec is None or spec == []:
                return
            if _is_condition(spec):
                op = str(spec.get("operator", "")).upper()
                if op not in allowed_ops:
                    raise InvalidFilterException(
                        message=f"Unsupported operator: {op}",
                        details={"operator": op, "allowed": sorted(allowed_ops)},
                    )
                if op == "IN" and not isinstance(spec.get("value"), list):
                    raise InvalidFilterException(message="IN operator requires a list value", details={"filter": spec})
                if op == "IN" and isinstance(spec.get("value"), list) and len(spec.get("value")) == 0:
                    raise InvalidFilterException(message="IN operator requires a non-empty list", details={"filter": spec})
                if op == "LIKE" and not isinstance(spec.get("value"), str):
                    raise InvalidFilterException(message="LIKE operator requires a string value", details={"filter": spec})
                return
            if isinstance(spec, list):
                for cond in spec:
                    if not _is_condition(cond):
                        raise InvalidFilterException(details={"filters": spec})
                    op = str(cond.get("operator", "")).upper()
                    if op not in allowed_ops:
                        raise InvalidFilterException(
                            message=f"Unsupported operator: {op}",
                            details={"operator": op, "allowed": sorted(allowed_ops)},
                        )
                    if op == "IN" and not isinstance(cond.get("value"), list):
                        raise InvalidFilterException(message="IN operator requires a list value", details={"filter": cond})
                    if op == "IN" and isinstance(cond.get("value"), list) and len(cond.get("value")) == 0:
                        raise InvalidFilterException(message="IN operator requires a non-empty list", details={"filter": cond})
                    if op == "LIKE" and not isinstance(cond.get("value"), str):
                        raise InvalidFilterException(message="LIKE operator requires a string value", details={"filter": cond})
                return
            if _is_group(spec):
                op = str(spec.get("op", "")).upper()
                if op not in {"AND", "OR"}:
                    raise InvalidFilterException(message=f"Unsupported logical op: {op}", details={"op": op})
                conditions = spec.get("conditions")
                if not isinstance(conditions, list) or len(conditions) == 0:
                    raise InvalidFilterException(message="Filter group requires non-empty conditions", details={"filters": spec})
                for c in conditions:
                    _validate_filters(c)
                return
            raise InvalidFilterException(details={"filters": spec})

        def _coerce_numeric(series: "pd.Series", column: str) -> "pd.Series":
            numeric = pd.to_numeric(series, errors="coerce")
            # Si hay valores no nulos que se volvieron NaN, es mismatch
            bad = series.notna() & numeric.isna()
            if bool(bad.any()):
                examples = series[bad].astype(str).head(5).tolist()
                raise TypeMismatchException(
                    message=f"Column '{column}' contains non-numeric values.",
                    details={"column": column, "examples": examples},
                )
            return numeric

        def _apply_condition(local_df: "pd.DataFrame", cond: dict[str, Any]) -> "pd.Series":
            col = cond["column"]
            op = str(cond["operator"]).upper()
            val = cond.get("value")

            if col not in local_df.columns:
                raise InvalidFilterException(message=f"Unknown column in filter: {col}", details={"column": col})

            s = local_df[col]
            def _coerce_filter_value_numeric(v: Any) -> float:
                try:
                    if isinstance(v, bool):
                        raise ValueError("bool is not a numeric filter value")
                    return float(v)
                except Exception as e:
                    raise TypeMismatchException(
                        message=f"Filter value for '{col}' must be numeric.",
                        details={"column": col, "value": v},
                    ) from e

            def _should_numeric_compare(series: "pd.Series", v: Any) -> bool:
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return True
                try:
                    from pandas.api.types import is_numeric_dtype

                    if is_numeric_dtype(series):
                        float(v)
                        return True
                except Exception:
                    return False
                return False

            if op in {">", "<", ">=", "<="}:
                s_num = _coerce_numeric(s, col)
                v_num = _coerce_filter_value_numeric(val)
                if op == ">":
                    return s_num > v_num
                if op == "<":
                    return s_num < v_num
                if op == ">=":
                    return s_num >= v_num
                return s_num <= v_num

            if op in {"=", "!="}:
                if _should_numeric_compare(s, val):
                    s_num = _coerce_numeric(s, col)
                    v_num = _coerce_filter_value_numeric(val)
                    return (s_num == v_num) if op == "=" else (s_num != v_num)
                left = s.astype(str)
                right = str(val)
                return (left == right) if op == "=" else (left != right)

            if op == "IN":
                if not isinstance(val, list) or len(val) == 0:
                    raise InvalidFilterException(message="IN operator requires a non-empty list value", details={"filter": cond})
                if _should_numeric_compare(s, val[0]) and all(_should_numeric_compare(s, v) for v in val):
                    s_num = _coerce_numeric(s, col)
                    values_num = [_coerce_filter_value_numeric(v) for v in val]
                    return s_num.isin(values_num)
                values_str = [str(v) for v in val]
                return s.astype(str).isin(values_str)

            if op == "LIKE":
                if not isinstance(val, str):
                    raise InvalidFilterException(message="LIKE operator requires a string value", details={"filter": cond})
                # SQL LIKE -> regex: % => .*, _ => .
                escaped = re.escape(val)
                pattern = "^" + escaped.replace("%", ".*").replace("_", ".") + "$"
                return s.astype(str).str.match(pattern, flags=re.IGNORECASE, na=False)

            raise InvalidFilterException(message=f"Unsupported operator: {op}", details={"operator": op})

        def _apply_filters(local_df: "pd.DataFrame", spec: Any) -> "pd.DataFrame":
            """Aplica filtros deterministas soportando AND/OR (y AND implícito para listas)."""
            if spec is None or spec == []:
                return local_df

            def _mask_for(node: Any) -> "pd.Series":
                if node is None or node == []:
                    return pd.Series([True] * len(local_df), index=local_df.index)
                if isinstance(node, list):
                    m = pd.Series([True] * len(local_df), index=local_df.index)
                    for c in node:
                        m = m & _apply_condition(local_df, c)
                    return m
                if _is_group(node):
                    op2 = str(node.get("op", "AND")).upper()
                    conds2 = node.get("conditions", [])
                    if op2 == "AND":
                        m = pd.Series([True] * len(local_df), index=local_df.index)
                        for c in conds2:
                            m = m & _mask_for(c)
                        return m
                    if op2 == "OR":
                        m = pd.Series([False] * len(local_df), index=local_df.index)
                        for c in conds2:
                            m = m | _mask_for(c)
                        return m
                    raise InvalidFilterException(message=f"Unsupported logical op: {op2}", details={"op": op2})
                if _is_condition(node):
                    return _apply_condition(local_df, node)
                raise InvalidFilterException(details={"filters": node})

            return local_df[_mask_for(spec)]

        _validate_filters(filters_spec)

        # Validar columnas requeridas tempranamente
        required_columns: set[str] = set(columns)
        for filt in _flatten_conditions(filters_spec):
            if isinstance(filt, dict) and "column" in filt:
                required_columns.add(filt["column"])
        if group_by:
            required_columns.update(group_by)

        # Columnas implicadas por métricas (para validación de NaNs / tipos)
        metric_columns: set[str] = set()
        for metric in metrics:
            expr = str(metric.get("sql", ""))
            expr_u = expr.strip().upper()
            if "COUNT(DISTINCT CUSTOMER_ID)" in expr_u and "FILTER" in expr_u and "ORDER_COUNT" in expr_u:
                metric_columns.add("customer_id")
            m = re.search(r"^(COUNT|SUM|AVG)\s*\(\s*(DISTINCT\s+)?([A-Z0-9_]+)\s*\)", expr_u)
            if m:
                metric_columns.add(m.group(3).lower())

        required_columns.update(metric_columns)

        # Algunos CSV pueden incluir espacios; normalizamos solo para matching exacto (sin mutar nombres)
        missing = [c for c in required_columns if c and c not in df.columns]
        if missing:
            raise KeyError(f"Missing columns in '{table_name}': {missing}")

        # Validación de NaNs (estricta) sobre columnas referenciadas
        for c in sorted(required_columns):
            if c and c in df.columns:
                nulls = int(df[c].isna().sum())
                if nulls:
                    raise TypeMismatchException(
                        message=f"Column '{c}' contains null/NaN values.",
                        details={"column": c, "null_count": nulls},
                    )

        # Aplicar filtros deterministas (AND/OR)
        df = _apply_filters(df, filters_spec)
        if df.empty:
            raise EmptyResultException(details={"table": table_name, "filters": filters_spec})

        def _apply_compare_periods(local_df: "pd.DataFrame") -> "pd.DataFrame":
            if not time_column or not time_grain or not isinstance(baseline_period, dict) or not isinstance(compare_period, dict):
                return local_df
            rel_base = str(baseline_period.get("relative", "")).lower()
            rel_comp = str(compare_period.get("relative", "")).lower()

            grain = str(time_grain).lower()
            if grain not in {"day", "week", "month"}:
                return local_df

            dt = _ensure_datetime_column(local_df, time_column)
            if dt.isna().all():
                raise TypeMismatchException(message=f"Column '{time_column}' contains only null/NaN values.", details={"column": time_column})

            max_dt = dt.max()
            if grain == "month":
                cur = max_dt.to_period("M")
                mapping = {
                    "current_month": cur,
                    "previous_month": cur - 1,
                    "same_month_last_year": cur - 12,
                }
                base_p = mapping.get(rel_base)
                comp_p = mapping.get(rel_comp)
                bucket_col = f"{time_column}__month"
                if bucket_col not in local_df.columns:
                    local_df[bucket_col] = dt.dt.to_period("M").astype(str)
                allowed = {p for p in [base_p, comp_p] if p is not None}
                if not allowed:
                    return local_df
                allowed_str = {str(p) for p in allowed}
                return local_df[local_df[bucket_col].isin(allowed_str)]

            if grain == "week":
                cur = max_dt.to_period("W-MON")
                mapping = {
                    "current_week": cur,
                    "previous_week": cur - 1,
                }
                base_p = mapping.get(rel_base)
                comp_p = mapping.get(rel_comp)
                bucket_col = f"{time_column}__week"
                if bucket_col not in local_df.columns:
                    p = dt.dt.to_period("W-MON")
                    local_df[bucket_col] = p.apply(lambda x: x.start_time.strftime("%Y-%m-%d"))
                allowed = {p for p in [base_p, comp_p] if p is not None}
                if not allowed:
                    return local_df
                allowed_start = {p.start_time.strftime("%Y-%m-%d") for p in allowed}
                return local_df[local_df[bucket_col].isin(allowed_start)]

            # day
            cur = max_dt.normalize()
            mapping = {
                "current_day": cur,
                "previous_day": cur - pd.Timedelta(days=1),
            }
            base_d = mapping.get(rel_base)
            comp_d = mapping.get(rel_comp)
            bucket_col = f"{time_column}__day"
            if bucket_col not in local_df.columns:
                local_df[bucket_col] = dt.dt.strftime("%Y-%m-%d")
            allowed = {d for d in [base_d, comp_d] if d is not None}
            if not allowed:
                return local_df
            allowed_str = {d.strftime("%Y-%m-%d") for d in allowed}
            return local_df[local_df[bucket_col].isin(allowed_str)]

        df = _apply_compare_periods(df)
        if df.empty:
            raise EmptyResultException(
                details={
                    "table": table_name,
                    "filters": filters_spec,
                    "baseline_period": baseline_period,
                    "compare_period": compare_period,
                    "time_column": time_column,
                    "time_grain": time_grain,
                }
            )

        def _parse_agg(expr: str) -> tuple[str, str, bool]:
            """Retorna (func, col, distinct). Soporta COUNT/SUM/AVG y COUNT(DISTINCT col)."""
            expr_u = expr.strip().upper()
            m = re.search(r"^(COUNT|SUM|AVG)\s*\(\s*(DISTINCT\s+)?([A-Z0-9_]+)\s*\)", expr_u)
            if not m:
                raise ValueError(f"Unsupported metric expression: {expr}")
            func = m.group(1)
            distinct = bool(m.group(2))
            col = m.group(3).lower()
            return func, col, distinct

        def _compute_metric(series_or_df, expr: str, group_keys: list[str] | None):
            """Computa una métrica en df o grouped de forma determinista."""
            expr_u = expr.strip().upper()

            # Caso especial soportado por DD v1: clientes con >1 orden
            if "COUNT(DISTINCT CUSTOMER_ID)" in expr_u and "FILTER" in expr_u and "ORDER_COUNT" in expr_u:
                # Semántica: contar clientes con más de una fila (después de filtros)
                if group_keys:
                    # Por grupo, contar clientes con count>1 dentro de cada grupo
                    def per_group(g):
                        counts = g["customer_id"].value_counts(dropna=False)
                        return int((counts > 1).sum())

                    return series_or_df.apply(per_group)

                counts = series_or_df["customer_id"].value_counts(dropna=False)
                return int((counts > 1).sum())

            func, col, distinct = _parse_agg(expr)
            if group_keys:
                grouped = series_or_df
                if distinct and func == "COUNT":
                    return grouped[col].nunique()
                if func == "COUNT":
                    return grouped[col].count()
                if func == "SUM":
                    return grouped[col].sum()
                if func == "AVG":
                    return grouped[col].mean()

            # Global
            df_local = series_or_df
            if distinct and func == "COUNT":
                return int(df_local[col].nunique())
            if func == "COUNT":
                return int(df_local[col].count())
            if func == "SUM":
                s = _coerce_numeric(df_local[col], col)
                return float(s.sum())
            if func == "AVG":
                s = _coerce_numeric(df_local[col], col)
                return float(s.mean())
            raise ValueError(f"Unsupported metric expression: {expr}")
        
        # Calcular métricas o seleccionar columnas
        if metrics:
            # Agrupar si es necesario
            if group_by:
                grouped = df.groupby(group_by)
                result_data = {}
                
                # Agregar columnas de group_by
                for col in group_by:
                    result_data[col] = grouped[col].first().values
                
                # Calcular cada métrica
                for metric in metrics:
                    metric_name = metric["name"]
                    sql_expr = metric.get("sql", "")

                    result_data[metric_name] = _compute_metric(grouped, sql_expr, group_by).values
                
                result_df = pd.DataFrame(result_data)
            else:
                # Sin group_by, calcular métricas agregadas globales
                result_data = {}
                
                for metric in metrics:
                    metric_name = metric["name"]
                    sql_expr = metric.get("sql", "")

                    result_data[metric_name] = [_compute_metric(df, sql_expr, None)]
                
                result_df = pd.DataFrame(result_data)
        else:
            # Solo seleccionar columnas
            result_df = df[columns] if columns else df
        
        # Ordenar
        if order_by:
            sort_columns = [item["column"] for item in order_by]
            ascending = [item.get("direction", "ASC") == "ASC" for item in order_by]
            result_df = result_df.sort_values(by=sort_columns, ascending=ascending)
        elif group_by:
            # Orden determinista por la primera clave de group_by si no se especificó order_by
            result_df = result_df.sort_values(by=[group_by[0]], ascending=True)
        
        # Aplicar limit con tracking de truncación
        rows_before_limit = len(result_df)
        result_df = result_df.head(limit)
        rows_truncated = rows_before_limit > len(result_df)
        
        if rows_truncated:
            logger.warning(
                f"[run_table_query] Results truncated: {rows_before_limit} -> {len(result_df)} rows (limit={limit})"
            )
        
        # Convertir a formato de salida
        execution_time_ms = (time.time() - start_time) * 1000

        schema_out = {c: str(result_df[c].dtype) for c in result_df.columns}

        table_id = f"t_{uuid4().hex[:8]}"

        TABLE_STORE.put(
            TableResult(
                table_id=table_id,
                columns=result_df.columns.tolist(),
                rows=result_df.values.tolist(),
                row_count=len(result_df),
                rows_count=len(result_df),
                schema=schema_out,
            )
        )
        
        final_result = {
            "table_id": table_id,
            "columns": result_df.columns.tolist(),
            "rows": result_df.values.tolist(),
            "row_count": len(result_df),
            "rows_count": len(result_df),
            "rows_before_limit": rows_before_limit,
            "rows_truncated": rows_truncated,
            "data_source": data_source,
            "schema": schema_out,
            "execution_time_ms": execution_time_ms,
            "cache_hit": False,
            "result_metadata": input_data.get("result_metadata", {})
        }

        # Guardar en Cache
        _QUERY_CACHE[cache_key] = (
            now + timedelta(seconds=_CACHE_TTL_SECONDS),
            final_result.copy()
        )
        
        return final_result


__all__ = ["RunTableQueryTool"]
