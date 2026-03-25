from __future__ import annotations

from typing import Protocol

from app.models import BotStatus, TradeDecision


class DecisionEngine(Protocol):
    def decide(self, status: BotStatus) -> TradeDecision:
        ...


class HoldDecisionEngine:
    def decide(self, status: BotStatus) -> TradeDecision:
        return TradeDecision(
            action="hold",
            symbol=status.symbol,
            confidence=0.0,
            reason="Compatibility mode: no AI decision engine configured yet.",
            strategy_tag="hold",
        )
