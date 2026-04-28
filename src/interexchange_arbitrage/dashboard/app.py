from __future__ import annotations

import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any


from dotenv import set_key
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from interexchange_arbitrage.scanner import ScanResult, run_scan
from interexchange_arbitrage.settings import Settings, load_settings

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
SERVICE_NAME = os.getenv("ARB_SERVICE_NAME", "interexchange-arbitrage")
DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "changeme")
DASHBOARD_SESSION_SECRET = os.getenv(
    "DASHBOARD_SESSION_SECRET",
    "change-this-dashboard-session-secret",
)


def _ensure_env_file() -> None:
    if ENV_FILE.exists():
        return
    if ENV_EXAMPLE_FILE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        ENV_FILE.write_text("", encoding="utf-8")


def _current_settings() -> Settings:
    _ensure_env_file()
    return load_settings(env_file=str(ENV_FILE))


def _service_status() -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except Exception:
        return "unknown"

    value = (result.stdout or result.stderr).strip().lower()
    if not value:
        return "unknown"
    return value


def _read_signals(csv_path: str, limit: int = 30) -> list[dict[str, str]]:
    path = Path(csv_path)
    if not path.exists() or path.stat().st_size == 0:
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    return list(reversed(rows[-limit:]))


def _safe_float(value: str | None) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_chart_data(signals: list[dict[str, str]]) -> dict[str, list[float] | list[str]]:
    # Reverse for left-to-right chronological chart rendering.
    asc = list(reversed(signals))
    labels = [row.get("run_at_utc", "")[-8:] for row in asc]
    net_spread = [_safe_float(row.get("net_spread_pct")) for row in asc]
    profit_quote = [_safe_float(row.get("estimated_profit_quote")) for row in asc]
    return {
        "labels": labels,
        "net_spread": net_spread,
        "profit_quote": profit_quote,
    }


def _read_paper_portfolio(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.exists():
        return {
            "total_quote_balance": 0.0,
            "total_executed_trades": 0,
            "total_realized_profit_quote": 0.0,
        }

    payload = json.loads(path.read_text(encoding="utf-8"))
    quote_balances = payload.get("quote_balances", {})
    return {
        "total_quote_balance": sum(float(v) for v in quote_balances.values()),
        "total_executed_trades": int(payload.get("total_executed_trades", 0)),
        "total_realized_profit_quote": float(payload.get("total_realized_profit_quote", 0.0)),
    }


def _read_paper_trades(path_value: str, limit: int = 20) -> list[dict[str, str]]:
    path = Path(path_value)
    if not path.exists() or path.stat().st_size == 0:
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    return list(reversed(rows[-limit:]))


def _dashboard_context(
    request: Request,
    settings: Settings,
    signals: list[dict[str, str]],
    status: str,
    scan_result: ScanResult | None,
    messages: list[str],
) -> dict[str, Any]:
    chart_data = _build_chart_data(signals)
    latest_net_spread = _safe_float(signals[0].get("net_spread_pct")) if signals else 0.0
    latest_profit_quote = (
        _safe_float(signals[0].get("estimated_profit_quote")) if signals else 0.0
    )
    paper_portfolio = _read_paper_portfolio(settings.paper_state_path)
    paper_trades = _read_paper_trades(settings.paper_trades_csv_path)

    return {
        "settings": _settings_payload(settings),
        "signals": signals,
        "service_status": status,
        "scan_result": scan_result,
        "messages": messages,
        "chart_data": chart_data,
        "latest_net_spread": latest_net_spread,
        "latest_profit_quote": latest_profit_quote,
        "paper_portfolio": paper_portfolio,
        "paper_trades": paper_trades,
    }


def _settings_payload(settings: Settings) -> dict[str, str]:
    return {
        "SYMBOLS": ",".join(settings.symbols),
        "ENABLED_EXCHANGES": ",".join(settings.enabled_exchanges),
        "MIN_NET_SPREAD_PCT": str(settings.min_net_spread_pct),
        "MIN_NET_PROFIT_QUOTE": str(settings.min_net_profit_quote),
        "TRADE_SIZE_QUOTE": str(settings.trade_size_quote),
        "SLIPPAGE_BPS": str(settings.slippage_bps),
        "SNAPSHOT_CSV_PATH": settings.snapshot_csv_path,
        "DEFAULT_TAKER_FEE_RATE": str(settings.default_taker_fee_rate),
        "BINANCE_SPOT_FEE": str(settings.exchange_fee_rate.get("binance", settings.default_taker_fee_rate)),
        "BYBIT_SPOT_FEE": str(settings.exchange_fee_rate.get("bybit", settings.default_taker_fee_rate)),
        "OKX_SPOT_FEE": str(settings.exchange_fee_rate.get("okx", settings.default_taker_fee_rate)),
        "KUCOIN_SPOT_FEE": str(settings.exchange_fee_rate.get("kucoin", settings.default_taker_fee_rate)),
        "TELEGRAM_ENABLED": "true" if settings.telegram_enabled else "false",
        "TELEGRAM_BOT_TOKEN": settings.telegram_bot_token,
        "TELEGRAM_CHAT_ID": settings.telegram_chat_id,
        "PAPER_TRADING_ENABLED": "true" if settings.paper_trading_enabled else "false",
        "PAPER_STATE_PATH": settings.paper_state_path,
        "PAPER_TRADES_CSV_PATH": settings.paper_trades_csv_path,
        "PAPER_INITIAL_QUOTE_BALANCE": str(settings.paper_initial_quote_balance),
        "PAPER_INITIAL_BASE_BALANCE": str(settings.paper_initial_base_balance),
        "PAPER_MAX_QUOTE_PER_TRADE": str(settings.paper_max_quote_per_trade),
        "PAPER_COOLDOWN_SECONDS": str(settings.paper_cooldown_seconds),
    }


def _save_settings(payload: dict[str, str]) -> None:
    _ensure_env_file()
    for key, value in payload.items():
        set_key(str(ENV_FILE), key, value)


def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("dashboard_authenticated"))


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=303)


