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


@dataclass(frozen=True)
class PaperTrade:
    run_at_utc: datetime
    symbol: str
    buy_exchange: str
    sell_exchange: str
    base_size: float
    buy_effective_price: float
    sell_effective_price: float
    buy_cost_quote: float
    sell_proceeds_quote: float
    estimated_profit_quote: float
    net_spread_pct: float


@dataclass(frozen=True)
class PortfolioSummary:
    total_quote_balance: float
    total_executed_trades: int
    total_realized_profit_quote: float
