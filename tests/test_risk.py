from app.config import Settings
from app.models import BotStatus, OpenOrderSnapshot, PositionSnapshot, TradeDecision
from app.risk import RiskEngine


def make_settings() -> Settings:
    return Settings(
        HL_ACCOUNT_ADDRESS="0xabc",
        HL_SECRET_KEY="0xdef",
        MAX_ORDER_SIZE=0.05,
        MAX_NOTIONAL_USD=200,
        MAX_OPEN_ORDERS=2,
        MAX_NET_POSITION=0.10,
        APP_ENV="testnet",
    )


def make_status() -> BotStatus:
    status = BotStatus.fresh("testnet", "observe_only", "ETH")
    status.current_mid = 2000
    return status


def test_blocks_size_above_limit():
    settings = make_settings()
    risk = RiskEngine(settings)
    decision = TradeDecision(action="buy", symbol="ETH", size=0.2, confidence=1.0)
    verdict = risk.evaluate(decision, make_status())
    assert verdict.approved is False
    assert "MAX_ORDER_SIZE" in verdict.reason


def test_blocks_excess_open_orders():
    settings = make_settings()
    risk = RiskEngine(settings)
    status = make_status()
    status.open_orders = [
        OpenOrderSnapshot(coin="ETH", oid=1, side="B", size=0.01, limit_price=1000, timestamp=1),
        OpenOrderSnapshot(coin="ETH", oid=2, side="A", size=0.01, limit_price=1001, timestamp=2),
    ]
    decision = TradeDecision(action="buy", symbol="ETH", size=0.01, confidence=1.0)
    verdict = risk.evaluate(decision, status)
    assert verdict.approved is False
    assert "MAX_OPEN_ORDERS" in verdict.reason


def test_allows_small_order():
    settings = make_settings()
    risk = RiskEngine(settings)
    status = make_status()
    status.positions = [PositionSnapshot(coin="ETH", size=0.01)]
    decision = TradeDecision(action="buy", symbol="ETH", size=0.02, confidence=1.0)
    verdict = risk.evaluate(decision, status)
    assert verdict.approved is True
