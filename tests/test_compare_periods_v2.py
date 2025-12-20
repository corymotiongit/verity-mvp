import pytest
from fastapi.testclient import TestClient

from verity.main import app


@pytest.mark.asyncio
async def test_v2_compare_periods_produces_temporal_series_and_chart_checkpoint(tmp_path, monkeypatch):
    # Asegura que run_table_query use uploads/canonical relativo al cwd
    monkeypatch.chdir(tmp_path)

    canonical = tmp_path / "uploads" / "canonical"
    canonical.mkdir(parents=True)

    # Dos meses de datos para que month-bucket tenga al menos 2 puntos
    (canonical / "orders.csv").write_text(
        "order_id,customer_id,order_status,order_date,order_amount\n"
        "o1,c1,delivered,2025-11-10,10\n"
        "o2,c2,delivered,2025-11-12,20\n"
        "o3,c1,delivered,2025-12-02,5\n"
        "o4,c3,delivered,2025-12-03,15\n",
        encoding="utf-8",
    )

    client = TestClient(app)
    r = client.post(
        "/api/v2/query",
        json={
            "question": "Compare delivered revenue vs last month",
            "available_tables": ["orders"],
            "context": {},
        },
    )

    assert r.status_code == 200
    body = r.json()

    # Intent debe ser compare (fallback determinista sin Gemini key)
    assert body["intent"] == "compare"

    tools = [cp.get("tool") for cp in body.get("checkpoints", [])]
    assert tools == ["semantic_resolution", "run_table_query@1.0", "build_chart@2.0"]

    run_cp = next(cp for cp in body["checkpoints"] if cp.get("tool") == "run_table_query@1.0")
    out = run_cp["output"]

    # Esperamos serie temporal (>=2 buckets)
    assert out["row_count"] >= 2
    assert out["columns"][0] == "order_date__month"

    chart_cp = next(cp for cp in body["checkpoints"] if cp.get("tool") == "build_chart@2.0")
    chart = chart_cp["output"]
    assert chart["library"] == "plotly"
    assert "chart_spec" in chart and "data" in chart["chart_spec"]
