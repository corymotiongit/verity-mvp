"""DIA Schemas - Column schema inference results."""

from typing import Literal

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Schema for a single column inferred by DIA."""

    name: str = Field(description="Column name from CSV header")
    data_type: Literal["string", "integer", "float", "boolean", "datetime"] = Field(
        description="Inferred data type"
    )
    role: Literal["metric", "entity", "time", "filter"] = Field(
        description="Semantic role in analytics queries"
    )
    allowed_ops: list[str] = Field(
        default_factory=list,
        description="Allowed operators (e.g., ['SUM', 'AVG'] for metrics, ['=', 'IN'] for filters)",
    )
    sample_values: list[str] = Field(
        default_factory=list, description="Sample values for reference (max 5)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for type/role inference (0-1)",
    )


class DIAInferenceResult(BaseModel):
    """Result of DIA schema inference."""

    table_name: str = Field(description="Table name (from filename)")
    columns: list[ColumnSchema] = Field(description="Inferred column schemas")
    row_count: int = Field(description="Total rows in file (excluding header)")
    confidence_avg: float = Field(
        ge=0.0,
        le=1.0,
        description="Average confidence across all columns",
    )
    inference_method: str = Field(
        default="gemini-analysis",
        description="Method used for inference (gemini-analysis, fallback-heuristic)",
    )
