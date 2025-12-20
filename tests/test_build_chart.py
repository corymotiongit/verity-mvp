import pytest

from verity.core.table_store import TABLE_STORE, TableResult
from verity.tools.build_chart import BuildChartTool


@pytest.mark.asyncio
async def test_build_chart_bar_multiy_generates_multiple_traces():
    TABLE_STORE.clear()
    table_id = "t_test1234"
    TABLE_STORE.put(
        TableResult(
            table_id=table_id,
            columns=["month", "revenue", "orders"],
            rows=[["2025-01", 10.0, 2], ["2025-02", 20.0, 3]],
            row_count=2,
            rows_count=2,
            schema={"month": "object", "revenue": "float64", "orders": "int64"},
        )
    )

    tool = BuildChartTool()
    out = await tool.execute(
        {
            "table_id": table_id,
            "chart_kind": "bar",
            "x_axis": "month",
            "y_axes": ["revenue", "orders"],
            "title": "Test",
        }
    )

    assert out["library"] == "plotly"
    assert isinstance(out["chart_id"], str) and out["chart_id"]
    spec = out["chart_spec"]
    assert "data" in spec and isinstance(spec["data"], list)
    assert "layout" in spec and isinstance(spec["layout"], dict)
    assert len(spec["data"]) == 2
    assert {t.get("name") for t in spec["data"]} == {"revenue", "orders"}


@pytest.mark.asyncio
async def test_build_chart_pie_uses_first_y_axis():
    TABLE_STORE.clear()
    table_id = "t_testpie"
    TABLE_STORE.put(
        TableResult(
            table_id=table_id,
            columns=["segment", "value"],
            rows=[["A", 1], ["B", 2]],
            row_count=2,
            rows_count=2,
            schema={"segment": "object", "value": "int64"},
        )
    )

    tool = BuildChartTool()
    out = await tool.execute(
        {
            "table_id": table_id,
            "chart_kind": "pie",
            "x_axis": "segment",
            "y_axes": ["value"],
            "title": "Pie",
        }
    )

    spec = out["chart_spec"]
    assert spec["data"][0]["type"] == "pie"
    assert spec["data"][0]["labels"] == ["A", "B"]
    assert spec["data"][0]["values"] == [1, 2]
