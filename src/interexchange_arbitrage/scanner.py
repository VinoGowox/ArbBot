from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from interexchange_arbitrage.engine import ArbitrageEngine
from interexchange_arbitrage.exchanges import (
    BinanceClient,
    BybitClient,
    ExchangeClient,
    KucoinClient,
    OkxClient,
)
from interexchange_arbitrage.models import ArbitrageOpportunity, TickerQuote
from interexchange_arbitrage.models import PaperTrade, PortfolioSummary
from interexchange_arbitrage.paper_trading import PaperTradingEngine
from interexchange_arbitrage.persistence import append_opportunities_csv
from interexchange_arbitrage.settings import Settings


EXCHANGE_CLIENTS: dict[str, type[ExchangeClient]] = {
    "binance": BinanceClient,
    "bybit": BybitClient,
    "okx": OkxClient,
    "kucoin": KucoinClient,
}


@dataclass(frozen=True)
class ScanResult:
    filtered_opportunities: list[ArbitrageOpportunity]
    all_candidates: list[ArbitrageOpportunity]
    warnings: list[str]
    executed_paper_trades: list[PaperTrade]
    portfolio_summary: PortfolioSummary | None


def build_clients(enabled_exchanges: list[str]) -> tuple[list[ExchangeClient], list[str]]:
    clients: list[ExchangeClient] = []
    warnings: list[str] = []

    for exchange_name in enabled_exchanges:
        client_cls = EXCHANGE_CLIENTS.get(exchange_name)
        if client_cls is None:
            warnings.append(f"Unknown exchange skipped: {exchange_name}")
            continue
        clients.append(client_cls())

    return clients, warnings


def fetch_quotes_for_symbol(
    symbol: str,
    clients: list[ExchangeClient],
) -> tuple[list[TickerQuote], list[str]]:
    quotes: list[TickerQuote] = []
    warnings: list[str] = []

    with ThreadPoolExecutor(max_workers=len(clients)) as executor:
        futures = [executor.submit(client.fetch_ticker, symbol) for client in clients]
        for future in as_completed(futures):
            try:
                quotes.append(future.result())
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Skip quote ({symbol}): {exc}")

    return quotes, warnings


def run_scan(settings: Settings, *, persist_candidates: bool = True) -> ScanResult:
    clients, warnings = build_clients(settings.enabled_exchanges)
    if len(clients) < 2:
        warnings.append("Need at least 2 enabled exchanges. Set ENABLED_EXCHANGES in .env.")
        return ScanResult(
            filtered_opportunities=[],
            all_candidates=[],
            warnings=warnings,
            executed_paper_trades=[],
            portfolio_summary=None,
        )

    engine = ArbitrageEngine(settings)
    filtered_opportunities: list[ArbitrageOpportunity] = []
    all_candidates: list[ArbitrageOpportunity] = []

    for symbol in settings.symbols:
        quotes, quote_warnings = fetch_quotes_for_symbol(symbol, clients)
        warnings.extend(quote_warnings)
        all_candidates.extend(engine.scan_symbol(quotes, apply_thresholds=False))
        filtered_opportunities.extend(engine.scan_symbol(quotes, apply_thresholds=True))

    if persist_candidates:
        append_opportunities_csv(
            all_candidates,
            settings.snapshot_csv_path,
            max_rows=settings.snapshot_csv_max_rows,
            max_backups=settings.snapshot_csv_max_backups,
        )

    executed_paper_trades: list[PaperTrade] = []
    portfolio_summary: PortfolioSummary | None = None
    if settings.paper_trading_enabled:
        paper_engine = PaperTradingEngine(settings)
        executed_paper_trades, portfolio_summary = paper_engine.execute(
            filtered_opportunities
        )

    filtered_opportunities.sort(key=lambda item: item.net_spread_pct, reverse=True)
    all_candidates.sort(key=lambda item: item.net_spread_pct, reverse=True)

    return ScanResult(
        filtered_opportunities=filtered_opportunities,
        all_candidates=all_candidates,
        warnings=warnings,
        executed_paper_trades=executed_paper_trades,
        portfolio_summary=portfolio_summary,
    )
