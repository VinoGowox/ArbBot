# Inter-Exchange Spot Arbitrage - Week 1

Implementasi Week 1 untuk scanner peluang arbitrase spot antar exchange dengan fokus:

- Pengambilan top-of-book (`bid`/`ask`) via public API
- Standardisasi simbol (`BTC/USDT` style)
- Kalkulasi spread kotor dan spread bersih setelah taker fee
- Filter minimum net spread
- Output peluang dalam bentuk tabel CLI

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

## Jalankan Test

```powershell
$env:PYTHONPATH = "src"
python -m pytest
```

## Catatan Batasan Week 1

- Belum ada eksekusi order (hanya scanner)
- Belum ada transfer inventory antar exchange
- Belum ada depth/slippage model
- Belum ada scheduler daemon / alerting otomatis
