from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS bot_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    payload TEXT
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    symbol TEXT NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    size REAL NOT NULL,
    order_type TEXT NOT NULL,
    request_payload TEXT NOT NULL,
    response_payload TEXT,
    status TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def insert(self, query: str, params: Iterable[Any]) -> int:
        with self.connection() as conn:
            cur = conn.execute(query, tuple(params))
            return int(cur.lastrowid)

    def fetch_all(self, query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def dump_payload(payload: Any) -> str:
        return json.dumps(payload, default=str, ensure_ascii=False)
