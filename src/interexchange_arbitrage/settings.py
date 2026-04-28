from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import dotenv_values, load_dotenv


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



def load_settings(
    *,
    env_file: str | None = None,
    overrides: Mapping[str, str] | None = None,
) -> Settings:
    file_values: dict[str, str] = {}
    if env_file is not None:
        file_values = {
            key: value
            for key, value in dotenv_values(env_file).items()
            if value is not None
        }
    else:
        load_dotenv()

    def get_value(name: str, default: str) -> str:
        if overrides is not None and name in overrides:
            return str(overrides[name])
        if name in file_values:
            return file_values[name]
        value = os.getenv(name)
        return value if value is not None else default

    symbols = _parse_symbols(get_value("SYMBOLS", "BTC/USDT,ETH/USDT"))
    enabled_exchanges = _parse_enabled_exchanges(
        get_value("ENABLED_EXCHANGES", "binance,bybit")
    )
    min_net_spread_pct = float(get_value("MIN_NET_SPREAD_PCT", "0.2"))
    min_net_profit_quote = float(get_value("MIN_NET_PROFIT_QUOTE", "0"))
    trade_size_quote = float(get_value("TRADE_SIZE_QUOTE", "1000"))
    slippage_bps = float(get_value("SLIPPAGE_BPS", "2"))
    snapshot_csv_path = get_value(
        "SNAPSHOT_CSV_PATH", "data/arbitrage_opportunities.csv"
    )
    telegram_enabled = _parse_bool(get_value("TELEGRAM_ENABLED", "false"))
    telegram_bot_token = get_value("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = get_value("TELEGRAM_CHAT_ID", "")
    default_taker_fee_rate = float(get_value("DEFAULT_TAKER_FEE_RATE", "0.001"))

    exchange_fee_rate = {
        "binance": float(get_value("BINANCE_SPOT_FEE", str(default_taker_fee_rate))),
        "bybit": float(get_value("BYBIT_SPOT_FEE", str(default_taker_fee_rate))),
        "okx": float(get_value("OKX_SPOT_FEE", str(default_taker_fee_rate))),
        "kucoin": float(get_value("KUCOIN_SPOT_FEE", str(default_taker_fee_rate))),
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
