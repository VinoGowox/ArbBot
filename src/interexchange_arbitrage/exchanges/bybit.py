from __future__ import annotations

from datetime import datetime, timezone

import httpx

from interexchange_arbitrage.exchanges.base import ExchangeClient
from interexchange_arbitrage.models import TickerQuote


class BybitClient(ExchangeClient):
    name = "bybit"
    _base_url = "https://api.bybit.com"

    @staticmethod
    def _to_exchange_symbol(symbol: str) -> str:
        return symbol.replace("/", "").upper()

    def fetch_ticker(self, symbol: str) -> TickerQuote:
        exchange_symbol = self._to_exchange_symbol(symbol)
        url = f"{self._base_url}/v5/market/tickers"

        with httpx.Client(timeout=10.0, headers={"User-Agent": "ArbBot/1.0"}) as client:
            response = client.get(
                url,
                params={"category": "spot", "symbol": exchange_symbol},
            )
            response.raise_for_status()
            payload = response.json()

        result = payload.get("result", {})
        quotes = result.get("list", [])
        if not quotes:
            raise ValueError(f"No ticker data returned by Bybit for {symbol}")

        quote = quotes[0]
        return TickerQuote(
            exchange=self.name,
            symbol=symbol,
            bid=float(quote["bid1Price"]),
            ask=float(quote["ask1Price"]),
            timestamp=datetime.now(timezone.utc),
        )
