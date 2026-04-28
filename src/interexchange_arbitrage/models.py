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
    effective_buy_price: float
    effective_sell_price: float
    gross_spread_pct: float
    net_spread_pct: float
    trade_size_quote: float
    estimated_base_size: float
    estimated_profit_per_unit: float
    estimated_profit_quote: float
