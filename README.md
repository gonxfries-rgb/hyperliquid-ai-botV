# Hyperliquid AI Bot Starter

A GitHub-ready starter project for a **Hyperliquid-compatible trading bot** with:

- Hyperliquid **Info**, **Exchange**, and optional **WebSocket** integration
- strict execution/risk shell separate from the future AI decision layer
- SQLite journaling for decisions, orders, and bot events
- small FastAPI-based web UI for status and controls
- safe defaults: **testnet-first**, observe-only mode, live orders disabled

## What this repo is

This is a **Phase 1 / compatibility-first** bot. It is built to help you prove that the bot can:

1. connect to Hyperliquid
2. read account + exchange state
3. place/cancel small test orders
4. flatten/cancel safely
5. recover state on restart
6. expose status through a small web UI

The architecture already includes a decision contract so you can add the AI layer later without rewriting the execution shell.

## Why it is structured this way

Hyperliquid’s API is organized around the **Info endpoint** for reads, the **Exchange endpoint** for signed trade actions, and **WebSocket** endpoints for live data and alternative request sending. Hyperliquid also documents separate mainnet/testnet URLs, recommends using an existing SDK for signing, recommends a separate API wallet per trading process, and tracks nonces per signer. That is why this starter uses the official Python SDK, defaults to testnet, keeps the signing key separate from the account address, and serializes execution behind a service layer. citeturn144882search0turn144882search4turn511255search8turn511255search2turn795762view0

## Features

- **Safe startup reconciliation**
  - pulls `user_state`, `open_orders`, recent fills, and mids before trading
- **Config-driven environment switch**
  - testnet by default, mainnet blocked unless explicitly enabled
- **Risk engine**
  - max order size
  - max notional
  - max net position
  - max open orders
  - daily loss cap
- **Execution controls**
  - cancel all orders
  - flatten symbol
  - emergency panic mode
- **Web UI**
  - start/stop loop
  - panic mode toggle
  - submit small test orders
  - cancel all / flatten
  - view positions, open orders, recent events
- **Decision engine contract**
  - `HoldDecisionEngine` included now
  - clean place to plug in your AI later

## Current defaults

- `APP_ENV=testnet`
- `BOT_MODE=observe_only`
- `ALLOW_LIVE_ORDERS=false`
- `WEB_UI_BEARER_TOKEN` support for locking down the UI/API

FastAPI supports standard bearer-token auth patterns, and its docs note that OAuth2/JWT-based bearer token flows are supported, which is why the API layer is ready for authenticated control endpoints. citeturn311782search3turn311782search1turn311782search9

## Project layout

```text
hyperliquid-ai-bot/
├── app/
│   ├── api.py
│   ├── config.py
│   ├── db.py
│   ├── decision_engines.py
│   ├── hl_client.py
│   ├── journal.py
│   ├── models.py
│   ├── risk.py
│   ├── service.py
│   ├── static/
│   │   ├── index.html
│   │   └── app.js
│   └── __init__.py
├── tests/
│   └── test_risk.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Requirements

- Python 3.10+
- a Hyperliquid account
- ideally a **dedicated API wallet** private key
- if using an API wallet, keep your **main wallet public address** in `HL_ACCOUNT_ADDRESS`

The current SDK README explicitly says that when using an API wallet, the API wallet private key goes in `secret_key` and the main wallet public key remains the `account_address`. citeturn795762view0

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
```

Fill in `.env`:

- `HL_ACCOUNT_ADDRESS` = **main wallet public address**
- `HL_SECRET_KEY` = **API wallet private key**

## Testnet notes

Hyperliquid documents that the same API calls can be made against testnet by switching from `https://api.hyperliquid.xyz` to `https://api.hyperliquid-testnet.xyz`, and the WebSocket URLs are likewise separated by network. Hyperliquid also documents a testnet faucet that currently requires a mainnet deposit with the same address before claiming mock USDC. citeturn144882search0turn144882search4turn144882search3

## Running the bot

```bash
uvicorn app.api:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

If you set `WEB_UI_BEARER_TOKEN`, add this header in your browser/dev client for API calls:

```text
Authorization: Bearer <your token>
```

## First workflow I recommend

1. keep `APP_ENV=testnet`
2. keep `ALLOW_LIVE_ORDERS=false`
3. start the web UI and confirm the bot can connect
4. review status, positions, mids, and open orders
5. enable `ALLOW_LIVE_ORDERS=true` only on testnet
6. submit a **small** test order through the UI
7. cancel or flatten through the UI
8. confirm the journal rows in SQLite

## Safety notes

Hyperliquid recommends using an existing SDK instead of manually generating signatures because there are multiple ways to get signatures wrong, including field ordering, trailing zero handling, and choosing the wrong signing scheme. Hyperliquid also documents only the 100 highest nonces per signer being stored and recommends a separate API wallet per trading process plus an atomic nonce strategy for batches. Hyperliquid’s websocket docs note that automated users should handle disconnects gracefully and that missed data will be present in the snapshot ack on reconnect; idle connections may be closed after 60 seconds unless you send heartbeat pings. citeturn511255search8turn511255search2turn144882search4turn511255search1

This repo therefore assumes:

- API wallet instead of your main private key
- testnet first
- explicit mainnet opt-in
- live orders off by default
- panic/cancel/flatten controls available in the UI/API

## GitHub upload

```bash
git init
git add .
git commit -m "Initial Hyperliquid bot starter"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Next steps after this starter

- plug in an AI decision engine that returns the `TradeDecision` schema
- add richer websocket-driven market state
- add real authentication + HTTPS reverse proxy for any remote deployment
- add backtesting and paper trading modes
- add strategy-specific execution policies
