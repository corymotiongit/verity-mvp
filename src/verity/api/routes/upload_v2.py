"""
Verity Upload v2 - Router.

Generic file upload endpoint with schema inference preparation.
Part of PR1: Upload + Storage + Metadata for generic dataset support.
"""

import hashlib
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from verity.auth import get_current_user
from verity.auth.schemas import User
from verity.api.routes.upload_v2_schemas import (
    UploadResponse,
    UploadMetadata,
    TableInfo,
)
from verity.tools.document_interpreter import infer_schema_from_csv

router = APIRouter(prefix="/api/v2", tags=["upload-v2"])

logger = logging.getLogger(__name__)

# Base upload directory
UPLOAD_BASE = Path("uploads")
UPLOAD_BASE.mkdir(exist_ok=True)


def _generate_table_id(filename: str, content: bytes) -> str:
    """Generate deterministic table_id from filename + content hash."""
    content_hash = hashlib.sha256(content).hexdigest()[:16]
    return f"{Path(filename).stem}_{content_hash}"


def _count_rows_csv(file_path: Path) -> int:
    """Quick row count for CSV files (header excluded)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1  # Exclude header
    except Exception as e:
        logger.warning(f"Failed to count rows in {file_path}: {e}")
        return 0


def _infer_file_type(filename: str, mime_type: str | None) -> str:
    """Infer file type from extension and MIME type."""
    ext = Path(filename).suffix.lower()
    
    # CSV/Excel detection
    if ext == ".csv" or mime_type == "text/csv":
        return "csv"
    if ext in [".xlsx", ".xls"] or mime_type in [
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    ]:
        return "excel"
    
    # Document types (for future PDF support)
    if ext == ".pdf" or mime_type == "application/pdf":
        return "pdf"
    if ext in [".txt", ".md"] or mime_type == "text/plain":
        return "text"
    
    return "unknown"


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_file(
    user: User = Depends(get_current_user),
    file: UploadFile = File(..., description="File to upload (CSV, Excel, PDF, etc.)"),
    table_name: str | None = Form(default=None, description="Optional friendly name for the table"),
    conversation_id: str | None = Form(default=None, description="Optional conversation scope"),
):
    """
    Upload a file for schema inference and query processing.
    
    **Flow:**
    1. Store file in `uploads/{conversation_id}/{table_id}/`
    2. Generate metadata (row count, file type, etc.)
    3. Return table_id + metadata for next step (DIA inference in PR2)
    
    **Supported formats:**
    - CSV (.csv)
    - Excel (.xlsx, .xls)
    - PDF (.pdf) - future
    - Text (.txt, .md) - future
    
    **Returns:**
    - `table_id`: Unique identifier for this table (hash-based)
    - `metadata`: File info, row count, paths
    - `inference_status`: Always "pending" (PR2 will implement DIA)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Generate table_id (deterministic)
    table_id = _generate_table_id(file.filename, content)
    
    # Determine conversation scope (default to user-specific)
    conv_id = conversation_id or f"user_{user.id}"
    
    # Create storage directory: uploads/{conversation_id}/{table_id}/
    storage_dir = UPLOAD_BASE / conv_id / table_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = storage_dir / file.filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    logger.info(
        f"[upload_v2] Saved file: {file.filename} -> {file_path} "
        f"(table_id={table_id}, user={user.id}, org={user.org_id})"
    )
    
    # Infer file type
    file_type = _infer_file_type(file.filename, file.content_type)
    
    # Quick row count (CSV only for now)
    row_count = 0
    if file_type == "csv":
        row_count = _count_rows_csv(file_path)
    
    # Build metadata
    metadata = UploadMetadata(
        filename=file.filename,
        original_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        file_type=file_type,
        size_bytes=len(content),
        row_count=row_count,
        storage_path=str(file_path.relative_to(UPLOAD_BASE)),
        conversation_id=conv_id,
        created_at=datetime.now(timezone.utc),
        created_by=user.id,
    )
    
    # Table info (friendly name defaults to filename stem)
    friendly_name = table_name or Path(file.filename).stem
    table_info = TableInfo(
        table_id=table_id,
        table_name=friendly_name,
        file_type=file_type,
        row_count=row_count,
    )
    
    # DIA: Infer schema (CSV only for now)
    inferred_schema = None
    inference_status = "not_supported"
    inference_message = "Schema inference not supported for this file type"
    
    if file_type == "csv":
        try:
            logger.info(f"[upload_v2] Running DIA schema inference for {file.filename}")
            dia_result = infer_schema_from_csv(
                file_path=file_path,
                table_name=friendly_name,
                sample_rows=10,
            )
            
            inferred_schema = {
                "table_name": dia_result.table_name,
                "columns": [col.model_dump() for col in dia_result.columns],
                "row_count": dia_result.row_count,
                "confidence_avg": dia_result.confidence_avg,
                "inference_method": dia_result.inference_method,
            }
            
            inference_status = "completed"
            inference_message = (
                f"Schema inferred: {len(dia_result.columns)} columns, "
                f"avg confidence {dia_result.confidence_avg:.2%}"
            )
            
            logger.info(
                f"[upload_v2] DIA success: {len(dia_result.columns)} columns, "
                f"method={dia_result.inference_method}, confidence={dia_result.confidence_avg:.2f}"
            )
            
        except Exception as e:
            logger.error(f"[upload_v2] DIA failed: {e}")
            inference_status = "failed"
            inference_message = f"Schema inference failed: {str(e)}"
    
    # Return response
    return UploadResponse(
        table_id=table_id,
        table_info=table_info,
        metadata=metadata,
        inferred_schema=inferred_schema,
        inference_status=inference_status,
        message=inference_message,
    )


@router.get("/upload/{table_id}", response_model=UploadResponse)
async def get_upload_metadata(
    table_id: str,
    user: User = Depends(get_current_user),
    conversation_id: str | None = None,
):
    """
    Get metadata for a previously uploaded file.
    
    **Note**: This is a placeholder for PR2 (when we persist metadata in DB/cache).
    For now, returns 404 if file not found in filesystem.
    """
    conv_id = conversation_id or f"user_{user.id}"
    storage_dir = UPLOAD_BASE / conv_id / table_id
    
    if not storage_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Table {table_id} not found in conversation {conv_id}",
        )
    
    # Find the file (should be only one)
    files = list(storage_dir.glob("*"))
    if not files:
        raise HTTPException(
            status_code=404,
            detail=f"No files found for table {table_id}",
        )
    
    file_path = files[0]
    file_type = _infer_file_type(file_path.name, None)
    row_count = 0
    if file_type == "csv":
        row_count = _count_rows_csv(file_path)
    
    metadata = UploadMetadata(
        filename=file_path.name,
        original_name=file_path.name,
        mime_type="application/octet-stream",
        file_type=file_type,
        size_bytes=file_path.stat().st_size,
        row_count=row_count,
        storage_path=str(file_path.relative_to(UPLOAD_BASE)),
        conversation_id=conv_id,
        created_at=datetime.fromtimestamp(file_path.stat().st_ctime, tz=timezone.utc),
        created_by=user.id,
    )
    
    table_info = TableInfo(
        table_id=table_id,
        table_name=file_path.stem,
        file_type=file_type,
        row_count=row_count,
    )
    
    return UploadResponse(
        table_id=table_id,
        table_info=table_info,
        metadata=metadata,
        inference_status="pending",
        message="Metadata retrieved from filesystem (PR1 implementation)",
    )
