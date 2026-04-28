from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    symbols: list[str]
    enabled_exchanges: list[str]
    min_net_spread_pct: float
    min_net_profit_quote: float
    trade_size_quote: float
    slippage_bps: float
    snapshot_csv_path: str
    telegram_enabled: bool
    telegram_bot_token: str
    telegram_chat_id: str
    default_taker_fee_rate: float
    exchange_fee_rate: dict[str, float]



def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _parse_enabled_exchanges(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}



def load_settings() -> Settings:
    load_dotenv()

    symbols = _parse_symbols(os.getenv("SYMBOLS", "BTC/USDT,ETH/USDT"))
    enabled_exchanges = _parse_enabled_exchanges(
        os.getenv("ENABLED_EXCHANGES", "binance,bybit")
    )
    min_net_spread_pct = float(os.getenv("MIN_NET_SPREAD_PCT", "0.2"))
    min_net_profit_quote = float(os.getenv("MIN_NET_PROFIT_QUOTE", "0"))
    trade_size_quote = float(os.getenv("TRADE_SIZE_QUOTE", "1000"))
    slippage_bps = float(os.getenv("SLIPPAGE_BPS", "2"))
    snapshot_csv_path = os.getenv(
        "SNAPSHOT_CSV_PATH", "data/arbitrage_opportunities.csv"
    )
    telegram_enabled = _parse_bool(os.getenv("TELEGRAM_ENABLED", "false"))
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    default_taker_fee_rate = float(os.getenv("DEFAULT_TAKER_FEE_RATE", "0.001"))

    exchange_fee_rate = {
        "binance": float(os.getenv("BINANCE_SPOT_FEE", str(default_taker_fee_rate))),
        "bybit": float(os.getenv("BYBIT_SPOT_FEE", str(default_taker_fee_rate))),
        "okx": float(os.getenv("OKX_SPOT_FEE", str(default_taker_fee_rate))),
        "kucoin": float(os.getenv("KUCOIN_SPOT_FEE", str(default_taker_fee_rate))),
    }

    return Settings(
        symbols=symbols,
        enabled_exchanges=enabled_exchanges,
        min_net_spread_pct=min_net_spread_pct,
        min_net_profit_quote=min_net_profit_quote,
        trade_size_quote=trade_size_quote,
        slippage_bps=slippage_bps,
        snapshot_csv_path=snapshot_csv_path,
        telegram_enabled=telegram_enabled,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        default_taker_fee_rate=default_taker_fee_rate,
        exchange_fee_rate=exchange_fee_rate,
    )
