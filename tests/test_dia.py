"""Tests for Document Interpreter Agent (DIA)."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

# Set dev bypass before importing app
os.environ["AUTH_INSECURE_DEV_BYPASS"] = "true"

from verity.tools.document_interpreter import infer_schema_from_csv


@pytest.fixture
def sample_csv():
    """Create a sample CSV file for testing."""
    csv_content = """customer_id,customer_name,order_date,total_amount,quantity,status
1001,Acme Corp,2024-01-15,1500.50,10,completed
1002,TechCo,2024-01-16,2300.75,15,pending
1003,Global Ltd,2024-01-17,950.00,5,completed
1004,StartupX,2024-01-18,3200.25,25,processing
1005,MegaCorp,2024-01-19,1800.00,12,completed
"""
    
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


def test_infer_schema_basic(sample_csv):
    """Test basic schema inference from CSV."""
    result = infer_schema_from_csv(
        file_path=sample_csv,
        table_name="test_orders",
        sample_rows=10,
    )
    
    assert result.table_name == "test_orders"
    assert len(result.columns) == 6
    assert result.row_count == 5
    assert 0.0 <= result.confidence_avg <= 1.0
    
    # Check column names
    column_names = [col.name for col in result.columns]
    assert "customer_id" in column_names
    assert "total_amount" in column_names
    assert "status" in column_names


def test_infer_schema_column_types(sample_csv):
    """Test that DIA correctly infers column types."""
    result = infer_schema_from_csv(
        file_path=sample_csv,
        table_name="test_orders",
        sample_rows=10,
    )
    
    columns_by_name = {col.name: col for col in result.columns}
    
    # customer_id: should be integer
    assert columns_by_name["customer_id"].data_type in ["integer", "string"]
    
    # total_amount: should be float or numeric
    assert columns_by_name["total_amount"].data_type in ["float", "integer"]
    
    # customer_name: should be string
    assert columns_by_name["customer_name"].data_type == "string"
    
    # order_date: should be datetime or string
    assert columns_by_name["order_date"].data_type in ["datetime", "string"]


def test_infer_schema_column_roles(sample_csv):
    """Test that DIA correctly infers semantic roles."""
    result = infer_schema_from_csv(
        file_path=sample_csv,
        table_name="test_orders",
        sample_rows=10,
    )
    
    columns_by_name = {col.name: col for col in result.columns}
    
    # total_amount: should be metric (aggregatable numeric)
    assert columns_by_name["total_amount"].role in ["metric"]
    
    # status: should be filter (low-cardinality categorical)
    assert columns_by_name["status"].role in ["filter", "entity"]
    
    # customer_id or customer_name: should be entity
    assert any(
        col.role == "entity"
        for col in [columns_by_name["customer_id"], columns_by_name["customer_name"]]
    )


def test_infer_schema_allowed_ops(sample_csv):
    """Test that DIA assigns appropriate allowed operators."""
    result = infer_schema_from_csv(
        file_path=sample_csv,
        table_name="test_orders",
        sample_rows=10,
    )
    
    columns_by_name = {col.name: col for col in result.columns}
    
    # Metric columns should have aggregation ops
    total_amount = columns_by_name["total_amount"]
    assert any(op in total_amount.allowed_ops for op in ["SUM", "AVG", "COUNT"])
    
    # Filter columns should have comparison ops
    status = columns_by_name["status"]
    assert any(op in status.allowed_ops for op in ["=", "IN"])


def test_infer_schema_sample_values(sample_csv):
    """Test that DIA captures sample values."""
    result = infer_schema_from_csv(
        file_path=sample_csv,
        table_name="test_orders",
        sample_rows=10,
    )
    
    columns_by_name = {col.name: col for col in result.columns}
    
    # Each column should have sample values
    for col in result.columns:
        assert len(col.sample_values) > 0
        assert len(col.sample_values) <= 5  # Max 5 samples
    
    # Status should have actual values from CSV
    status_samples = columns_by_name["status"].sample_values
    assert any(val in status_samples for val in ["completed", "pending", "processing"])


def test_infer_schema_confidence_scores(sample_csv):
    """Test that DIA produces valid confidence scores."""
    result = infer_schema_from_csv(
        file_path=sample_csv,
        table_name="test_orders",
        sample_rows=10,
    )
    
    # Average confidence should be valid
    assert 0.0 <= result.confidence_avg <= 1.0
    
    # Each column confidence should be valid
    for col in result.columns:
        assert 0.0 <= col.confidence <= 1.0


def test_infer_schema_empty_file():
    """Test that DIA handles empty files gracefully."""
    csv_content = "col1,col2,col3\n"  # Only header, no data
    
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        result = infer_schema_from_csv(
            file_path=temp_path,
            table_name="empty_table",
            sample_rows=10,
        )
        
        # Should still infer columns from header
        assert len(result.columns) == 3
        assert result.row_count == 0
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_infer_schema_file_not_found():
    """Test that DIA raises error for non-existent file."""
    with pytest.raises(FileNotFoundError):
        infer_schema_from_csv(
            file_path="/nonexistent/file.csv",
            table_name="test",
            sample_rows=10,
        )


def test_infer_schema_invalid_csv():
    """Test that DIA handles malformed CSV gracefully."""
    csv_content = "not,valid,csv\nthis\tis\ttab\tseparated"
    
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        # Should still attempt inference
        result = infer_schema_from_csv(
            file_path=temp_path,
            table_name="malformed",
            sample_rows=10,
        )
        
        # Should have inferred something (fallback or partial)
        assert result is not None
        
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_infer_schema_fallback_heuristic():
    """Test that fallback heuristic inference works when Gemini fails."""
    # Create CSV with clear patterns for heuristic inference
    csv_content = """product_id,product_name,price,quantity_sold,is_active
SKU001,Widget A,19.99,100,true
SKU002,Widget B,29.99,150,false
SKU003,Widget C,39.99,75,true
"""
    
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        temp_path = f.name
    
    try:
        result = infer_schema_from_csv(
            file_path=temp_path,
            table_name="products",
            sample_rows=10,
        )
        
        # Even if Gemini fails, fallback should work
        assert result is not None
        assert len(result.columns) == 5
        
        columns_by_name = {col.name: col for col in result.columns}
        
        # Heuristic should detect numeric price as float
        assert columns_by_name["price"].data_type in ["float", "integer"]
        
        # Heuristic should detect boolean
        assert columns_by_name["is_active"].data_type in ["boolean", "string"]
        
    finally:
        Path(temp_path).unlink(missing_ok=True)
