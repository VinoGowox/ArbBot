from __future__ import annotations

from itertools import permutations

from interexchange_arbitrage.models import ArbitrageOpportunity, TickerQuote
from interexchange_arbitrage.settings import Settings


class ArbitrageEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _fee(self, exchange_name: str) -> float:
        return self.settings.exchange_fee_rate.get(
            exchange_name,
            self.settings.default_taker_fee_rate,
        )

    def scan_symbol(
        self,
        quotes: list[TickerQuote],
        *,
        apply_thresholds: bool = True,
    ) -> list[ArbitrageOpportunity]:
        if len(quotes) < 2:
            return []

        opportunities: list[ArbitrageOpportunity] = []

        for buy_quote, sell_quote in permutations(quotes, 2):
            if buy_quote.exchange == sell_quote.exchange:
                continue

            buy_fee = self._fee(buy_quote.exchange)
            sell_fee = self._fee(sell_quote.exchange)
            slippage_multiplier = self.settings.slippage_bps / 10_000

            # Effective prices after taker fee and slippage buffer on both legs.
            effective_buy = buy_quote.ask * (1 + buy_fee) * (1 + slippage_multiplier)
            effective_sell = sell_quote.bid * (1 - sell_fee) * (1 - slippage_multiplier)

            gross_spread_pct = ((sell_quote.bid - buy_quote.ask) / buy_quote.ask) * 100
            net_spread_pct = ((effective_sell - effective_buy) / effective_buy) * 100
            estimated_profit_per_unit = effective_sell - effective_buy

            estimated_base_size = self.settings.trade_size_quote / effective_buy
            estimated_profit_quote = estimated_profit_per_unit * estimated_base_size

            if apply_thresholds:
                if net_spread_pct < self.settings.min_net_spread_pct:
                    continue
                if estimated_profit_quote < self.settings.min_net_profit_quote:
                    continue

            opportunities.append(
                ArbitrageOpportunity(
                    symbol=buy_quote.symbol,
                    buy_exchange=buy_quote.exchange,
                    sell_exchange=sell_quote.exchange,
                    buy_price=buy_quote.ask,
                    sell_price=sell_quote.bid,
                    effective_buy_price=effective_buy,
                    effective_sell_price=effective_sell,
                    gross_spread_pct=gross_spread_pct,
                    net_spread_pct=net_spread_pct,
                    trade_size_quote=self.settings.trade_size_quote,
                    estimated_base_size=estimated_base_size,
                    estimated_profit_per_unit=estimated_profit_per_unit,
                    estimated_profit_quote=estimated_profit_quote,
                )
            )

        opportunities.sort(key=lambda item: item.net_spread_pct, reverse=True)
        return opportunities
