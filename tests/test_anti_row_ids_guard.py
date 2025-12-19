"""Tests for ANTI row_ids guard behavior."""

from uuid import uuid4

from verity.config import get_settings
from verity.modules.agent.anti import anti_normalize
from verity.modules.agent.schemas import DataEvidence, Source


def _data_source(*, row_ids, row_count: int) -> Source:
    ev = DataEvidence(
        operation="query",
        filter_applied=None,
        columns_used=["Empresa", "count"],
        row_ids=row_ids,
        row_count=row_count,
        sample_rows=[],
        result_value=None,
    )
    return Source(
        type="data",
        file="vista_empleados.csv",
        data_evidence=ev,
        id=str(uuid4()),
        title="Data Engine: vista_empleados.csv",
        relevance=1.0,
    )


def test_anti_no_rows_is_not_no_verificable():
    msg, _ = anti_normalize(
        user_message="graficalo",
        chat_context={},
        assistant_message="ok",
        sources=[_data_source(row_ids=[], row_count=0)],
        data_meta=None,
    )
    assert "No verificable" not in msg
    assert "No encontr" in msg  # No encontré filas...
    assert "FUENTES:" in msg


def test_anti_missing_row_ids_not_blocked_in_dev_by_default():
    # Default test env is development -> guard should not block.
    msg, _ = anti_normalize(
        user_message="cuantos empleados",
        chat_context={},
        assistant_message="Respuesta tabular",
        sources=[_data_source(row_ids=[], row_count=11)],
        data_meta=None,
    )
    assert "No verificable" not in msg
    assert "FUENTES:" in msg


def test_anti_blocks_missing_row_ids_in_production(monkeypatch):
    # Force production + guard enabled
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AGENT_ENFORCE_ROW_IDS_GUARD", "true")
    get_settings.cache_clear()

    msg, _ = anti_normalize(
        user_message="cuantos empleados",
        chat_context={},
        assistant_message="Respuesta tabular",
        sources=[_data_source(row_ids=[], row_count=11)],
        data_meta=None,
    )
    assert "No verificable" in msg
    assert "FUENTES:" in msg

    # Restore cache for other tests
    get_settings.cache_clear()
