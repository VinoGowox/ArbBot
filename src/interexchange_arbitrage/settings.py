from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    symbols: list[str]
    enabled_exchanges: list[str]
    min_net_spread_pct: float
    default_taker_fee_rate: float
    exchange_fee_rate: dict[str, float]



def _parse_symbols(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _parse_enabled_exchanges(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]



def load_settings() -> Settings:
    load_dotenv()

    symbols = _parse_symbols(os.getenv("SYMBOLS", "BTC/USDT,ETH/USDT"))
    enabled_exchanges = _parse_enabled_exchanges(
        os.getenv("ENABLED_EXCHANGES", "binance,bybit")
    )
    min_net_spread_pct = float(os.getenv("MIN_NET_SPREAD_PCT", "0.2"))
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
        default_taker_fee_rate=default_taker_fee_rate,
        exchange_fee_rate=exchange_fee_rate,
    )
