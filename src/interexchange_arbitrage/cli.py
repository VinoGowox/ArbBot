from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.table import Table

from interexchange_arbitrage.engine import ArbitrageEngine
from interexchange_arbitrage.exchanges import (
    BinanceClient,
    BybitClient,
    ExchangeClient,
    KucoinClient,
    OkxClient,
)
from interexchange_arbitrage.models import ArbitrageOpportunity, TickerQuote
from interexchange_arbitrage.settings import load_settings

console = Console()


EXCHANGE_CLIENTS: dict[str, type[ExchangeClient]] = {
    "binance": BinanceClient,
    "bybit": BybitClient,
    "okx": OkxClient,
    "kucoin": KucoinClient,
}


def build_clients(enabled_exchanges: list[str]) -> list[ExchangeClient]:
    clients: list[ExchangeClient] = []
    for exchange_name in enabled_exchanges:
        client_cls = EXCHANGE_CLIENTS.get(exchange_name)
        if client_cls is None:
            console.print(f"[yellow]Unknown exchange skipped: {exchange_name}[/yellow]")
            continue
        clients.append(client_cls())

    return clients


def fetch_quotes_for_symbol(symbol: str, clients: list[ExchangeClient]) -> list[TickerQuote]:
    quotes: list[TickerQuote] = []
    with ThreadPoolExecutor(max_workers=len(clients)) as executor:
        futures = [executor.submit(client.fetch_ticker, symbol) for client in clients]
        for future in as_completed(futures):
            try:
                quotes.append(future.result())
            except Exception as exc:  # noqa: BLE001
                console.print(f"[yellow]Skip quote ({symbol}): {exc}[/yellow]")
    return quotes


def render_opportunities(opportunities: list[ArbitrageOpportunity]) -> None:
    if not opportunities:
        console.print("[cyan]No opportunities above threshold.[/cyan]")
        return

    table = Table(title="Inter-Exchange Spot Arbitrage (Week 1)")
    table.add_column("Symbol")
    table.add_column("Buy")
    table.add_column("Sell")
    table.add_column("Ask", justify="right")
    table.add_column("Bid", justify="right")
    table.add_column("Gross %", justify="right")
    table.add_column("Net %", justify="right")
    table.add_column("Est. Profit/Unit", justify="right")

    for item in opportunities:
        table.add_row(
            item.symbol,
            item.buy_exchange,
            item.sell_exchange,
            f"{item.buy_price:.6f}",
            f"{item.sell_price:.6f}",
            f"{item.gross_spread_pct:.3f}",
            f"{item.net_spread_pct:.3f}",
            f"{item.estimated_profit_per_unit:.6f}",
        )

    console.print(table)


def main() -> None:
    settings = load_settings()
    engine = ArbitrageEngine(settings)
    clients = build_clients(settings.enabled_exchanges)
    if len(clients) < 2:
        console.print(
            "[red]Need at least 2 enabled exchanges. Set ENABLED_EXCHANGES in .env.[/red]"
        )
        return

    all_opportunities: list[ArbitrageOpportunity] = []

    for symbol in settings.symbols:
        quotes = fetch_quotes_for_symbol(symbol, clients)
        all_opportunities.extend(engine.scan_symbol(quotes))

    render_opportunities(all_opportunities)


if __name__ == "__main__":
    main()
