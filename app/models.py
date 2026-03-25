from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class TradeDecision(BaseModel):
    action: Literal["buy", "sell", "hold", "close"] = "hold"
    symbol: str
    size: float = 0.0
    order_type: Literal["market", "limit"] = "market"
    limit_price: float | None = None
    reduce_only: bool = False
    confidence: float = 0.0
    reason: str = ""
    strategy_tag: str = "compatibility"
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskVerdict(BaseModel):
    approved: bool
    reason: str


class PositionSnapshot(BaseModel):
    coin: str
    size: float
    entry_price: float | None = None
    position_value: float | None = None
    unrealized_pnl: float | None = None
    leverage: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class OpenOrderSnapshot(BaseModel):
    coin: str
    oid: int
    side: str
    size: float
    limit_price: float
    timestamp: int
    raw: dict[str, Any] = Field(default_factory=dict)


class BotStatus(BaseModel):
    running: bool = False
    panic_mode: bool = False
    connected: bool = False
    last_error: str | None = None
    last_sync_time: datetime | None = None
    account_address: str | None = None
    app_env: str
    mode: str
    symbol: str
    current_mid: float | None = None
    open_orders: list[OpenOrderSnapshot] = Field(default_factory=list)
    positions: list[PositionSnapshot] = Field(default_factory=list)

    @classmethod
    def fresh(cls, app_env: str, mode: str, symbol: str) -> "BotStatus":
        return cls(
            running=False,
            panic_mode=False,
            connected=False,
            app_env=app_env,
            mode=mode,
            symbol=symbol,
            last_sync_time=datetime.now(timezone.utc),
        )


class TestOrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    size: float
    order_type: Literal["market", "limit"] = "market"
    limit_price: float | None = None
    reduce_only: bool = False


class ControlResponse(BaseModel):
    ok: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
