from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from interexchange_arbitrage.models import ArbitrageOpportunity, PaperTrade, PortfolioSummary
from interexchange_arbitrage.settings import Settings


TRADE_HEADERS = [
    "run_at_utc",
    "symbol",
    "buy_exchange",
    "sell_exchange",
    "base_size",
    "buy_effective_price",
    "sell_effective_price",
    "buy_cost_quote",
    "sell_proceeds_quote",
    "estimated_profit_quote",
    "net_spread_pct",
]


@dataclass
class PaperPortfolio:
    quote_balances: dict[str, float]
    base_balances: dict[str, dict[str, float]]
    last_trade_ts_by_symbol: dict[str, float]
    total_executed_trades: int
    total_realized_profit_quote: float


class PaperTradingEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def _base_asset(symbol: str) -> str:
        return symbol.split("/", 1)[0]

    def _load_or_init_portfolio(self) -> PaperPortfolio:
        path = Path(self.settings.paper_state_path)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return PaperPortfolio(
                quote_balances={k: float(v) for k, v in payload.get("quote_balances", {}).items()},
                base_balances={
                    exchange: {symbol: float(v) for symbol, v in balances.items()}
                    for exchange, balances in payload.get("base_balances", {}).items()
                },
                last_trade_ts_by_symbol={
                    k: float(v) for k, v in payload.get("last_trade_ts_by_symbol", {}).items()
                },
                total_executed_trades=int(payload.get("total_executed_trades", 0)),
                total_realized_profit_quote=float(payload.get("total_realized_profit_quote", 0.0)),
            )

        quote_balances = {
            exchange: self.settings.paper_initial_quote_balance
            for exchange in self.settings.enabled_exchanges
        }

        base_balances: dict[str, dict[str, float]] = {}
        for exchange in self.settings.enabled_exchanges:
            base_balances[exchange] = {
                self._base_asset(symbol): self.settings.paper_initial_base_balance
                for symbol in self.settings.symbols
            }

        return PaperPortfolio(
            quote_balances=quote_balances,
            base_balances=base_balances,
            last_trade_ts_by_symbol={},
            total_executed_trades=0,
            total_realized_profit_quote=0.0,
        )

    def _save_portfolio(self, portfolio: PaperPortfolio) -> None:
        path = Path(self.settings.paper_state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "quote_balances": portfolio.quote_balances,
            "base_balances": portfolio.base_balances,
            "last_trade_ts_by_symbol": portfolio.last_trade_ts_by_symbol,
            "total_executed_trades": portfolio.total_executed_trades,
            "total_realized_profit_quote": portfolio.total_realized_profit_quote,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _append_trades(self, trades: list[PaperTrade]) -> None:
        if not trades:
            return

        path = Path(self.settings.paper_trades_csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists() or path.stat().st_size == 0

        with path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if write_header:
                writer.writerow(TRADE_HEADERS)

            for trade in trades:
                writer.writerow(
                    [
                        trade.run_at_utc.isoformat(),
                        trade.symbol,
                        trade.buy_exchange,
                        trade.sell_exchange,
                        trade.base_size,
                        trade.buy_effective_price,
                        trade.sell_effective_price,
                        trade.buy_cost_quote,
                        trade.sell_proceeds_quote,
                        trade.estimated_profit_quote,
                        trade.net_spread_pct,
                    ]
                )

    def _can_trade(
        self,
        portfolio: PaperPortfolio,
        opportunity: ArbitrageOpportunity,
        now_ts: float,
    ) -> tuple[bool, float]:
        cooldown_until = (
            portfolio.last_trade_ts_by_symbol.get(opportunity.symbol, 0.0)
            + self.settings.paper_cooldown_seconds
        )
        if now_ts < cooldown_until:
            return False, 0.0

        max_quote = min(opportunity.trade_size_quote, self.settings.paper_max_quote_per_trade)
        buy_quote_available = portfolio.quote_balances.get(opportunity.buy_exchange, 0.0)
        executable_quote = min(max_quote, buy_quote_available)
        if executable_quote <= 0:
            return False, 0.0

        base_asset = self._base_asset(opportunity.symbol)
        required_base = executable_quote / opportunity.effective_buy_price
        sell_base_available = portfolio.base_balances.get(opportunity.sell_exchange, {}).get(
            base_asset,
            0.0,
        )
        if sell_base_available <= 0:
            return False, 0.0

        executable_base = min(required_base, sell_base_available)
        if executable_base <= 0:
            return False, 0.0

        return True, executable_base

    def execute(self, opportunities: list[ArbitrageOpportunity]) -> tuple[list[PaperTrade], PortfolioSummary]:
        portfolio = self._load_or_init_portfolio()
        if not opportunities:
            summary = PortfolioSummary(
                total_quote_balance=sum(portfolio.quote_balances.values()),
                total_executed_trades=portfolio.total_executed_trades,
                total_realized_profit_quote=portfolio.total_realized_profit_quote,
            )
            return [], summary

        now = datetime.now(timezone.utc)
        now_ts = now.timestamp()
        executed: list[PaperTrade] = []

        for opportunity in opportunities:
            can_trade, base_size = self._can_trade(portfolio, opportunity, now_ts)
            if not can_trade:
                continue

            base_asset = self._base_asset(opportunity.symbol)
            buy_cost = base_size * opportunity.effective_buy_price
            sell_proceeds = base_size * opportunity.effective_sell_price
            pnl = sell_proceeds - buy_cost

            portfolio.quote_balances[opportunity.buy_exchange] = (
                portfolio.quote_balances.get(opportunity.buy_exchange, 0.0) - buy_cost
            )
            portfolio.quote_balances[opportunity.sell_exchange] = (
                portfolio.quote_balances.get(opportunity.sell_exchange, 0.0) + sell_proceeds
            )

            buy_base_balances = portfolio.base_balances.setdefault(opportunity.buy_exchange, {})
            sell_base_balances = portfolio.base_balances.setdefault(opportunity.sell_exchange, {})

            buy_base_balances[base_asset] = buy_base_balances.get(base_asset, 0.0) + base_size
            sell_base_balances[base_asset] = sell_base_balances.get(base_asset, 0.0) - base_size

            portfolio.last_trade_ts_by_symbol[opportunity.symbol] = now_ts
            portfolio.total_executed_trades += 1
            portfolio.total_realized_profit_quote += pnl

            executed.append(
                PaperTrade(
                    run_at_utc=now,
                    symbol=opportunity.symbol,
                    buy_exchange=opportunity.buy_exchange,
                    sell_exchange=opportunity.sell_exchange,
                    base_size=base_size,
                    buy_effective_price=opportunity.effective_buy_price,
                    sell_effective_price=opportunity.effective_sell_price,
                    buy_cost_quote=buy_cost,
                    sell_proceeds_quote=sell_proceeds,
                    estimated_profit_quote=pnl,
                    net_spread_pct=opportunity.net_spread_pct,
                )
            )

        self._save_portfolio(portfolio)
        self._append_trades(executed)

        summary = PortfolioSummary(
            total_quote_balance=sum(portfolio.quote_balances.values()),
            total_executed_trades=portfolio.total_executed_trades,
            total_realized_profit_quote=portfolio.total_realized_profit_quote,
        )
        return executed, summary
