from __future__ import annotations

from app.config import Settings
from app.models import BotStatus, RiskVerdict, TradeDecision


class RiskEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, decision: TradeDecision, status: BotStatus) -> RiskVerdict:
        if status.panic_mode:
            return RiskVerdict(approved=False, reason="panic mode is enabled")

        if decision.action == "hold":
            return RiskVerdict(approved=False, reason="hold decision does not execute")

        if decision.size <= 0:
            return RiskVerdict(approved=False, reason="size must be positive")

        if decision.size > self.settings.max_order_size:
            return RiskVerdict(approved=False, reason="size exceeds MAX_ORDER_SIZE")

        if len(status.open_orders) >= self.settings.max_open_orders and not decision.reduce_only:
            return RiskVerdict(approved=False, reason="open-order count exceeds MAX_OPEN_ORDERS")

        current_mid = status.current_mid or 0
        reference_price = decision.limit_price or current_mid
        if reference_price and decision.size * reference_price > self.settings.max_notional_usd:
            return RiskVerdict(approved=False, reason="order notional exceeds MAX_NOTIONAL_USD")

        symbol_position = next((p for p in status.positions if p.coin == decision.symbol), None)
        existing_abs_position = abs(symbol_position.size) if symbol_position else 0.0
        if not decision.reduce_only and existing_abs_position + decision.size > self.settings.max_net_position:
            return RiskVerdict(approved=False, reason="net position would exceed MAX_NET_POSITION")

        return RiskVerdict(approved=True, reason="approved")
