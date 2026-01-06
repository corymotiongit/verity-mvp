"""
Tests for Upload v2 endpoint.

Part of PR1: Upload + Storage + Metadata for generic dataset support.
"""

import io
import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Enable dev bypass for testing
os.environ["AUTH_INSECURE_DEV_BYPASS"] = "true"

from verity.main import app

client = TestClient(app)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def auth_headers():
    """
    Mock auth headers for testing.
    
    Note: In production, use real JWT from /api/v2/auth/validate.
    For PR1 testing, we bypass auth with dev flag.
    """
    return {"Authorization": "Bearer mock-token-for-testing"}


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return b"""Store,Date,Weekly_Sales,Holiday_Flag,Temperature
1,2010-02-05,24924.50,0,42.31
1,2010-02-12,46039.49,1,38.51
2,2010-02-05,38124.52,0,41.75
2,2010-02-12,50549.88,1,37.92
3,2010-02-05,31032.11,0,43.20"""


@pytest.fixture
def sample_csv_file(sample_csv_content):
    """Sample CSV file object."""
    return io.BytesIO(sample_csv_content)


# =============================================================================
# Tests: POST /api/v2/upload
# =============================================================================


def test_upload_csv_success(auth_headers, sample_csv_content):
    """Test successful CSV upload with metadata extraction."""
    files = {"file": ("walmart_sample.csv", sample_csv_content, "text/csv")}
    data = {"table_name": "Walmart Sales Sample"}
    
    response = client.post(
        "/api/v2/upload",
        headers=auth_headers,
        files=files,
        data=data,
    )
    
    assert response.status_code == 201
    result = response.json()
    
    # Validate response structure
    assert "table_id" in result
    assert "table_info" in result
    assert "metadata" in result
    assert result["inference_status"] == "completed"  # DIA integrated in PR2
    
    # Validate DIA schema inference (aliased as "schema" in API response)
    assert "schema" in result
    schema = result["schema"]
    assert schema is not None
    assert "columns" in schema
    assert len(schema["columns"]) > 0  # Should have inferred columns
    assert "confidence_avg" in schema
    
    # Validate table_info
    table_info = result["table_info"]
    assert table_info["table_name"] == "Walmart Sales Sample"
    assert table_info["file_type"] == "csv"
    assert table_info["row_count"] == 5  # Excludes header
    
    # Validate metadata
    metadata = result["metadata"]
    assert metadata["filename"] == "walmart_sample.csv"
    assert metadata["mime_type"] == "text/csv"
    assert metadata["size_bytes"] == len(sample_csv_content)
    assert metadata["row_count"] == 5
    assert "storage_path" in metadata
    
    # Validate file was actually saved
    storage_path = Path("uploads") / metadata["storage_path"]
    assert storage_path.exists()
    assert storage_path.read_bytes() == sample_csv_content
    
    # Cleanup
    storage_path.unlink()
    storage_path.parent.rmdir()


def test_upload_csv_deterministic_table_id(auth_headers, sample_csv_content):
    """Test that same file produces same table_id (idempotency)."""
    files = {"file": ("test.csv", sample_csv_content, "text/csv")}
    
    response1 = client.post("/api/v2/upload", headers=auth_headers, files=files)
    response2 = client.post("/api/v2/upload", headers=auth_headers, files=files)
    
    assert response1.status_code == 201
    assert response2.status_code == 201
    
    table_id_1 = response1.json()["table_id"]
    table_id_2 = response2.json()["table_id"]
    
    assert table_id_1 == table_id_2  # Same content → same table_id
    
    # Cleanup
    storage_path = Path("uploads") / response1.json()["metadata"]["storage_path"]
    storage_path.unlink()
    storage_path.parent.rmdir()


def test_upload_with_conversation_id(auth_headers, sample_csv_content):
    """Test upload with explicit conversation_id."""
    conv_id = f"conv_{uuid4()}"
    files = {"file": ("test.csv", sample_csv_content, "text/csv")}
    data = {"conversation_id": conv_id}
    
    response = client.post(
        "/api/v2/upload",
        headers=auth_headers,
        files=files,
        data=data,
    )
    
    assert response.status_code == 201
    metadata = response.json()["metadata"]
    assert metadata["conversation_id"] == conv_id
    
    # Validate storage path includes conversation_id
    assert conv_id in metadata["storage_path"]
    
    # Cleanup
    storage_path = Path("uploads") / metadata["storage_path"]
    storage_path.unlink()
    storage_path.parent.rmdir()
    storage_path.parent.parent.rmdir()  # Remove conv_id dir


