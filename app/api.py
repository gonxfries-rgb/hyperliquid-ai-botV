from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.db import Database
from app.hl_client import HyperliquidClient
from app.journal import Journal
from app.models import ControlResponse, TestOrderRequest
from app.service import BotService

logging.basicConfig(level=logging.INFO)
settings = get_settings()
database = Database(settings.database_path)
journal = Journal(database)
client = HyperliquidClient(settings)
service = BotService(settings, client, journal)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if settings.is_configured:
            service.connect()
            journal.event("INFO", "startup", "Service connected to Hyperliquid.")
        else:
            journal.event(
                "WARNING",
                "startup_unconfigured",
                "Service started without Hyperliquid credentials. Set HL_ACCOUNT_ADDRESS and HL_SECRET_KEY.",
            )
    except Exception as exc:
        journal.event("ERROR", "startup_failed", str(exc))
    yield
    try:
        service.stop()
        client.disconnect()
    except Exception:
        pass


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def require_token(authorization: str | None = Header(default=None)) -> None:
    token = settings.web_ui_bearer_token.strip()
    if not token:
        return
    expected = f"Bearer {token}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health(_: None = Depends(require_token)) -> dict:
    return service.health()


@app.get("/api/status")
def bot_status(_: None = Depends(require_token)) -> dict:
    return service.status.model_dump(mode="json")


@app.get("/api/events")
def events(limit: int = 50, _: None = Depends(require_token)) -> dict:
    return {"items": journal.recent_events(limit=limit)}


@app.get("/api/orders")
def orders(limit: int = 50, _: None = Depends(require_token)) -> dict:
    return {"items": journal.recent_orders(limit=limit)}


@app.get("/api/decisions")
def decisions(limit: int = 50, _: None = Depends(require_token)) -> dict:
    return {"items": journal.recent_decisions(limit=limit)}


@app.post("/api/control/start", response_model=ControlResponse)
def start(_: None = Depends(require_token)) -> ControlResponse:
    return service.start()


@app.post("/api/control/stop", response_model=ControlResponse)
def stop(_: None = Depends(require_token)) -> ControlResponse:
    return service.stop()


@app.post("/api/control/panic/{enabled}", response_model=ControlResponse)
def panic(enabled: bool, _: None = Depends(require_token)) -> ControlResponse:
    return service.panic(enabled)


@app.post("/api/control/cancel-all", response_model=ControlResponse)
def cancel_all(_: None = Depends(require_token)) -> ControlResponse:
    return service.cancel_all()


@app.post("/api/control/flatten/{symbol}", response_model=ControlResponse)
def flatten(symbol: str, _: None = Depends(require_token)) -> ControlResponse:
    return service.flatten(symbol.upper())


@app.post("/api/control/test-order", response_model=ControlResponse)
def test_order(request: TestOrderRequest, _: None = Depends(require_token)) -> ControlResponse:
    request.symbol = request.symbol.upper()
    return service.submit_test_order(request)
