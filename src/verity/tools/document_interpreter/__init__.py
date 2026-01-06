"""Document Interpreter Agent (DIA) - Generic schema inference from uploaded files."""

from verity.tools.document_interpreter.dia import infer_schema_from_csv
from verity.tools.document_interpreter.schemas import ColumnSchema, DIAInferenceResult

__all__ = ["infer_schema_from_csv", "ColumnSchema", "DIAInferenceResult"]
