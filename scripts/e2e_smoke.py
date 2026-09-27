"""Local-only E2E: user CSV -> validation -> Parquet -> local resolver -> stored candles."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from qi_data_wrapper.api.container import build_container
from qi_data_wrapper.application.local_import import LocalCsvImporter
from qi_data_wrapper.core.config import Settings
from qi_data_wrapper.domain.models import DatasetStatus, ResolveDataRequest
from qi_data_wrapper.infrastructure.source_archive import SourceArchive


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local-only CSV import and resolve smoke test.")
    parser.add_argument("source_file", type=Path)
    args = parser.parse_args()

    with TemporaryDirectory(prefix="qi-data-e2e-") as temporary_directory:
        settings = Settings(storage_path=Path(temporary_directory))
        container = build_container(settings)
        dataset = LocalCsvImporter(
            catalog=container.catalog,
            store=container.store,
            archive=SourceArchive(settings.storage_path),
        ).import_bitstamp_btcusd_1h(args.source_file)
        stored_candles = container.store.read(dataset.storage_uri or "")
        resolved = container.resolver.resolve(
            ResolveDataRequest(
                instrument_id=dataset.instrument_id,
                timeframe=dataset.timeframe,
                start=dataset.start,
                end=dataset.end,
            )
        )

    assert dataset.validation_state.value == "PASSED"
    assert dataset.row_count == len(stored_candles) > 0
    assert resolved.status is DatasetStatus.READY
    assert resolved.dataset is not None
    print(f"E2E PASS: dataset={dataset.dataset_version_id} candles={dataset.row_count}")


if __name__ == "__main__":
    main()
