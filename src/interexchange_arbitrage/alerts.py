from __future__ import annotations

import httpx

from interexchange_arbitrage.models import ArbitrageOpportunity


def build_alert_message(item: ArbitrageOpportunity) -> str:
    return (
        "Arbitrage signal\n"
        f"Symbol: {item.symbol}\n"
        f"Buy: {item.buy_exchange} @ {item.buy_price:.6f}\n"
        f"Sell: {item.sell_exchange} @ {item.sell_price:.6f}\n"
        f"Net spread: {item.net_spread_pct:.4f}%\n"
        f"Est. profit ({item.trade_size_quote:.2f} quote): {item.estimated_profit_quote:.6f}"
    )


def send_telegram_alert(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token or not chat_id:
        raise ValueError("Telegram bot token and chat ID must be configured")

    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    with httpx.Client(timeout=10.0) as client:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
