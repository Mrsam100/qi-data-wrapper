import hashlib
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

import pyarrow as pa
import pyarrow.parquet as pq

from qi_data_wrapper.domain.models import Candle


class ParquetStore:
    """Read and write canonical candles in deterministic, month-partitioned Parquet files."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def write(self, dataset_id: UUID, candles: Sequence[Candle]) -> tuple[str, str]:
        if not candles:
            raise ValueError("cannot store an empty dataset")
        grouped: dict[tuple[int, int], list[Candle]] = defaultdict(list)
        for candle in candles:
            grouped[(candle.timestamp.year, candle.timestamp.month)].append(candle)
        paths: list[str] = []
        for (year, month), rows in grouped.items():
            first = rows[0]
            path = Path("normalized") / first.instrument_id / first.timeframe / str(year) / f"{month:02d}" / f"{dataset_id}.parquet"
            destination = self._root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pylist([self._row(candle) for candle in rows]), destination, compression="zstd")
            paths.append(path.as_posix())
        checksum = hashlib.sha256(json.dumps([self._row(candle) for candle in candles], sort_keys=True).encode()).hexdigest()
        return ";".join(paths), checksum

    def read(self, storage_uri: str) -> list[Candle]:
        candles = [
            Candle.model_validate(row)
            for relative_path in storage_uri.split(";")
            for row in pq.read_table(self._root / relative_path).to_pylist()
        ]
        return sorted(candles, key=lambda candle: candle.timestamp)

    @staticmethod
    def _row(candle: Candle) -> dict[str, Any]:
        return candle.model_dump(mode="json")
