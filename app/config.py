from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Hyperliquid AI Bot", alias="APP_NAME")
    app_env: Literal["testnet", "mainnet"] = Field(default="testnet", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    hl_account_address: str = Field(default="", alias="HL_ACCOUNT_ADDRESS")
    hl_secret_key: str = Field(default="", alias="HL_SECRET_KEY")
    hl_symbol: str = Field(default="ETH", alias="HL_SYMBOL")

    default_test_order_size: float = Field(default=0.01, alias="DEFAULT_TEST_ORDER_SIZE")
    default_test_slippage: float = Field(default=0.01, alias="DEFAULT_TEST_SLIPPAGE")
    bot_mode: Literal["observe_only", "manual_test", "live"] = Field(
        default="observe_only", alias="BOT_MODE"
    )
    enable_websocket: bool = Field(default=True, alias="ENABLE_WEBSOCKET")
    poll_interval_seconds: int = Field(default=5, alias="POLL_INTERVAL_SECONDS")
    allow_live_orders: bool = Field(default=False, alias="ALLOW_LIVE_ORDERS")
    allow_mainnet: bool = Field(default=False, alias="ALLOW_MAINNET")

    max_order_size: float = Field(default=0.05, alias="MAX_ORDER_SIZE")
    max_notional_usd: float = Field(default=250.0, alias="MAX_NOTIONAL_USD")
    max_open_orders: int = Field(default=5, alias="MAX_OPEN_ORDERS")
    max_net_position: float = Field(default=0.05, alias="MAX_NET_POSITION")
    max_leverage: int = Field(default=3, alias="MAX_LEVERAGE")
    daily_loss_limit_usd: float = Field(default=50.0, alias="DAILY_LOSS_LIMIT_USD")
    panic_flatten_on_startup: bool = Field(default=False, alias="PANIC_FLATTEN_ON_STARTUP")
    cancel_all_on_startup: bool = Field(default=False, alias="CANCEL_ALL_ON_STARTUP")

    sqlite_path: str = Field(default="data/bot.sqlite3", alias="SQLITE_PATH")
    web_ui_bearer_token: str = Field(default="", alias="WEB_UI_BEARER_TOKEN")

    @field_validator("hl_symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @property
    def database_path(self) -> Path:
        return Path(self.sqlite_path)

    @property
    def is_mainnet(self) -> bool:
        return self.app_env == "mainnet"

    @property
    def is_configured(self) -> bool:
        return bool(self.hl_secret_key and self.hl_account_address)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