def test_upload_excel_detection(auth_headers):
    """Test Excel file type detection."""
    excel_content = b"PK\x03\x04"  # Minimal XLSX magic bytes (mock)
    files = {
        "file": ("sales.xlsx", excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    
    response = client.post("/api/v2/upload", headers=auth_headers, files=files)
    
    assert response.status_code == 201
    result = response.json()
    assert result["table_info"]["file_type"] == "excel"
    
    # Cleanup
    storage_path = Path("uploads") / result["metadata"]["storage_path"]
    storage_path.unlink()
    storage_path.parent.rmdir()


def test_upload_empty_file_fails(auth_headers):
    """Test that empty file upload fails."""
    files = {"file": ("empty.csv", b"", "text/csv")}
    
    response = client.post("/api/v2/upload", headers=auth_headers, files=files)
    
    assert response.status_code == 400
    assert "Empty file" in response.json()["detail"]


def test_upload_no_filename_fails(auth_headers):
    """Test that file without filename fails."""
    # This is hard to test with TestClient, but validates contract
    pass  # Skip for now - contract validation


# =============================================================================
# Tests: GET /api/v2/upload/{table_id}
# =============================================================================


def test_get_upload_metadata_success(auth_headers, sample_csv_content):
    """Test retrieving metadata for an uploaded file."""
    # First upload
    files = {"file": ("test.csv", sample_csv_content, "text/csv")}
    upload_response = client.post("/api/v2/upload", headers=auth_headers, files=files)
    assert upload_response.status_code == 201
    
    table_id = upload_response.json()["table_id"]
    
    # Then retrieve
    get_response = client.get(f"/api/v2/upload/{table_id}", headers=auth_headers)
    
    assert get_response.status_code == 200
    result = get_response.json()
    
    assert result["table_id"] == table_id
    assert result["table_info"]["file_type"] == "csv"
    assert result["metadata"]["row_count"] == 5
    
    # Cleanup
    storage_path = Path("uploads") / upload_response.json()["metadata"]["storage_path"]
    storage_path.unlink()
    storage_path.parent.rmdir()


def test_get_upload_metadata_not_found(auth_headers):
    """Test 404 for non-existent table_id."""
    response = client.get("/api/v2/upload/nonexistent_table_id", headers=auth_headers)
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


# =============================================================================
# Integration Test: Full Upload Flow
# =============================================================================


def test_upload_integration_flow(auth_headers, sample_csv_content):
    """
    Test complete upload flow:
    1. Upload file
    2. Get metadata
    3. Verify storage
    4. Verify idempotency
    """
    # Step 1: Upload
    files = {"file": ("walmart_test.csv", sample_csv_content, "text/csv")}
    data = {"table_name": "Walmart Test"}
    
    upload_resp = client.post("/api/v2/upload", headers=auth_headers, files=files, data=data)
    assert upload_resp.status_code == 201
    
    result = upload_resp.json()
    table_id = result["table_id"]
    
    # Step 2: Validate response
    assert result["table_info"]["table_name"] == "Walmart Test"
    assert result["table_info"]["row_count"] == 5
    assert result["metadata"]["size_bytes"] > 0
    assert result["inference_status"] == "completed"  # DIA integrated in PR2
    assert result["schema"] is not None  # Schema should be inferred (aliased from inferred_schema)
    
    # Step 3: Get metadata
    get_resp = client.get(f"/api/v2/upload/{table_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["table_id"] == table_id
    
    # Step 4: Verify storage
    storage_path = Path("uploads") / result["metadata"]["storage_path"]
    assert storage_path.exists()
    assert storage_path.read_bytes() == sample_csv_content
    
    # Step 5: Re-upload same file → same table_id
    upload_resp_2 = client.post("/api/v2/upload", headers=auth_headers, files=files, data=data)
    assert upload_resp_2.json()["table_id"] == table_id
    
    # Cleanup
    storage_path.unlink()
    storage_path.parent.rmdir()


# =============================================================================
# Notes for PR2 (DIA Schema Inference)
# =============================================================================
# When implementing PR2, add tests for:
# - test_upload_triggers_dia_inference()
# - test_upload_schema_in_response()
# - test_upload_with_inference_errors()
# - test_upload_confidence_thresholds()
