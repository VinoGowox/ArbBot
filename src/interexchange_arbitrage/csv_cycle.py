from __future__ import annotations

import csv
from pathlib import Path


def _rotated_path(path: Path, index: int) -> Path:
    return path.with_name(f"{path.stem}.{index}{path.suffix}")


def _count_data_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        row_count = sum(1 for _ in csv.reader(csv_file))

    return max(row_count - 1, 0)


def rotate_csv_if_needed(
    path: Path,
    headers: list[str],
    *,
    max_rows: int,
    max_backups: int,
) -> None:
    if max_rows <= 0:
        return

    if _count_data_rows(path) < max_rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    if max_backups <= 0:
        path.unlink(missing_ok=True)
    else:
        oldest = _rotated_path(path, max_backups)
        oldest.unlink(missing_ok=True)

        for index in range(max_backups - 1, 0, -1):
            source = _rotated_path(path, index)
            target = _rotated_path(path, index + 1)
            if source.exists():
                source.rename(target)

        if path.exists():
            path.rename(_rotated_path(path, 1))

    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(headers)
