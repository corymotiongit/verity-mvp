"""Document Interpreter Agent (DIA) - Schema inference using Gemini API.

Analyzes CSV/Excel files to produce JSON schema with:
- Column names, types, roles (metric/entity/time/filter)
- Allowed operators per column
- Confidence scores
"""

import csv
import logging
from pathlib import Path

from verity.core.gemini import get_gemini_client
from verity.exceptions import ExternalServiceException
from verity.tools.document_interpreter.schemas import ColumnSchema, DIAInferenceResult

logger = logging.getLogger(__name__)


def infer_schema_from_csv(
    file_path: str | Path,
    table_name: str,
    sample_rows: int = 10,
) -> DIAInferenceResult:
    """
    Infer schema from CSV file using Gemini API.

    Args:
        file_path: Path to CSV file
        table_name: Name for the table (from filename)
        sample_rows: Number of rows to sample for inference (default 10)

    Returns:
        DIAInferenceResult with inferred columns, types, roles

    Raises:
        ExternalServiceException: If Gemini API fails
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    logger.info(f"[DIA] Inferring schema from {file_path} (sample_rows={sample_rows})")

    # Read header + sample rows
    try:
        with file_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            samples = [row for _, row in zip(range(sample_rows), reader)]
            row_count = sum(1 for _ in reader) + len(samples)  # Remaining + sampled
    except Exception as e:
        logger.error(f"[DIA] Failed to read CSV: {e}")
        raise ValueError(f"Invalid CSV file: {e}")

    if not headers:
        raise ValueError("CSV file has no headers")

    logger.info(f"[DIA] Found {len(headers)} columns, {row_count} rows")

    # Build prompt for Gemini
    prompt = _build_inference_prompt(table_name, headers, samples)

    # Call Gemini API
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )

        # Parse JSON response
        import json

        result = json.loads(response.text)
        columns = [ColumnSchema(**col) for col in result["columns"]]

        logger.info(
            f"[DIA] Inferred {len(columns)} columns with avg confidence {result['confidence_avg']:.2f}"
        )

        return DIAInferenceResult(
            table_name=table_name,
            columns=columns,
            row_count=row_count,
            confidence_avg=result["confidence_avg"],
            inference_method="gemini-analysis",
        )

    except Exception as e:
        logger.error(f"[DIA] Gemini API failed: {e}")
        # Fallback to heuristic inference
        return _fallback_heuristic_inference(table_name, headers, samples, row_count)


def _build_inference_prompt(
    table_name: str, headers: list[str], samples: list[dict]
) -> str:
    """Build prompt for Gemini schema inference."""
    sample_text = "\n".join(
        [f"Row {i+1}: {row}" for i, row in enumerate(samples[:5])]  # Max 5 rows
    )

    return f"""Analyze this CSV table and infer the schema for each column.

Table: {table_name}
Columns: {', '.join(headers)}

Sample data (first 5 rows):
{sample_text}

For each column, determine:
1. data_type: "string", "integer", "float", "boolean", or "datetime"
2. role: "metric" (numeric aggregatable), "entity" (categorical groupable), "time" (date/time), or "filter" (low-cardinality categorical)
3. allowed_ops: list of valid operators (e.g., ["SUM", "AVG", "COUNT"] for metrics, ["=", "IN", "LIKE"] for filters)
4. sample_values: up to 5 unique sample values from the data
5. confidence: 0.0-1.0 score for inference certainty

Rules:
- Metrics: numeric columns typically aggregated (sales, revenue, quantity, count, etc.)
- Entities: categorical columns used for grouping (product, customer, category, id, etc.)
- Time: date/datetime columns (date, timestamp, year, month, etc.)
- Filters: low-cardinality categorical (status, type, flag, boolean, etc.)

Return JSON:
{{
  "columns": [
    {{
      "name": "column_name",
      "data_type": "string|integer|float|boolean|datetime",
      "role": "metric|entity|time|filter",
      "allowed_ops": ["OP1", "OP2"],
      "sample_values": ["val1", "val2"],
      "confidence": 0.95
    }}
  ],
  "confidence_avg": 0.90
}}"""


def _fallback_heuristic_inference(
    table_name: str, headers: list[str], samples: list[dict], row_count: int
) -> DIAInferenceResult:
    """Fallback heuristic inference when Gemini API fails."""
    logger.warning("[DIA] Using fallback heuristic inference")

    columns = []
    for header in headers:
        # Collect sample values
        sample_vals = [row.get(header, "") for row in samples[:5]]
        sample_vals = [str(v) for v in sample_vals if v]

        # Heuristic type detection
        data_type = _infer_type_heuristic(sample_vals)
        role = _infer_role_heuristic(header, data_type)
        allowed_ops = _infer_ops_heuristic(role)

        columns.append(
            ColumnSchema(
                name=header,
                data_type=data_type,
                role=role,
                allowed_ops=allowed_ops,
                sample_values=sample_vals[:5],
                confidence=0.6,  # Lower confidence for heuristic
            )
        )

    avg_confidence = sum(c.confidence for c in columns) / len(columns) if columns else 0.0

    return DIAInferenceResult(
        table_name=table_name,
        columns=columns,
        row_count=row_count,
        confidence_avg=avg_confidence,
        inference_method="fallback-heuristic",
    )


def _infer_type_heuristic(sample_values: list[str]) -> str:
    """Infer data type from sample values."""
    if not sample_values:
        return "string"

    # Try integer
    try:
        all(int(v) for v in sample_values if v)
        return "integer"
    except ValueError:
        pass

    # Try float
    try:
        all(float(v) for v in sample_values if v)
        return "float"
    except ValueError:
        pass

    # Try boolean
    bool_vals = {"true", "false", "1", "0", "yes", "no"}
    if all(v.lower() in bool_vals for v in sample_values if v):
        return "boolean"

    # Try datetime (simple check for date-like patterns)
    if any(c in sample_values[0] for c in ["-", "/", ":"]) if sample_values else False:
        return "datetime"

    return "string"


def _infer_role_heuristic(column_name: str, data_type: str) -> str:
    """Infer semantic role from column name and type."""
    name_lower = column_name.lower()

    # Time indicators
    if any(t in name_lower for t in ["date", "time", "timestamp", "year", "month", "day"]):
        return "time"

    # Metric indicators (numeric + aggregatable keywords)
    if data_type in ["integer", "float"]:
        metric_keywords = [
            "amount",
            "total",
            "sum",
            "count",
            "revenue",
            "sales",
            "price",
            "cost",
            "quantity",
            "qty",
            "number",
            "value",
        ]
        if any(k in name_lower for k in metric_keywords):
            return "metric"

    # Entity indicators (id, name, category)
    if any(e in name_lower for e in ["id", "name", "category", "product", "customer", "user"]):
        return "entity"

    # Filter indicators (status, type, flag)
    if any(f in name_lower for f in ["status", "type", "flag", "is_", "has_"]):
        return "filter"

    # Default: entity for categorical, metric for numeric
    return "entity" if data_type == "string" else "metric"


def _infer_ops_heuristic(role: str) -> list[str]:
    """Infer allowed operators based on role."""
    ops_map = {
        "metric": ["SUM", "AVG", "MIN", "MAX", "COUNT"],
        "entity": ["=", "IN", "LIKE", "GROUP_BY"],
        "time": ["=", ">", "<", ">=", "<=", "BETWEEN"],
        "filter": ["=", "IN", "!="],
    }
    return ops_map.get(role, ["="])
