"""
Suite automatizada de tests end-to-end para beta con datos de Spotify.

Implementa los 5 casos de prueba definidos en beta_test_cases.md.

NOTA: Estos tests requieren un servidor corriendo en http://127.0.0.1:8001
Para ejecutar: primero correr ./start_verity.ps1, luego pytest tests/test_beta_e2e.py
"""
import pytest
import httpx
import os
from typing import Dict

# Skip all tests in this file - they require external server
pytestmark = pytest.mark.skip(reason="E2E tests require server running on port 8001 - run ./start_verity.ps1 first")

# Base URL del API
BASE_URL = "http://127.0.0.1:8001"

@pytest.fixture(scope="module")
def api_client():
    """Cliente HTTP para tests."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

@pytest.fixture(scope="module")
async def auth_token(api_client):
    """Obtiene JWT válido para tests."""
    # Usar bypass de dev si n8n no está disponible
    os.environ["AUTH_OTP_INSECURE_DEV_BYPASS"] = "true"
    
    response = await api_client.post(
        "/api/v2/auth/otp/validate",
        json={"wa_id": "5218112345678", "otp": "123456"}
    )
    assert response.status_code == 200
    data = response.json()
    return data["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """Headers con autenticación."""
    return {"Authorization": f"Bearer {auth_token}"}


# ============================================================================
# Caso 1: Auth + Query Simple
# ============================================================================

@pytest.mark.asyncio
async def test_case1_auth_and_simple_query(api_client, auth_headers):
    """Caso 1: Validar flujo completo de auth + query simple."""
    response = await api_client.post(
        "/api/v2/query",
        headers=auth_headers,
        json={
            "question": "¿Cuántas canciones he escuchado?",
            "available_tables": ["listening_history"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Validaciones
    assert "conversation_id" in data
    assert "response" in data
    assert "intent" in data
    assert "checkpoints" in data
    
    # Validar que resolvió la métrica correcta
    semantics_checkpoint = next(
        (c for c in data["checkpoints"] if c["tool"] == "resolve_semantics@1.0"),
        None
    )
    assert semantics_checkpoint is not None
    assert semantics_checkpoint["status"] == "ok"
    assert semantics_checkpoint["execution_time_ms"] < 200
    
    # Validar que ejecutó query
    query_checkpoint = next(
        (c for c in data["checkpoints"] if c["tool"] == "run_table_query@1.0"),
        None
    )
    assert query_checkpoint is not None
    assert query_checkpoint["status"] == "ok"
    assert query_checkpoint["execution_time_ms"] < 100


# ============================================================================
# Caso 2: Desambiguación Guiada
# ============================================================================

@pytest.mark.asyncio
async def test_case2_disambiguation(api_client, auth_headers):
    """Caso 2: Validar flujo de desambiguación."""
    conv_id = "beta-disamb-test-001"
    
    # Request 1: Query ambigua
    response1 = await api_client.post(
        "/api/v2/query",
        headers=auth_headers,
        json={
            "question": "¿Cuántos artistas?",
            "conversation_id": conv_id,
            "available_tables": ["listening_history"]
        }
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Debe detectar ambigüedad
    assert "awaiting_disambiguation" in data1
    assert data1["awaiting_disambiguation"] is True
    assert "1." in data1["response"]  # Opciones numeradas
    
    # Request 2: Selección
    response2 = await api_client.post(
        "/api/v2/query",
        headers=auth_headers,
        json={
            "question": "1",
            "conversation_id": conv_id,
            "available_tables": ["listening_history"]
        }
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Debe ejecutar query con métrica seleccionada
    assert data2["intent"] == "aggregate_metrics"
    assert "awaiting_disambiguation" not in data2 or data2["awaiting_disambiguation"] is False


# ============================================================================
# Caso 3: Follow-up Conversacional
# ============================================================================

@pytest.mark.asyncio
async def test_case3_followup_context(api_client, auth_headers):
    """Caso 3: Validar contexto conversacional y context boost."""
    conv_id = "beta-followup-test-001"
    
    # Request 1: Query inicial
    response1 = await api_client.post(
        "/api/v2/query",
        headers=auth_headers,
        json={
            "question": "¿Cuántas horas de música he escuchado?",
            "conversation_id": conv_id,
            "available_tables": ["listening_history"]
        }
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["intent"] == "aggregate_metrics"
    
    # Extraer base_match_score
    semantics1 = next(
        (c for c in data1["checkpoints"] if c["tool"] == "resolve_semantics@1.0"),
        None
    )
    assert semantics1 is not None
    base_score_1 = semantics1["output_data"].get("base_match_score", 0)
    
    # Request 2: Follow-up
    response2 = await api_client.post(
        "/api/v2/query",
        headers=auth_headers,
        json={
            "question": "¿Y cuántas canciones únicas?",
            "conversation_id": conv_id,
            "available_tables": ["listening_history"]
        }
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["intent"] == "aggregate_metrics"
    
    # Validar context boost
    semantics2 = next(
        (c for c in data2["checkpoints"] if c["tool"] == "resolve_semantics@1.0"),
        None
    )
    assert semantics2 is not None
    context_boost = semantics2["output_data"].get("context_boost", 0)
    
    # Debe haber boost por misma tabla
    assert context_boost > 0, "Expected context boost for follow-up in same table"


# ============================================================================
# Caso 4: Rate Limiting
# ============================================================================

@pytest.mark.asyncio
async def test_case4_rate_limiting(api_client):
    """Caso 4: Validar rate limits."""
    # Deshabilitar bypass para este test
    original_bypass = os.environ.get("AUTH_OTP_INSECURE_DEV_BYPASS")
    os.environ["AUTH_OTP_INSECURE_DEV_BYPASS"] = "false"
    
    try:
        # Enviar 6 requests (límite: 5/min)
        responses = []
        for i in range(6):
            response = await api_client.post(
                "/api/v2/auth/otp/validate",
                json={"wa_id": f"52181123456{i}", "otp": "123456"}
            )
            responses.append(response)
        
        # Primeras 5 deben pasar (o fallar por OTP inválido, no por rate limit)
        for r in responses[:5]:
            assert r.status_code in [200, 401, 503], f"Unexpected status: {r.status_code}"
        
        # La 6ta debe ser rate limited
        assert responses[5].status_code == 429
        assert "Retry-After" in responses[5].headers
        
        data = responses[5].json()
        assert data["error"]["code"] == "RATE_LIMITED"
    
    finally:
        # Restaurar bypass
        if original_bypass:
            os.environ["AUTH_OTP_INSECURE_DEV_BYPASS"] = original_bypass


# ============================================================================
# Caso 5: Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_case5_error_handling_unresolved_metric(api_client, auth_headers):
    """Caso 5.1: Métrica inexistente."""
    response = await api_client.post(
        "/api/v2/query",
        headers=auth_headers,
        json={
            "question": "¿Cuántos podcasts he escuchado?",
            "available_tables": ["listening_history"]
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    
    assert "error" in data
    assert data["error"]["code"] == "UNRESOLVED_METRIC"
    assert "request_id" in data["error"]


@pytest.mark.asyncio
async def test_case5_error_handling_empty_result(api_client, auth_headers):
    """Caso 5.2: Query sin resultados."""
    response = await api_client.post(
        "/api/v2/query",
        headers=auth_headers,
        json={
            "question": "¿Cuántas canciones escuché en 1990?",
            "available_tables": ["listening_history"]
        }
    )
    
    # Puede ser 404 o 200 con resultado 0, dependiendo de implementación
    assert response.status_code in [200, 404]
    
    if response.status_code == 404:
        data = response.json()
        assert data["error"]["code"] == "EMPTY_RESULT"


# ============================================================================
# Validación de Métricas
# ============================================================================

@pytest.mark.asyncio
async def test_observability_metrics(api_client):
    """Validar que métricas de observabilidad están funcionando."""
    response = await api_client.get("/api/v2/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    # Validar estructura
    assert "tools" in data
    assert "global_errors" in data
    assert "otp" in data
    
    # Validar métricas de tools
    if "resolve_semantics@1.0" in data["tools"]:
        tool_metrics = data["tools"]["resolve_semantics@1.0"]
        assert "call_count" in tool_metrics
        assert "p50_ms" in tool_metrics
        assert "p90_ms" in tool_metrics
        assert "p99_ms" in tool_metrics
        
        # Validar SLAs
        assert tool_metrics["p99_ms"] < 500, "p99 latency too high"
