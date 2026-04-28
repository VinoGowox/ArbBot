from datetime import datetime, timezone

from interexchange_arbitrage.engine import ArbitrageEngine
from interexchange_arbitrage.models import TickerQuote
from interexchange_arbitrage.settings import Settings


def _settings_base() -> dict:
    return {
        "paper_trading_enabled": False,
        "paper_state_path": "data/paper_state_test.json",
        "paper_trades_csv_path": "data/paper_trades_test.csv",
        "paper_initial_quote_balance": 10000.0,
        "paper_initial_base_balance": 0.1,
        "paper_max_quote_per_trade": 1000.0,
        "paper_cooldown_seconds": 60,
        "snapshot_csv_max_rows": 20000,
        "snapshot_csv_max_backups": 5,
    }


def test_scan_symbol_returns_net_profitable_opportunity() -> None:
    settings = Settings(
        symbols=["BTC/USDT"],
        enabled_exchanges=["binance", "bybit"],
        min_net_spread_pct=0.2,
        min_net_profit_quote=0.0,
        trade_size_quote=1000.0,
        slippage_bps=0.0,
        snapshot_csv_path="data/test.csv",
        telegram_enabled=False,
        telegram_bot_token="",
        telegram_chat_id="",
        **_settings_base(),
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
    assert top.estimated_profit_quote > 0


def test_scan_symbol_respects_min_net_profit_quote_threshold() -> None:
    settings = Settings(
        symbols=["BTC/USDT"],
        enabled_exchanges=["binance", "bybit"],
        min_net_spread_pct=-10.0,
        min_net_profit_quote=5.0,
        trade_size_quote=1000.0,
        slippage_bps=0.0,
        snapshot_csv_path="data/test.csv",
        telegram_enabled=False,
        telegram_bot_token="",
        telegram_chat_id="",
        **_settings_base(),
        default_taker_fee_rate=0.0,
        exchange_fee_rate={"binance": 0.0, "bybit": 0.0},
    )
    engine = ArbitrageEngine(settings)

    quotes = [
        TickerQuote(
            exchange="binance",
            symbol="BTC/USDT",
            bid=100.0,
            ask=100.0,
            timestamp=datetime.now(timezone.utc),
        ),
        TickerQuote(
            exchange="bybit",
            symbol="BTC/USDT",
            bid=100.1,
            ask=100.2,
            timestamp=datetime.now(timezone.utc),
        ),
    ]

    opportunities = engine.scan_symbol(quotes)

    assert opportunities == []