app = FastAPI(title="ArbBot Dashboard", version="0.1.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=DASHBOARD_SESSION_SECRET,
    max_age=12 * 60 * 60,
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/login")
def login_page(request: Request) -> Any:
    if _is_authenticated(request):
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": "",
        },
    )


@app.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> Any:
    if username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD:
        request.session["dashboard_authenticated"] = True
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": "Invalid username or password.",
        },
        status_code=401,
    )


@app.post("/logout")
def logout(request: Request) -> Any:
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/")
def dashboard(request: Request) -> Any:
    if not _is_authenticated(request):
        return _redirect_login()

    settings = _current_settings()
    signals = _read_signals(settings.snapshot_csv_path)
    status = _service_status()
    return templates.TemplateResponse(
        request,
        "index.html",
        _dashboard_context(request, settings, signals, status, None, []),
    )


@app.post("/settings")
def update_settings(
    request: Request,
    symbols: str = Form(...),
    enabled_exchanges: str = Form(...),
    min_net_spread_pct: str = Form(...),
    min_net_profit_quote: str = Form(...),
    trade_size_quote: str = Form(...),
    slippage_bps: str = Form(...),
    snapshot_csv_path: str = Form(...),
    default_taker_fee_rate: str = Form(...),
    binance_spot_fee: str = Form(...),
    bybit_spot_fee: str = Form(...),
    okx_spot_fee: str = Form(...),
    kucoin_spot_fee: str = Form(...),
    telegram_enabled: str = Form("false"),
    telegram_bot_token: str = Form(""),
    telegram_chat_id: str = Form(""),
    paper_trading_enabled: str = Form("true"),
    paper_state_path: str = Form(...),
    paper_trades_csv_path: str = Form(...),
    paper_initial_quote_balance: str = Form(...),
    paper_initial_base_balance: str = Form(...),
    paper_max_quote_per_trade: str = Form(...),
    paper_cooldown_seconds: str = Form(...),
) -> Any:
    if not _is_authenticated(request):
        return _redirect_login()

    _save_settings(
        {
            "SYMBOLS": symbols,
            "ENABLED_EXCHANGES": enabled_exchanges,
            "MIN_NET_SPREAD_PCT": min_net_spread_pct,
            "MIN_NET_PROFIT_QUOTE": min_net_profit_quote,
            "TRADE_SIZE_QUOTE": trade_size_quote,
            "SLIPPAGE_BPS": slippage_bps,
            "SNAPSHOT_CSV_PATH": snapshot_csv_path,
            "DEFAULT_TAKER_FEE_RATE": default_taker_fee_rate,
            "BINANCE_SPOT_FEE": binance_spot_fee,
            "BYBIT_SPOT_FEE": bybit_spot_fee,
            "OKX_SPOT_FEE": okx_spot_fee,
            "KUCOIN_SPOT_FEE": kucoin_spot_fee,
            "TELEGRAM_ENABLED": telegram_enabled,
            "TELEGRAM_BOT_TOKEN": telegram_bot_token,
            "TELEGRAM_CHAT_ID": telegram_chat_id,
            "PAPER_TRADING_ENABLED": paper_trading_enabled,
            "PAPER_STATE_PATH": paper_state_path,
            "PAPER_TRADES_CSV_PATH": paper_trades_csv_path,
            "PAPER_INITIAL_QUOTE_BALANCE": paper_initial_quote_balance,
            "PAPER_INITIAL_BASE_BALANCE": paper_initial_base_balance,
            "PAPER_MAX_QUOTE_PER_TRADE": paper_max_quote_per_trade,
            "PAPER_COOLDOWN_SECONDS": paper_cooldown_seconds,
        }
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/scan-test")
def scan_test(request: Request) -> Any:
    if not _is_authenticated(request):
        return _redirect_login()

    settings = _current_settings()
    scan_result: ScanResult = run_scan(settings, persist_candidates=False)
    signals = _read_signals(settings.snapshot_csv_path)
    status = _service_status()

    return templates.TemplateResponse(
        request,
        "index.html",
        _dashboard_context(
            request,
            settings,
            signals,
            status,
            scan_result,
            ["One-off scan finished from dashboard."],
        ),
    )
