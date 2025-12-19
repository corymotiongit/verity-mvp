"""Regression tests for chart follow-up shortcuts."""

from verity.modules.agent.service import _coerce_table_preview_dict
from verity.modules.data.schemas import TablePreview


def test_coerce_table_preview_from_pydantic_model():
    tp = TablePreview(columns=["Empresa", "count"], rows=[["A", 1], ["B", 2]], total_rows=2)
    out = _coerce_table_preview_dict(tp)
    assert isinstance(out, dict)
    assert out["columns"] == ["Empresa", "count"]
    assert out["rows"] == [["A", 1], ["B", 2]]


def test_coerce_table_preview_from_dict():
    d = {"columns": ["x"], "rows": [[1]], "total_rows": 1}
    out = _coerce_table_preview_dict(d)
    assert out == d


def test_coerce_table_preview_rejects_invalid_shape():
    assert _coerce_table_preview_dict("not-a-table") is None
    assert _coerce_table_preview_dict({"columns": "x", "rows": []}) is None
    assert _coerce_table_preview_dict({"columns": [], "rows": "nope"}) is None
