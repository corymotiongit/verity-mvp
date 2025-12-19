"""
Verity Data Engine - Schemas

Pydantic models for the data execution pipeline.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class DatasetProfile(BaseModel):
    """Complete profile of a dataset for LLM context."""
    
    dataset_id: str
    filename: str
    shape: tuple[int, int]
    columns: List[str]
    dtypes: Dict[str, str]
    head: List[Dict[str, Any]]
    sample: Optional[List[Dict[str, Any]]] = None
    column_analysis: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ValueIndexEntry(BaseModel):
    """Single entry in the value index."""
    
    column: str
    count: int
    sample_values: List[str] = Field(default_factory=list)


class ValueIndex(BaseModel):
    """Index of normalized values to their column mappings."""
    
    dataset_id: str
    entries: Dict[str, List[ValueIndexEntry]] = Field(default_factory=dict)
    
    def lookup(self, token: str) -> Optional[List[ValueIndexEntry]]:
        """Lookup a normalized token."""
        normalized = token.lower().strip()
        return self.entries.get(normalized)


class ResolvedFilter(BaseModel):
    """A filter resolved from user intent."""
    
    column: str
    value: str
    confidence: float = 1.0


class CodeExecutionRequest(BaseModel):
    """Request to execute generated Python code on a dataframe."""
    
    dataset_id: str
    code: str = Field(..., description="Python code using 'df' and assigning final answer to 'result'")
    resolved_filters: List[ResolvedFilter] = Field(default_factory=list)
    attempt: int = 1


class CodeExecutionResult(BaseModel):
    """Result of the code execution."""
    
    success: bool
    value: Any = None
    table_preview: Optional[Dict[str, Any]] = None  # {"columns": [...], "rows": [...], "total_rows": int}
    logs: str = ""
    error: Optional[str] = None
    executed_code: str = ""
    execution_time_ms: int = 0
    
    # Row tracking for audit
    row_ids: List[int] = []  # 1-indexed line numbers from canonical file
    row_count: int = 0  # Total matching rows
    sample_rows: List[Dict[str, Any]] = []  # 1-3 sample rows for audit


class TablePreview(BaseModel):
    """Structured table data for frontend rendering."""
    columns: List[str]
    rows: List[List[Any]]
    total_rows: int = 0  # Original row count before truncation


class DataEngineResponse(BaseModel):
    """Standard response from the Data Engine."""
    
    answer: str
    answer_type: str = "text"  # "text", "scalar", "table"
    table_preview: Optional[TablePreview] = None
    table_markdown: Optional[str] = None  # Top 10 for chat display
    chart_spec: Optional[Dict[str, Any]] = None
    source: str = "data_engine"
    dataset_id: Optional[str] = None
    
    # Audit-ready evidence
    evidence_ref: Optional[str] = None  # Human readable trace of how data was derived
    operation: Optional[str] = None  # "lookup", "aggregate", "filter", "count", "list"
    match_policy: str = "all"  # "first", "all", "error_if_multiple"
    filters_applied: Optional[List[str]] = None
    columns_used: List[str] = []
    
    # Row Evidence (REQUIRED for audit)
    row_ids: List[int] = []  # Line numbers (1-indexed, relative to canonical)
    row_count: int = 0  # Total matching rows
    row_limit: Optional[int] = None  # If truncated
    
    # Sample Rows (1-3 for visual audit)
    sample_rows: List[Dict[str, Any]] = []
    
    # Value Info (for scalar results)
    raw_value: Optional[Any] = None
    value_type: Optional[str] = None  # "number", "text", "date"
    unit: Optional[str] = None  # "MXN", "USD", etc.
    
    # Internal only (not exposed in API serialization)
    executed_code: Optional[str] = None


class ChartAxis(BaseModel):
    field: str
    type: str  # category|date|number
    label: str


class ChartSort(BaseModel):
    by: str  # y|x
    order: str  # asc|desc


class ChartLimits(BaseModel):
    top_n: int
    others: bool


class ChartFormat(BaseModel):
    type: str  # currency|percent|number
    unit: Optional[str] = None
    decimals: int = 0


class ChartSpec(BaseModel):
    version: str = "1.0"
    chart_type: str  # bar|line|stacked_bar|scatter|heatmap|treemap
    title: str
    subtitle: Optional[str] = None
    x: ChartAxis
    y: ChartAxis
    series: Optional[ChartAxis] = None
    sort: Optional[ChartSort] = None
    limits: Optional[ChartLimits] = None
    format: Optional[ChartFormat] = None
    tooltips: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ChartGenerationResponse(BaseModel):
    needs_recalc: bool
    recalc_request: Optional[str] = None
    chart_spec: Optional[ChartSpec] = None


