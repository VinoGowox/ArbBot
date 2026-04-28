from datetime import datetime, timezone

from interexchange_arbitrage.models import ArbitrageOpportunity
from interexchange_arbitrage.paper_trading import PaperTradingEngine
from interexchange_arbitrage.settings import Settings


def _build_settings(state_path: str, trades_path: str) -> Settings:
    return Settings(
        symbols=["BTC/USDT"],
        enabled_exchanges=["binance", "bybit"],
        min_net_spread_pct=0.0,
        min_net_profit_quote=0.0,
        trade_size_quote=1000.0,
        slippage_bps=0.0,
        snapshot_csv_path="data/opps_test.csv",
        telegram_enabled=False,
        telegram_bot_token="",
        telegram_chat_id="",
        paper_trading_enabled=True,
        paper_state_path=state_path,
        paper_trades_csv_path=trades_path,
        paper_initial_quote_balance=10000.0,
        paper_initial_base_balance=1.0,
        paper_max_quote_per_trade=1000.0,
        paper_cooldown_seconds=0,
        default_taker_fee_rate=0.001,
        exchange_fee_rate={"binance": 0.001, "bybit": 0.001},
    )


def test_paper_trading_engine_executes_and_updates_state(tmp_path) -> None:
    state_path = str(tmp_path / "paper_state.json")
    trades_path = str(tmp_path / "paper_trades.csv")
    settings = _build_settings(state_path, trades_path)

    engine = PaperTradingEngine(settings)
    now = datetime.now(timezone.utc)

    opportunities = [
        ArbitrageOpportunity(
            symbol="BTC/USDT",
            buy_exchange="binance",
            sell_exchange="bybit",
            buy_price=100.0,
            sell_price=101.0,
            effective_buy_price=100.2,
            effective_sell_price=100.8,
            gross_spread_pct=1.0,
            net_spread_pct=0.5,
            trade_size_quote=1000.0,
            estimated_base_size=9.98,
            estimated_profit_per_unit=0.6,
            estimated_profit_quote=5.988,
        )
    ]

    trades, summary = engine.execute(opportunities)

    assert len(trades) == 1
    assert trades[0].symbol == "BTC/USDT"
    assert summary.total_executed_trades == 1
    assert summary.total_realized_profit_quote > 0
