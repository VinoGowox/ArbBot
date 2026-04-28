from __future__ import annotations

from datetime import datetime, timezone

import httpx

from interexchange_arbitrage.exchanges.base import ExchangeClient
from interexchange_arbitrage.models import TickerQuote


class OkxClient(ExchangeClient):
    name = "okx"
    _base_url = "https://www.okx.com"

    @staticmethod
    def _to_exchange_symbol(symbol: str) -> str:
        return symbol.replace("/", "-").upper()

    def fetch_ticker(self, symbol: str) -> TickerQuote:
        exchange_symbol = self._to_exchange_symbol(symbol)
        url = f"{self._base_url}/api/v5/market/ticker"

        with httpx.Client(timeout=10.0, headers={"User-Agent": "ArbBot/1.0"}) as client:
            response = client.get(url, params={"instId": exchange_symbol})
            response.raise_for_status()
            payload = response.json()

        data = payload.get("data", [])
        if not data:
            raise ValueError(f"No ticker data returned by OKX for {symbol}")

        ticker = data[0]
        return TickerQuote(
            exchange=self.name,
            symbol=symbol,
            bid=float(ticker["bidPx"]),
            ask=float(ticker["askPx"]),
            timestamp=datetime.now(timezone.utc),
        )
