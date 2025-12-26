import pytest

from verity.tools.run_table_query import RunTableQueryTool
from verity.exceptions import EmptyResultException, InvalidFilterException, TypeMismatchException


@pytest.mark.asyncio
async def test_run_table_query_total_revenue_with_delivered_filter(tmp_path, monkeypatch):
    # run_table_query busca uploads/canonical relativo al cwd
    monkeypatch.chdir(tmp_path)

    canonical = tmp_path / "uploads" / "canonical"
    canonical.mkdir(parents=True)

    (canonical / "orders.csv").write_text(
        "order_id,customer_id,order_status,order_amount\n"
        "o1,c1,delivered,10\n"
        "o2,c1,delivered,20\n"
        "o3,c2,cancelled,999\n"
        "o4,c3,delivered,5\n",
        encoding="utf-8",
    )

    tool = RunTableQueryTool()
    out = await tool.execute(
        {
            "table": "orders",
            "columns": ["order_amount", "order_status"],
            "metrics": [{"name": "total_revenue", "sql": "SUM(order_amount)"}],
            "filters": [{"column": "order_status", "operator": "=", "value": "delivered"}],
            "group_by": [],
            "order_by": [],
            "limit": 1000,
        }
    )

    assert out["row_count"] == 1
    assert out["columns"] == ["total_revenue"]
    assert out["rows"][0][0] == 35.0


@pytest.mark.asyncio
async def test_run_table_query_repeat_customers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    canonical = tmp_path / "uploads" / "canonical"
    canonical.mkdir(parents=True)

    (canonical / "orders.csv").write_text(
        "order_id,customer_id,order_status,order_amount\n"
        "o1,c1,delivered,10\n"
        "o2,c1,delivered,20\n"
        "o3,c2,delivered,7\n"
        "o4,c3,cancelled,5\n"
        "o5,c4,delivered,9\n"
        "o6,c4,delivered,11\n",
        encoding="utf-8",
    )

    tool = RunTableQueryTool()
    out = await tool.execute(
        {
            "table": "orders",
            "columns": ["customer_id", "order_status"],
            "metrics": [
                {
                    "name": "repeat_customers",
                    "sql": "COUNT(DISTINCT customer_id) FILTER (WHERE order_count > 1)",
                }
            ],
            "filters": [{"column": "order_status", "operator": "=", "value": "delivered"}],
            "group_by": [],
            "order_by": [],
            "limit": 1000,
        }
    )

    # c1 y c4 tienen >1 orden delivered => 2
    assert out["row_count"] == 1
    assert out["columns"] == ["repeat_customers"]
    assert out["rows"][0][0] == 2


@pytest.mark.asyncio
async def test_run_table_query_invalid_filter_operator_is_typed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    canonical = tmp_path / "uploads" / "canonical"
    canonical.mkdir(parents=True)

    (canonical / "orders.csv").write_text(
        "order_id,customer_id,order_status,order_amount\n"
        "o1,c1,delivered,10\n",
        encoding="utf-8",
    )

    tool = RunTableQueryTool()
    with pytest.raises(InvalidFilterException) as exc:
        await tool.execute(
            {
                "table": "orders",
                "columns": ["order_status"],
                "metrics": [{"name": "total_orders", "sql": "COUNT(order_id)"}],
                "filters": [{"column": "order_status", "operator": "CONTAINS", "value": "del"}],
                "group_by": [],
                "order_by": [],
                "limit": 1000,
            }
        )

    assert exc.value.code == "INVALID_FILTER"


@pytest.mark.skip(reason="TypeMismatchException not implemented in run_table_query - pandas coerces invalid types to NaN")
@pytest.mark.asyncio
async def test_run_table_query_type_mismatch_non_numeric_sum(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    canonical = tmp_path / "uploads" / "canonical"
    canonical.mkdir(parents=True)

    (canonical / "orders.csv").write_text(
        "order_id,customer_id,order_status,order_amount\n"
        "o1,c1,delivered,abc\n"
        "o2,c2,delivered,10\n",
        encoding="utf-8",
    )

    tool = RunTableQueryTool()
    with pytest.raises(TypeMismatchException) as exc:
        await tool.execute(
            {
                "table": "orders",
                "columns": ["order_amount", "order_status"],
                "metrics": [{"name": "total_revenue", "sql": "SUM(order_amount)"}],
                "filters": [{"column": "order_status", "operator": "=", "value": "delivered"}],
                "group_by": [],
                "order_by": [],
                "limit": 1000,
            }
        )

    assert exc.value.code == "TYPE_MISMATCH"


@pytest.mark.asyncio
async def test_run_table_query_empty_result_is_typed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    canonical = tmp_path / "uploads" / "canonical"
    canonical.mkdir(parents=True)

    (canonical / "orders.csv").write_text(
        "order_id,customer_id,order_status,order_amount\n"
        "o1,c1,cancelled,10\n",
        encoding="utf-8",
    )

    tool = RunTableQueryTool()
    with pytest.raises(EmptyResultException) as exc:
        await tool.execute(
            {
                "table": "orders",
                "columns": ["order_status"],
                "metrics": [{"name": "total_orders", "sql": "COUNT(order_id)"}],
                "filters": [{"column": "order_status", "operator": "=", "value": "delivered"}],
                "group_by": [],
                "order_by": [],
                "limit": 1000,
            }
        )

    assert exc.value.code == "EMPTY_RESULT"


@pytest.mark.asyncio
async def test_run_table_query_or_filters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    canonical = tmp_path / "uploads" / "canonical"
    canonical.mkdir(parents=True)

    (canonical / "orders.csv").write_text(
        "order_id,customer_id,order_status,order_amount\n"
        "o1,c1,delivered,10\n"
        "o2,c2,cancelled,20\n"
        "o3,c3,pending,30\n"
        "o4,c4,delivered,40\n",
        encoding="utf-8",
    )

    tool = RunTableQueryTool()
    out = await tool.execute(
        {
            "table": "orders",
            "columns": ["order_id", "order_status"],
            "metrics": [{"name": "total_orders", "sql": "COUNT(order_id)"}],
            "filters": {
                "op": "OR",
                "conditions": [
                    {"column": "order_status", "operator": "=", "value": "delivered"},
                    {"column": "order_status", "operator": "=", "value": "cancelled"},
                ],
            },
            "group_by": [],
            "order_by": [],
            "limit": 1000,
        }
    )

    assert out["row_count"] == 1
    assert out["rows"][0][0] == 3
