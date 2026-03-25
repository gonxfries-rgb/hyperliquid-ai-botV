from __future__ import annotations

from typing import Any

from app.db import Database
from app.models import TradeDecision


class Journal:
    def __init__(self, db: Database) -> None:
        self.db = db

    def event(self, level: str, event_type: str, message: str, payload: Any | None = None) -> int:
        return self.db.insert(
            "INSERT INTO bot_events(level, event_type, message, payload) VALUES (?, ?, ?, ?)",
            (level, event_type, message, self.db.dump_payload(payload)),
        )

    def decision(self, decision: TradeDecision) -> int:
        return self.db.insert(
            "INSERT INTO decisions(action, symbol, confidence, reason, payload) VALUES (?, ?, ?, ?, ?)",
            (
                decision.action,
                decision.symbol,
                decision.confidence,
                decision.reason,
                self.db.dump_payload(decision.model_dump()),
            ),
        )

    def order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str,
        request_payload: Any,
        response_payload: Any,
        status: str,
    ) -> int:
        return self.db.insert(
            """
            INSERT INTO orders(symbol, side, size, order_type, request_payload, response_payload, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                side,
                size,
                order_type,
                self.db.dump_payload(request_payload),
                self.db.dump_payload(response_payload),
                status,
            ),
        )

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.db.fetch_all(
            "SELECT * FROM bot_events ORDER BY id DESC LIMIT ?",
            (limit,),
        )

    def recent_orders(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.db.fetch_all(
            "SELECT * FROM orders ORDER BY id DESC LIMIT ?",
            (limit,),
        )

    def recent_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.db.fetch_all(
            "SELECT * FROM decisions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
