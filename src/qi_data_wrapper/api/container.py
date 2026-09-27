from dataclasses import dataclass

from qi_data_wrapper.application.resolver import DataResolver
from qi_data_wrapper.core.config import Settings
from qi_data_wrapper.infrastructure.catalog import FileCatalog
from qi_data_wrapper.infrastructure.parquet_store import ParquetStore


@dataclass(frozen=True)
class Container:
    catalog: FileCatalog
    store: ParquetStore
    resolver: DataResolver


def build_container(settings: Settings) -> Container:
    catalog = FileCatalog(settings.storage_path / "catalog" / "datasets.json")
    store = ParquetStore(settings.storage_path)
    return Container(catalog=catalog, store=store, resolver=DataResolver(catalog))
