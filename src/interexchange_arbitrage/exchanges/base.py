from __future__ import annotations

from abc import ABC, abstractmethod

from interexchange_arbitrage.models import TickerQuote


class ExchangeClient(ABC):
    name: str

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> TickerQuote:
        """Return best bid and ask for a unified symbol (e.g. BTC/USDT)."""
