"""
Test para COMPARE_PERIODS intent.

ESTADO: Skip temporalmente.

RAZÓN: 
TestClient(app) carga la app FastAPI antes de que se apliquen los patches.
Los módulos ya están importados con sus rutas registradas.

SOLUCIÓN REQUERIDA:
1. Refactor de app factory pattern en main.py
2. O usar dependency_overrides de FastAPI para inyectar mocks

Para validar COMPARE_PERIODS manualmente:
1. Iniciar servidor: ./start_verity.ps1
2. Usar query con "vs last month" que activa COMPARE_PERIODS
"""
import pytest
from fastapi.testclient import TestClient

from verity.main import app


@pytest.mark.skip(reason="Requires app factory pattern - TestClient imports app before patches apply")
@pytest.mark.asyncio
async def test_v2_compare_periods_produces_temporal_series_and_chart_checkpoint(tmp_path, monkeypatch):
    """Test COMPARE_PERIODS - pendiente refactor de app factory."""
    # Este test requiere que la app se cree DESPUÉS de aplicar mocks
    # FastAPI TestClient importa app al momento de instanciar
    pass
