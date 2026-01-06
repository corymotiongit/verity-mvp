"""Tests for PR3: Domain scoping in resolve_semantics.

Validates that when DIA schema is provided, fuzzy matching is scoped
to that schema only (no cross-domain suggestions).
"""

import os
import pytest

# Set dev bypass before importing
os.environ["AUTH_INSECURE_DEV_BYPASS"] = "true"

from verity.tools.resolve_semantics import ResolveSemanticsTool
from verity.exceptions import UnresolvedMetricException


@pytest.fixture
def walmart_dia_schema():
    """DIA schema for Walmart dataset (from audit)."""
    return {
        "table_name": "walmart_sales",
        "columns": [
            {
                "name": "Store",
                "data_type": "integer",
                "role": "entity",
                "allowed_ops": ["=", "IN", "GROUP_BY"],
                "sample_values": ["1", "2", "3"],
                "confidence": 0.95,
            },
            {
                "name": "Weekly_Sales",
                "data_type": "float",
                "role": "metric",
                "allowed_ops": ["SUM", "AVG", "MIN", "MAX"],
                "sample_values": ["24924.50", "46039.49"],
                "confidence": 0.98,
            },
            {
                "name": "Temperature",
                "data_type": "float",
                "role": "metric",
                "allowed_ops": ["AVG", "MIN", "MAX"],
                "sample_values": ["42.31", "38.51"],
                "confidence": 0.92,
            },
            {
                "name": "Fuel_Price",
                "data_type": "float",
                "role": "metric",
                "allowed_ops": ["AVG", "MIN", "MAX"],
                "sample_values": ["2.572", "2.548"],
                "confidence": 0.90,
            },
            {
                "name": "Date",
                "data_type": "datetime",
                "role": "time",
                "allowed_ops": ["=", ">", "<", "BETWEEN"],
                "sample_values": ["05-02-2010", "12-02-2010"],
                "confidence": 0.99,
            },
        ],
        "row_count": 6435,
        "confidence_avg": 0.95,
        "inference_method": "gemini-analysis",
    }


@pytest.fixture
def spotify_dia_schema():
    """DIA schema for Spotify dataset."""
    return {
        "table_name": "spotify_history",
        "columns": [
            {
                "name": "track_name",
                "data_type": "string",
                "role": "entity",
                "allowed_ops": ["=", "IN", "LIKE"],
                "sample_values": ["Song A", "Song B"],
                "confidence": 0.95,
            },
            {
                "name": "artist_name",
                "data_type": "string",
                "role": "entity",
                "allowed_ops": ["=", "IN", "LIKE", "GROUP_BY"],
                "sample_values": ["Artist X", "Artist Y"],
                "confidence": 0.97,
            },
            {
                "name": "play_count",
                "data_type": "integer",
                "role": "metric",
                "allowed_ops": ["SUM", "COUNT", "AVG"],
                "sample_values": ["10", "25", "5"],
                "confidence": 0.99,
            },
            {
                "name": "duration_ms",
                "data_type": "integer",
                "role": "metric",
                "allowed_ops": ["SUM", "AVG"],
                "sample_values": ["180000", "240000"],
                "confidence": 0.93,
            },
        ],
        "row_count": 1500,
        "confidence_avg": 0.96,
        "inference_method": "gemini-analysis",
    }


@pytest.mark.asyncio
async def test_domain_scoping_walmart_only(walmart_dia_schema):
    """Test that with Walmart DIA schema, only Walmart columns are suggested."""
    tool = ResolveSemanticsTool()
    
    # Query that would match Spotify if not scoped
    result = await tool.execute({
        "question": "What are the total sales?",
        "available_tables": ["walmart_sales"],
        "dia_schema": walmart_dia_schema,
    })
    
    # Should resolve to Weekly_Sales from Walmart schema
    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["name"] == "Weekly_Sales"
    assert result["tables"] == ["walmart_sales"]
    
    # Data source should indicate DIA
    assert result["data_dictionary_version"] == "dia-inference"


