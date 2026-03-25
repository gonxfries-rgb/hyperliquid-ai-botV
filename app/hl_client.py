from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.models import OpenOrderSnapshot, PositionSnapshot


@dataclass
class MarketSnapshot:
    mids: dict[str, str]
    user_state: dict[str, Any]
    open_orders: list[dict[str, Any]]
    recent_fills: list[dict[str, Any]]


class HyperliquidClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._lock = threading.Lock()
        self.info = None
        self.exchange = None
        self.address = settings.hl_account_address
        self._ws_subscription_ids: list[tuple[dict[str, Any], int]] = []
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        if self.settings.is_mainnet and not self.settings.allow_mainnet:
            raise RuntimeError("Mainnet is blocked. Set ALLOW_MAINNET=true to enable it.")
        if not self.settings.is_configured:
            raise RuntimeError("HL_ACCOUNT_ADDRESS and HL_SECRET_KEY must be set.")

        import eth_account
        from hyperliquid.exchange import Exchange
        from hyperliquid.info import Info
        from hyperliquid.utils import constants

        base_url = constants.MAINNET_API_URL if self.settings.is_mainnet else constants.TESTNET_API_URL
        account = eth_account.Account.from_key(self.settings.hl_secret_key)
        self.info = Info(base_url, skip_ws=not self.settings.enable_websocket)
        self.exchange = Exchange(account, base_url, account_address=self.settings.hl_account_address)
        self.address = self.settings.hl_account_address or account.address
        self._connected = True

    def disconnect(self) -> None:
        if self.info is not None and self.settings.enable_websocket:
            try:
                self.info.disconnect_websocket()
            except Exception:
                pass
        self._ws_subscription_ids.clear()
        self._connected = False

    def subscribe_defaults(self, on_message) -> None:
        if not self.settings.enable_websocket or self.info is None:
            return
        subscriptions = [
            {"type": "allMids"},
            {"type": "userEvents", "user": self.address},
            {"type": "userFills", "user": self.address},
            {"type": "orderUpdates", "user": self.address},
            {"type": "candle", "coin": self.settings.hl_symbol, "interval": "1m"},
        ]
        for sub in subscriptions:
            sub_id = self.info.subscribe(sub, on_message)
            self._ws_subscription_ids.append((sub, sub_id))

    def fetch_snapshot(self) -> MarketSnapshot:
        if self.info is None:
            raise RuntimeError("Hyperliquid client is not connected.")
        with self._lock:
            mids = self.info.all_mids()
            user_state = self.info.user_state(self.address)
            open_orders = self.info.open_orders(self.address)
            recent_fills = self.info.user_fills(self.address)
        return MarketSnapshot(mids=mids, user_state=user_state, open_orders=open_orders, recent_fills=recent_fills)

    def normalize_positions(self, user_state: dict[str, Any]) -> list[PositionSnapshot]:
        out: list[PositionSnapshot] = []
        for item in user_state.get("assetPositions", []):
            position = item.get("position", {})
            leverage = position.get("leverage") or {}
            out.append(
                PositionSnapshot(
                    coin=position.get("coin", ""),
                    size=float(position.get("szi", 0.0)),
                    entry_price=_to_float(position.get("entryPx")),
                    position_value=_to_float(position.get("positionValue")),
                    unrealized_pnl=_to_float(position.get("unrealizedPnl")),
                    leverage=_to_float(leverage.get("value")),
                    raw=position,
                )
            )
        return out

    def normalize_open_orders(self, open_orders: list[dict[str, Any]]) -> list[OpenOrderSnapshot]:
        return [
            OpenOrderSnapshot(
                coin=item.get("coin", ""),
                oid=int(item.get("oid", 0)),
                side=item.get("side", ""),
                size=float(item.get("sz", 0.0)),
                limit_price=float(item.get("limitPx", 0.0)),
                timestamp=int(item.get("timestamp", 0)),
                raw=item,
            )
            for item in open_orders
        ]

    def get_mid(self, symbol: str) -> float | None:
        snapshot = self.fetch_snapshot()
        value = snapshot.mids.get(symbol)
        return _to_float(value)

    def place_market_order(self, symbol: str, is_buy: bool, size: float, reduce_only: bool = False) -> Any:
        if self.exchange is None:
            raise RuntimeError("Exchange client is not connected.")
        with self._lock:
            if reduce_only:
                side_size = size if size is not None else None
                return self.exchange.market_close(symbol, sz=side_size, slippage=self.settings.default_test_slippage)
            return self.exchange.market_open(symbol, is_buy, size, slippage=self.settings.default_test_slippage)

    def place_limit_order(
        self, symbol: str, is_buy: bool, size: float, limit_price: float, reduce_only: bool = False
    ) -> Any:
        if self.exchange is None:
            raise RuntimeError("Exchange client is not connected.")
        order_type = {"limit": {"tif": "Gtc"}}
        with self._lock:
            return self.exchange.order(symbol, is_buy, size, limit_price, order_type, reduce_only=reduce_only)

    def cancel_all_orders(self) -> list[Any]:
        if self.info is None or self.exchange is None:
            raise RuntimeError("Clients are not connected.")
        results: list[Any] = []
        with self._lock:
            open_orders = self.info.open_orders(self.address)
            for order in open_orders:
                results.append(self.exchange.cancel(order["coin"], int(order["oid"])))
        return results

    def flatten_symbol(self, symbol: str) -> Any:
        if self.exchange is None:
            raise RuntimeError("Exchange client is not connected.")
        with self._lock:
            return self.exchange.market_close(symbol, slippage=self.settings.default_test_slippage)


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
