from datetime import datetime, timezone

from interexchange_arbitrage.engine import ArbitrageEngine
from interexchange_arbitrage.models import TickerQuote
from interexchange_arbitrage.settings import Settings


def test_scan_symbol_returns_net_profitable_opportunity() -> None:
    settings = Settings(
        symbols=["BTC/USDT"],
        enabled_exchanges=["binance", "bybit"],
        min_net_spread_pct=0.2,
        default_taker_fee_rate=0.001,
        exchange_fee_rate={"binance": 0.001, "bybit": 0.001},
    )
    engine = ArbitrageEngine(settings)

    quotes = [
        TickerQuote(
            exchange="binance",
            symbol="BTC/USDT",
            bid=100.0,
            ask=99.0,
            timestamp=datetime.now(timezone.utc),
        ),
        TickerQuote(
            exchange="bybit",
            symbol="BTC/USDT",
            bid=101.0,
            ask=100.8,
            timestamp=datetime.now(timezone.utc),
        ),
    ]

    opportunities = engine.scan_symbol(quotes)

    assert len(opportunities) == 1
    top = opportunities[0]
    assert top.buy_exchange == "binance"
    assert top.sell_exchange == "bybit"
    assert top.net_spread_pct > 0.2
