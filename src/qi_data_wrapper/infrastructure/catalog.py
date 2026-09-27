import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from qi_data_wrapper.domain.models import DatasetVersion, ValidationState


class FileCatalog:
    """Durable local catalog for development; replace with PostgreSQL in production."""

    def __init__(self, manifest_path: Path) -> None:
        self._manifest_path = manifest_path
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._datasets = self._load()

    def add(self, dataset: DatasetVersion) -> None:
        self._datasets.append(dataset)
        temporary_path = self._manifest_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps([item.model_dump(mode="json") for item in self._datasets], indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self._manifest_path)

    def all(self) -> Iterable[DatasetVersion]:
        return tuple(self._datasets)

    def find_covering(
        self, instrument_id: str, timeframe: str, start: datetime, end: datetime
    ) -> DatasetVersion | None:
        return next(
            (
                dataset for dataset in self._datasets
                if dataset.instrument_id == instrument_id and dataset.timeframe == timeframe
                and dataset.start <= start and dataset.end >= end
                and dataset.validation_state is ValidationState.PASSED
            ),
            None,
        )

    def _load(self) -> list[DatasetVersion]:
        if not self._manifest_path.exists():
            return []
        return [DatasetVersion.model_validate(item) for item in json.loads(self._manifest_path.read_text(encoding="utf-8"))]
