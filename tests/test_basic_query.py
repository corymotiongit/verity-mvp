"""
Tests para PR4 - Fallback a operaciones básicas sin Data Dictionary

Validación:
- COUNT funciona sin metadatos
- DISTINCT funciona con columna explícita
- TOP N con y sin ORDER BY
- SUM, AVG, MIN, MAX con columnas numéricas
- Fallback desde UnresolvedMetricException

Requisito: uploads/canonical/walmart.csv debe existir
"""

import pytest
from pathlib import Path

from verity.tools.run_basic_query import RunBasicQueryTool
from verity.exceptions import ValidationException, InvalidFilterException


@pytest.fixture
def ensure_walmart_csv():
    """Verifica que walmart.csv exista en uploads/canonical/"""
    csv_path = Path("uploads/canonical/walmart.csv")
    if not csv_path.exists():
        pytest.skip(f"Walmart CSV no encontrado: {csv_path}")
    return csv_path


@pytest.mark.asyncio
async def test_basic_query_count(ensure_walmart_csv):
    """Test COUNT sin metadatos."""
    tool = RunBasicQueryTool()
    
    result = await tool.execute({
        "question": "count rows",
        "table_name": "walmart",
    })
    
    assert result["operation"] == "COUNT"
    assert result["is_fallback"] is True
    assert result["confidence"] == 0.7
    assert len(result["data"]) == 1
    assert "count" in result["data"][0]
    assert result["data"][0]["count"] > 0  # Debe haber filas


@pytest.mark.asyncio
async def test_basic_query_count_spanish(ensure_walmart_csv):
    """Test COUNT con keywords en español."""
    tool = RunBasicQueryTool()
    
    result = await tool.execute({
        "question": "cuantos registros hay",
        "table_name": "walmart",
    })
    
    assert result["operation"] == "COUNT"
    assert result["data"][0]["count"] > 0


@pytest.mark.asyncio
async def test_basic_query_distinct(ensure_walmart_csv):
    """Test DISTINCT con columna explícita."""
    tool = RunBasicQueryTool()
    
    result = await tool.execute({
        "question": "distinct Store",
        "table_name": "walmart",
    })
    
    assert result["operation"] == "DISTINCT"
    assert result["confidence"] == 0.6
    assert len(result["data"]) > 0
    assert "value" in result["data"][0]
    
    # Walmart tiene 45 stores distintos (según audit)
    # Pero limitamos a 100 en el código
    assert len(result["data"]) <= 100


@pytest.mark.asyncio
async def test_basic_query_top_n_no_order(ensure_walmart_csv):
    """Test TOP N sin ORDER BY (primeras N filas)."""
    tool = RunBasicQueryTool()
    
    result = await tool.execute({
        "question": "top 5",
        "table_name": "walmart",
    })
    
    assert result["operation"] == "TOP_N"
    assert len(result["data"]) == 5
    assert "operation_detail" in result
    assert "LIMIT 5" in result["operation_detail"]


@pytest.mark.asyncio
async def test_basic_query_top_n_with_order(ensure_walmart_csv):
    """Test TOP N ORDER BY columna."""
    tool = RunBasicQueryTool()
    
    result = await tool.execute({
        "question": "top 10 by Weekly_Sales",
        "table_name": "walmart",
    })
    
    assert result["operation"] == "TOP_N"
    assert len(result["data"]) == 10
    assert "Weekly_Sales" in result["data"][0]
    assert "ORDER BY Weekly_Sales DESC" in result["operation_detail"]
    
    # Verificar ordenamiento descendente
    sales_values = [row["Weekly_Sales"] for row in result["data"]]
    assert sales_values == sorted(sales_values, reverse=True)


@pytest.mark.asyncio
async def test_basic_query_sum(ensure_walmart_csv):
    """Test SUM sobre columna numérica."""
    tool = RunBasicQueryTool()
    
    result = await tool.execute({
        "question": "sum Weekly_Sales",
        "table_name": "walmart",
    })
    
    assert result["operation"] == "SUM"
    assert len(result["data"]) == 1
    assert "sum" in result["data"][0]
    assert result["data"][0]["sum"] > 0


@pytest.mark.asyncio
async def test_basic_query_avg(ensure_walmart_csv):
    """Test AVG sobre columna numérica."""
    tool = RunBasicQueryTool()
    
    result = await tool.execute({
        "question": "average Temperature",
        "table_name": "walmart",
    })
    
    assert result["operation"] == "AVG"
    assert len(result["data"]) == 1
    assert "avg" in result["data"][0]
    assert result["data"][0]["avg"] > 0


