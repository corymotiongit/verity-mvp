from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class TableResult:
    table_id: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    rows_count: int
    schema: dict[str, str]


class InMemoryTableStore:
    def __init__(self):
        self._lock = RLock()
        self._tables: dict[str, TableResult] = {}

    def put(self, table: TableResult) -> None:
        with self._lock:
            self._tables[table.table_id] = table

    def get(self, table_id: str) -> TableResult | None:
        with self._lock:
            return self._tables.get(table_id)

    def clear(self) -> None:
        with self._lock:
            self._tables.clear()


# Process-local singleton store (sufficient for MVP + deterministic local tools).
TABLE_STORE = InMemoryTableStore()
