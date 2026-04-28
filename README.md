# Inter-Exchange Spot Arbitrage - Week 1-3

Implementasi Week 1-3 untuk scanner peluang arbitrase spot antar exchange dengan fokus:

- Pengambilan top-of-book (`bid`/`ask`) via public API
- Standardisasi simbol (`BTC/USDT` style)
- Kalkulasi spread kotor dan spread bersih setelah taker fee + slippage buffer
- Estimasi profit berbasis notional size (`TRADE_SIZE_QUOTE`)
- Filter minimum net spread dan minimum net profit quote
- Output peluang dalam bentuk tabel CLI
- Snapshot data peluang ke CSV
- Alert Telegram opsional untuk sinyal teratas
- Paper trading engine: portfolio state per exchange, simulated execution, dan PnL ledger

## Struktur

- `src/interexchange_arbitrage/exchanges/` adapter exchange
- `src/interexchange_arbitrage/engine.py` kalkulasi opportunity
- `src/interexchange_arbitrage/cli.py` orchestrator scanner
- `main.py` entrypoint
- `tests/test_engine.py` unit test kalkulasi inti

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
```

## Konfigurasi

Salin `.env.example` ke `.env`, lalu sesuaikan:

- `SYMBOLS` contoh: `BTC/USDT,ETH/USDT,SOL/USDT`
- `ENABLED_EXCHANGES` contoh: `okx,kucoin` atau `binance,bybit`
- `MIN_NET_SPREAD_PCT` contoh: `0.2`
- `MIN_NET_PROFIT_QUOTE` contoh: `1.0`
- `TRADE_SIZE_QUOTE` contoh: `1000`
- `SLIPPAGE_BPS` contoh: `2`
- `SNAPSHOT_CSV_PATH` contoh: `data/arbitrage_opportunities.csv`
- `SNAPSHOT_CSV_MAX_ROWS` contoh: `20000` (auto rotate saat baris data mencapai limit)
- `SNAPSHOT_CSV_MAX_BACKUPS` contoh: `5` (jumlah backup file snapshot: `.1`, `.2`, dst)
- `TELEGRAM_ENABLED` `true/false`
- `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID` jika alert aktif
- `PAPER_TRADING_ENABLED` `true/false`
- `PAPER_STATE_PATH` contoh: `data/paper_portfolio.json`
- `PAPER_TRADES_CSV_PATH` contoh: `data/paper_trades.csv`
- `PAPER_INITIAL_QUOTE_BALANCE` contoh: `10000`
- `PAPER_INITIAL_BASE_BALANCE` contoh: `0.1`
- `PAPER_MAX_QUOTE_PER_TRADE` contoh: `1000`
- `PAPER_COOLDOWN_SECONDS` contoh: `60`
- `DEFAULT_TAKER_FEE_RATE` default: `0.001`
- Fee per exchange opsional: `BINANCE_SPOT_FEE`, `BYBIT_SPOT_FEE`, `OKX_SPOT_FEE`, `KUCOIN_SPOT_FEE`

## Catatan Akses API Exchange

Beberapa VPS region/IP bisa dibatasi oleh exchange tertentu (mis. HTTP 451/403). Jika itu terjadi,
ubah `ENABLED_EXCHANGES` ke kombinasi exchange yang dapat diakses dari VPS Anda, misalnya:

```env
ENABLED_EXCHANGES=okx,kucoin
```

## Jalankan Scanner

```powershell
python main.py
```

## Jalankan Web Dashboard

Dashboard menyediakan:

- Edit parameter scanner via browser (menulis ke `.env`)
- Monitoring snapshot sinyal dari CSV
- Trigger one-off scan untuk pengecekan cepat
- Tampilan status service systemd (jika tersedia)
- Login session berbasis username/password

Set environment berikut di VPS untuk login dashboard:

- `DASHBOARD_USERNAME`
- `DASHBOARD_PASSWORD`
- `DASHBOARD_SESSION_SECRET`

```powershell
$env:PYTHONPATH = "src"
python dashboard.py
```

Lalu buka `http://localhost:8000`.

## Jalankan Test

```powershell
$env:PYTHONPATH = "src"
python -m pytest
```

## Catatan Batasan Saat Ini

- Belum ada eksekusi order (hanya scanner)
- Belum ada transfer inventory antar exchange
- Slippage masih model sederhana berbasis buffer bps (belum orderbook depth-aware)