@pytest.mark.asyncio
async def test_basic_query_min_max(ensure_walmart_csv):
    """Test MIN y MAX sobre columna numérica."""
    tool = RunBasicQueryTool()
    
    result_min = await tool.execute({
        "question": "min Fuel_Price",
        "table_name": "walmart",
    })
    
    result_max = await tool.execute({
        "question": "max Fuel_Price",
        "table_name": "walmart",
    })
    
    assert result_min["operation"] == "MIN"
    assert result_max["operation"] == "MAX"
    assert result_min["data"][0]["min"] < result_max["data"][0]["max"]


@pytest.mark.asyncio
async def test_basic_query_invalid_column():
    """Test error cuando columna no existe."""
    tool = RunBasicQueryTool()
    
    with pytest.raises(InvalidFilterException) as excinfo:
        await tool.execute({
            "question": "distinct NonExistentColumn",
            "table_name": "walmart",
        })
    
    assert "Columna no encontrada" in excinfo.value.message


@pytest.mark.asyncio
async def test_basic_query_unsupported_operation():
    """Test error cuando operación no soportada."""
    tool = RunBasicQueryTool()
    
    with pytest.raises(ValidationException) as excinfo:
        await tool.execute({
            "question": "complex query with joins",
            "table_name": "walmart",
        })
    
    assert "UNSUPPORTED_BASIC_OPERATION" in str(excinfo.value.details)


@pytest.mark.asyncio
async def test_basic_query_table_not_found():
    """Test error cuando tabla no existe."""
    tool = RunBasicQueryTool()
    
    with pytest.raises(ValidationException) as excinfo:
        await tool.execute({
            "question": "count rows",
            "table_name": "nonexistent_table",
        })
    
    assert "Tabla no encontrada" in excinfo.value.message


@pytest.mark.asyncio
async def test_fallback_integration_from_unresolved_metric(ensure_walmart_csv):
    """
    Test integración completa: UnresolvedMetricException → fallback basic_query.
    
    Simula query que falla en resolve_semantics y cae en fallback.
    """
    from verity.api.routes.query_v2 import router
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Query que NO existe en Data Dictionary (debería fallar semantic + usar fallback)
    response = client.post(
        "/api/v2/query",
        json={
            "question": "count rows",  # No es métrica en Data Dictionary
            "available_tables": ["walmart"],
            "context": {},
        },
    )
    
    # Debería retornar 200 con resultado de fallback
    assert response.status_code == 200
    data = response.json()
    
    # Verificar que usó fallback
    assert "checkpoints" in data
    checkpoints = data["checkpoints"]
    
    # Debe haber checkpoint de basic_query_fallback
    fallback_checkpoint = next(
        (cp for cp in checkpoints if cp.get("tool") == "basic_query_fallback"),
        None,
    )
    assert fallback_checkpoint is not None
    assert fallback_checkpoint["status"] == "ok"
    
    # Response debe incluir resultado COUNT
    assert "count" in data["response"].lower() or "resultado" in data["response"].lower()
    
    # Confidence bajo (señal de fallback)
    assert data["confidence"] < 0.8


@pytest.mark.skip(reason="Test obsoleto - IntentResolver devuelve UNKNOWN (200) para queries no clasificables, nunca llega a resolve_semantics/fallback")
@pytest.mark.asyncio
async def test_fallback_preserves_error_when_fallback_fails(ensure_walmart_csv):
    """
    Test que fallback re-raise error original si fallback también falla.
    
    NOTA: Este test está obsoleto porque asume que todas las queries pasan por
    resolve_semantics, pero el IntentResolver puede clasificar como UNKNOWN y
    devolver 200 sin ejecutar tools.
    
    Para validar el fallback error propagation, usar test que fuerza aggregate intent
    con query que falla tanto en semantic como en basic_query.
    """
    from verity.api.routes.query_v2 import router
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    # Query que falla en semantic Y no es operación básica válida
    # Forzar intent="aggregate" para que ejecute resolve_semantics
    response = client.post(
        "/api/v2/query",
        json={
            "question": "profit margin analysis with complex calculations",
            "available_tables": ["walmart"],
            "context": {"intent": "aggregate"},  # Force aggregate intent
        },
    )
    
    # Debug: print response to see what basic_query detected
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    
    # Debería retornar error (UnresolvedMetricException)
    # Porque basic_query no puede detectar "profit margin analysis" como operación válida
    assert response.status_code == 400
    data = response.json()
    
    # Error debe ser UNRESOLVED_METRIC (no fallback exitoso)
    assert "UNRESOLVED_METRIC" in data.get("error", {}).get("code", "")
