"""Import all historical CSV datasets present in Data_source/ into the local QI data store."""

import argparse
from pathlib import Path

from qi_data_wrapper.api.container import build_container
from qi_data_wrapper.application.local_import import LocalCsvImporter
from qi_data_wrapper.core.config import Settings
from qi_data_wrapper.infrastructure.source_archive import SourceArchive


def main() -> None:
    parser = argparse.ArgumentParser(description="Import all CSV datasets from a folder into QI Data Wrapper.")
    parser.add_argument("source_dir", type=Path, nargs="?", default=Path("Data_source"))
    args = parser.parse_args()

    source_dir = args.source_dir
    if not source_dir.exists() or not source_dir.is_dir():
        print(f"Directory not found: {source_dir}")
        return

    csv_files = sorted(source_dir.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {source_dir}")
        return

    container = build_container(Settings())
    importer = LocalCsvImporter(
        catalog=container.catalog,
        store=container.store,
        archive=SourceArchive(Settings().storage_path),
    )

    print(f"Found {len(csv_files)} CSV files in {source_dir}. Beginning import...")
    for csv_file in csv_files:
        try:
            dataset = importer.import_bitstamp_csv(csv_file)
            print(
                f"IMPORT SUCCESS: [{dataset.instrument_id}] dataset={dataset.dataset_version_id} "
                f"rows={dataset.row_count} range={dataset.start.isoformat()}..{dataset.end.isoformat()} checksum={dataset.checksum[:16]}..."
            )
        except Exception as err:
            print(f"IMPORT SKIPPED ({csv_file.name}): {err}")


if __name__ == "__main__":
    main()
