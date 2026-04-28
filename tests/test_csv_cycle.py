import csv
from pathlib import Path

from interexchange_arbitrage.csv_cycle import rotate_csv_if_needed


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def _read_csv(path: Path) -> list[list[str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def test_rotate_csv_if_needed_keeps_header_and_rolls_backups(tmp_path) -> None:
    path = tmp_path / "signals.csv"
    headers = ["run_at_utc", "symbol"]
    rows = [["t1", "BTC/USDT"], ["t2", "ETH/USDT"]]
    _write_csv(path, headers, rows)

    rotate_csv_if_needed(path, headers, max_rows=2, max_backups=2)

    rotated_1 = tmp_path / "signals.1.csv"
    assert rotated_1.exists()
    assert _read_csv(rotated_1)[1:] == rows

    current = _read_csv(path)
    assert current == [headers]


def test_rotate_csv_if_needed_no_backup_truncates_current(tmp_path) -> None:
    path = tmp_path / "paper.csv"
    headers = ["run_at_utc", "pnl"]
    rows = [["t1", "1.2"]]
    _write_csv(path, headers, rows)

    rotate_csv_if_needed(path, headers, max_rows=1, max_backups=0)

    assert path.exists()
    assert _read_csv(path) == [headers]
    assert not (tmp_path / "paper.1.csv").exists()
