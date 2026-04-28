from __future__ import annotations

from rich.console import Console
from rich.table import Table

from interexchange_arbitrage.alerts import build_alert_message, send_telegram_alert
from interexchange_arbitrage.models import ArbitrageOpportunity, PaperTrade
from interexchange_arbitrage.scanner import run_scan
from interexchange_arbitrage.settings import load_settings

console = Console()


def render_opportunities(opportunities: list[ArbitrageOpportunity]) -> None:
    if not opportunities:
        console.print("[cyan]No opportunities above threshold.[/cyan]")
        return

    table = Table(title="Inter-Exchange Spot Arbitrage (Week 3)")
    table.add_column("Symbol")
    table.add_column("Buy")
    table.add_column("Sell")
    table.add_column("Ask", justify="right")
    table.add_column("Bid", justify="right")
    table.add_column("Gross %", justify="right")
    table.add_column("Net %", justify="right")
    table.add_column("Size (Quote)", justify="right")
    table.add_column("Est. Profit", justify="right")

    for item in opportunities:
        table.add_row(
            item.symbol,
            item.buy_exchange,
            item.sell_exchange,
            f"{item.buy_price:.6f}",
            f"{item.sell_price:.6f}",
            f"{item.gross_spread_pct:.3f}",
            f"{item.net_spread_pct:.3f}",
            f"{item.trade_size_quote:.2f}",
            f"{item.estimated_profit_quote:.6f}",
        )

    console.print(table)


def render_paper_trades(trades: list[PaperTrade]) -> None:
    if not trades:
        console.print("[cyan]No paper trades executed this run.[/cyan]")
        return

    table = Table(title="Paper Trades (Week 3)")
    table.add_column("Symbol")
    table.add_column("Buy")
    table.add_column("Sell")
    table.add_column("Base Size", justify="right")
    table.add_column("Net %", justify="right")
    table.add_column("PnL Quote", justify="right")

    for trade in trades:
        table.add_row(
            trade.symbol,
            trade.buy_exchange,
            trade.sell_exchange,
            f"{trade.base_size:.6f}",
            f"{trade.net_spread_pct:.4f}",
            f"{trade.estimated_profit_quote:.6f}",
        )

    console.print(table)


def main() -> None:
    settings = load_settings()
    scan_result = run_scan(settings, persist_candidates=True)

    for warning in scan_result.warnings:
        console.print(f"[yellow]{warning}[/yellow]")

    if scan_result.filtered_opportunities:
        render_opportunities(scan_result.filtered_opportunities)
        if settings.telegram_enabled:
            top = scan_result.filtered_opportunities[0]
            try:
                send_telegram_alert(
                    settings.telegram_bot_token,
                    settings.telegram_chat_id,
                    build_alert_message(top),
                )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[yellow]Telegram alert failed: {exc}[/yellow]")
    else:
        render_opportunities(scan_result.all_candidates[:5])
        console.print("[cyan]No opportunities above threshold.[/cyan]")

    render_paper_trades(scan_result.executed_paper_trades)
    if scan_result.portfolio_summary is not None:
        summary = scan_result.portfolio_summary
        console.print(
            "[green]Paper portfolio:[/green] "
            f"quote_balance={summary.total_quote_balance:.2f}, "
            f"trades={summary.total_executed_trades}, "
            f"realized_pnl={summary.total_realized_profit_quote:.6f}"
        )


if __name__ == "__main__":
    main()
