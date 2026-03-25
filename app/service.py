from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.decision_engines import DecisionEngine, HoldDecisionEngine
from app.hl_client import HyperliquidClient
from app.journal import Journal
from app.models import BotStatus, ControlResponse, TestOrderRequest, TradeDecision
from app.risk import RiskEngine

logger = logging.getLogger(__name__)


class BotService:
    def __init__(self, settings: Settings, client: HyperliquidClient, journal: Journal) -> None:
        self.settings = settings
        self.client = client
        self.journal = journal
        self.risk = RiskEngine(settings)
        self.decision_engine: DecisionEngine = HoldDecisionEngine()
        self.status = BotStatus.fresh(settings.app_env, settings.bot_mode, settings.hl_symbol)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._latest_ws_message: dict[str, Any] | None = None

    def connect(self) -> None:
        self.client.connect()
        self.status.connected = True
        self.status.account_address = self.client.address
        self.client.subscribe_defaults(self._on_ws_message)
        self.startup_reconcile()

    def startup_reconcile(self) -> None:
        self.sync_once()
        if self.settings.cancel_all_on_startup:
            try:
                results = self.client.cancel_all_orders()
                self.journal.event("WARNING", "startup_cancel_all", "Canceled all open orders on startup.", results)
            except Exception as exc:
                self._record_error("cancel_all_on_startup_failed", exc)
        if self.settings.panic_flatten_on_startup:
            try:
                result = self.client.flatten_symbol(self.settings.hl_symbol)
                self.journal.event("WARNING", "startup_flatten", "Flattened symbol on startup.", result)
            except Exception as exc:
                self._record_error("flatten_on_startup_failed", exc)

    def _on_ws_message(self, message: Any) -> None:
        self._latest_ws_message = {"received_at": datetime.now(timezone.utc).isoformat(), "message": message}
        self.journal.event("INFO", "ws_message", "Received websocket message.", message)

    def start(self) -> ControlResponse:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return ControlResponse(ok=True, message="Bot loop is already running.")
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="bot-loop")
            self._thread.start()
            self.status.running = True
            self.journal.event("INFO", "bot_started", "Bot loop started.")
            return ControlResponse(ok=True, message="Bot loop started.")

    def stop(self) -> ControlResponse:
        self._stop_event.set()
        self.status.running = False
        self.journal.event("INFO", "bot_stopped", "Bot loop stop requested.")
        return ControlResponse(ok=True, message="Stop requested.")

    def _run_loop(self) -> None:
        logger.info("Starting bot loop")
        while not self._stop_event.is_set():
            try:
                self.sync_once()
                self._apply_decision_cycle()
            except Exception as exc:
                self._record_error("loop_error", exc)
            time.sleep(self.settings.poll_interval_seconds)
        self.status.running = False

    def sync_once(self) -> None:
        snapshot = self.client.fetch_snapshot()
        positions = self.client.normalize_positions(snapshot.user_state)
        open_orders = self.client.normalize_open_orders(snapshot.open_orders)

        self.status.connected = True
        self.status.last_error = None
        self.status.last_sync_time = datetime.now(timezone.utc)
        self.status.account_address = self.client.address
        self.status.current_mid = _safe_mid(snapshot.mids.get(self.settings.hl_symbol))
        self.status.positions = positions
        self.status.open_orders = open_orders

    def _apply_decision_cycle(self) -> None:
        decision = self.decision_engine.decide(self.status)
        self.journal.decision(decision)

        if self.settings.bot_mode == "observe_only":
            return
        if not self.settings.allow_live_orders:
            return

        verdict = self.risk.evaluate(decision, self.status)
        if not verdict.approved:
            self.journal.event("INFO", "decision_blocked", verdict.reason, decision.model_dump())
            return

        self._execute_decision(decision)

    def submit_test_order(self, request: TestOrderRequest) -> ControlResponse:
        decision = TradeDecision(
            action="buy" if request.side == "buy" else "sell",
            symbol=request.symbol,
            size=request.size,
            order_type=request.order_type,
            limit_price=request.limit_price,
            reduce_only=request.reduce_only,
            confidence=1.0,
            reason="manual test order from web UI",
            strategy_tag="manual_test",
        )
        verdict = self.risk.evaluate(decision, self.status)
        if not verdict.approved:
            self.journal.event("WARNING", "manual_test_order_blocked", verdict.reason, decision.model_dump())
            return ControlResponse(ok=False, message=verdict.reason)
        if not self.settings.allow_live_orders:
            return ControlResponse(ok=False, message="ALLOW_LIVE_ORDERS is false")
        if self.status.panic_mode:
            return ControlResponse(ok=False, message="panic mode is enabled")
        result = self._execute_decision(decision)
        return ControlResponse(ok=True, message="Test order submitted.", data={"response": result})

    def cancel_all(self) -> ControlResponse:
        results = self.client.cancel_all_orders()
        self.journal.event("WARNING", "cancel_all", "Canceled all open orders.", results)
        self.sync_once()
        return ControlResponse(ok=True, message="Canceled all open orders.", data={"results": results})

    def flatten(self, symbol: str) -> ControlResponse:
        if not self.settings.allow_live_orders:
            return ControlResponse(ok=False, message="ALLOW_LIVE_ORDERS is false")
        result = self.client.flatten_symbol(symbol)
        self.journal.event("WARNING", "flatten_symbol", f"Flattened {symbol}.", result)
        self.sync_once()
        return ControlResponse(ok=True, message=f"Flattened {symbol}.", data={"result": result})

    def panic(self, enabled: bool) -> ControlResponse:
        self.status.panic_mode = enabled
        level = "WARNING" if enabled else "INFO"
        self.journal.event(level, "panic_mode", f"Panic mode set to {enabled}.")
        return ControlResponse(ok=True, message=f"Panic mode set to {enabled}.")

    def health(self) -> dict[str, Any]:
        return {
            "app_name": self.settings.app_name,
            "configured": self.settings.is_configured,
            "connected": self.status.connected,
            "running": self.status.running,
            "panic_mode": self.status.panic_mode,
            "last_error": self.status.last_error,
            "latest_ws_message": self._latest_ws_message,
        }

    def _execute_decision(self, decision: TradeDecision) -> Any:
        is_buy = decision.action == "buy"
        request_payload = decision.model_dump()
        if decision.action == "close":
            result = self.client.flatten_symbol(decision.symbol)
            self.journal.order(
                symbol=decision.symbol,
                side="close",
                size=decision.size,
                order_type=decision.order_type,
                request_payload=request_payload,
                response_payload=result,
                status=_extract_status(result),
            )
            return result

        if decision.order_type == "limit":
            if decision.limit_price is None:
                raise ValueError("limit_price is required for limit orders")
            result = self.client.place_limit_order(
                decision.symbol, is_buy, decision.size, decision.limit_price, reduce_only=decision.reduce_only
            )
        else:
            result = self.client.place_market_order(
                decision.symbol, is_buy, decision.size, reduce_only=decision.reduce_only
            )
        self.journal.order(
            symbol=decision.symbol,
            side=decision.action,
            size=decision.size,
            order_type=decision.order_type,
            request_payload=request_payload,
            response_payload=result,
            status=_extract_status(result),
        )
        self.sync_once()
        return result

    def _record_error(self, event_type: str, exc: Exception) -> None:
        self.status.last_error = str(exc)
        self.status.connected = False
        logger.exception("%s: %s", event_type, exc)
        self.journal.event("ERROR", event_type, str(exc))


def _safe_mid(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_status(result: Any) -> str:
    if isinstance(result, dict):
        return str(result.get("status", "unknown"))
    return "unknown"