@pytest.mark.asyncio
async def test_domain_scoping_no_cross_domain(walmart_dia_schema):
    """Test that Spotify-specific terms don't match in Walmart schema."""
    tool = ResolveSemanticsTool()
    
    # This should FAIL because "artist" and "play_count" are not in Walmart schema
    with pytest.raises(UnresolvedMetricException) as exc_info:
        await tool.execute({
            "question": "How many plays by artist?",
            "available_tables": ["walmart_sales"],
            "dia_schema": walmart_dia_schema,
        })
    
    # Error should NOT suggest Spotify columns
    suggestions = exc_info.value.details.get("suggestions", [])
    suggestion_names = [s["metric"] for s in suggestions]
    
    # All suggestions must be from Walmart schema
    walmart_columns = {"Store", "Weekly_Sales", "Temperature", "Fuel_Price", "Date"}
    for name in suggestion_names:
        assert name in walmart_columns, f"Cross-domain suggestion detected: {name}"


@pytest.mark.asyncio
async def test_domain_scoping_spotify_only(spotify_dia_schema):
    """Test that with Spotify DIA schema, only Spotify columns are suggested."""
    tool = ResolveSemanticsTool()
    
    result = await tool.execute({
        "question": "What are the top artists by plays?",
        "available_tables": ["spotify_history"],
        "dia_schema": spotify_dia_schema,
    })
    
    # Debug: print result
    import json
    print("\n" + json.dumps(result, indent=2))
    
    # Should resolve to ranking with count metric
    assert len(result["metrics"]) > 0
    assert result["tables"] == ["spotify_history"]


@pytest.mark.asyncio
async def test_domain_scoping_walmart_temperature(walmart_dia_schema):
    """Test specific Walmart metric resolution."""
    tool = ResolveSemanticsTool()
    
    result = await tool.execute({
        "question": "What's the average temperature?",
        "available_tables": ["walmart_sales"],
        "dia_schema": walmart_dia_schema,
    })
    
    assert len(result["metrics"]) == 1
    assert result["metrics"][0]["name"] == "Temperature"
    assert "AVG" in result["metrics"][0]["allowed_ops"]


@pytest.mark.asyncio
async def test_fallback_to_data_dictionary_when_no_dia():
    """Test that without DIA schema, it falls back to Data Dictionary."""
    tool = ResolveSemanticsTool()
    
    # This should work with Data Dictionary (use more specific query to avoid ambiguity)
    result = await tool.execute({
        "question": "Total number of plays",  # More specific to avoid ambiguous matches
        "available_tables": ["listening_history"],  # Use correct Data Dictionary table
        # No dia_schema parameter - should use Data Dictionary
    })
    
    # Should resolve using Data Dictionary
    assert result["data_dictionary_version"] != "dia-inference"
    assert len(result["metrics"]) > 0


@pytest.mark.asyncio
async def test_dia_schema_confidence_passthrough(walmart_dia_schema):
    """Test that DIA confidence is preserved in output."""
    tool = ResolveSemanticsTool()
    
    result = await tool.execute({
        "question": "Total sales",
        "available_tables": ["walmart_sales"],
        "dia_schema": walmart_dia_schema,
    })
    
    # Confidence should be present and reasonable
    assert "confidence" in result
    assert 0.0 <= result["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_dia_schema_column_roles_respected(walmart_dia_schema):
    """Test that only metric columns are suggested for aggregation queries."""
    tool = ResolveSemanticsTool()
    
    # Query for metric - should match Weekly_Sales (role=metric)
    result = await tool.execute({
        "question": "Sum of sales",
        "available_tables": ["walmart_sales"],
        "dia_schema": walmart_dia_schema,
    })
    
    assert result["metrics"][0]["name"] == "Weekly_Sales"
    assert "SUM" in result["metrics"][0]["allowed_ops"]


@pytest.mark.asyncio
async def test_dia_schema_empty_columns():
    """Test handling of empty DIA schema."""
    tool = ResolveSemanticsTool()
    
    empty_schema = {
        "table_name": "empty_table",
        "columns": [],
        "row_count": 0,
        "confidence_avg": 0.0,
    }
    
    with pytest.raises(UnresolvedMetricException):
        await tool.execute({
            "question": "Any metric",
            "available_tables": ["empty_table"],
            "dia_schema": empty_schema,
        })
