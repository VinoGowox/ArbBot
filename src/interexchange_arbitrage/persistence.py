from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from interexchange_arbitrage.csv_cycle import rotate_csv_if_needed
from interexchange_arbitrage.models import ArbitrageOpportunity


CSV_HEADERS = [
    "run_at_utc",
    "symbol",
    "buy_exchange",
    "sell_exchange",
    "buy_price",
    "sell_price",
    "effective_buy_price",
    "effective_sell_price",
    "gross_spread_pct",
    "net_spread_pct",
    "trade_size_quote",
    "estimated_base_size",
    "estimated_profit_per_unit",
    "estimated_profit_quote",
]


def append_opportunities_csv(
    opportunities: list[ArbitrageOpportunity],
    csv_path: str,
    *,
    max_rows: int,
    max_backups: int,
) -> None:
    if not opportunities:
        return

    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rotate_csv_if_needed(
        path,
        CSV_HEADERS,
        max_rows=max_rows,
        max_backups=max_backups,
    )

    write_header = not path.exists() or path.stat().st_size == 0
    run_at = datetime.now(timezone.utc).isoformat()

    with path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        if write_header:
            writer.writerow(CSV_HEADERS)

        for item in opportunities:
            writer.writerow(
                [
                    run_at,
                    item.symbol,
                    item.buy_exchange,
                    item.sell_exchange,
                    item.buy_price,
                    item.sell_price,
                    item.effective_buy_price,
                    item.effective_sell_price,
                    item.gross_spread_pct,
                    item.net_spread_pct,
                    item.trade_size_quote,
                    item.estimated_base_size,
                    item.estimated_profit_per_unit,
                    item.estimated_profit_quote,
                ]
            )
