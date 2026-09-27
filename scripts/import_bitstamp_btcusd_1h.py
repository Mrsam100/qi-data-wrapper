"""Import the supplied Bitstamp BTC/USD 1-hour CSV into the local QI data store."""

import argparse
from pathlib import Path

from qi_data_wrapper.api.container import build_container
from qi_data_wrapper.application.local_import import LocalCsvImporter
from qi_data_wrapper.core.config import Settings
from qi_data_wrapper.infrastructure.source_archive import SourceArchive


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a local Bitstamp BTC/USD 1-hour CSV.")
    parser.add_argument("source_file", type=Path)
    args = parser.parse_args()

    container = build_container(Settings())
    importer = LocalCsvImporter(
        catalog=container.catalog,
        store=container.store,
        archive=SourceArchive(Settings().storage_path),
    )
    dataset = importer.import_bitstamp_btcusd_1h(args.source_file)
    print(
        f"IMPORT PASS: dataset={dataset.dataset_version_id} rows={dataset.row_count} "
        f"range={dataset.start.isoformat()}..{dataset.end.isoformat()} checksum={dataset.checksum}"
    )


if __name__ == "__main__":
    main()
