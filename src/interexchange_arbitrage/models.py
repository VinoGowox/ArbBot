from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TickerQuote:
    exchange: str
    symbol: str
    bid: float
    ask: float
    timestamp: datetime


@dataclass(frozen=True)
class ArbitrageOpportunity:
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    gross_spread_pct: float
    net_spread_pct: float
    estimated_profit_per_unit: float
