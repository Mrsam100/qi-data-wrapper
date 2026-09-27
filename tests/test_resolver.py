from datetime import UTC, datetime
from uuid import uuid4

from qi_data_wrapper.application.resolver import DataResolver
from qi_data_wrapper.domain.models import (
    DatasetStatus,
    DatasetVersion,
    ResolveDataRequest,
    ValidationState,
)
from qi_data_wrapper.infrastructure.catalog import FileCatalog


def request() -> ResolveDataRequest:
    return ResolveDataRequest(
        instrument_id="CRYPTO_KRAKEN_BTC_USD_SPOT",
        timeframe="1h",
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2025, 1, 2, tzinfo=UTC),
    )


def test_fails_when_no_local_validated_dataset_exists(tmp_path) -> None:
    response = DataResolver(FileCatalog(tmp_path / "datasets.json")).resolve(request())
    assert response.status == DatasetStatus.FAILED
    assert response.error_code == "INSUFFICIENT_LOCAL_HISTORY"


def test_returns_ready_when_validated_dataset_covers_request(tmp_path) -> None:
    catalog = FileCatalog(tmp_path / "datasets.json")
    catalog.add(
        DatasetVersion(
            dataset_version_id=uuid4(),
            instrument_id="CRYPTO_KRAKEN_BTC_USD_SPOT",
            timeframe="1h",
            start=datetime(2024, 12, 1, tzinfo=UTC),
            end=datetime(2025, 2, 1, tzinfo=UTC),
            source="bitstamp",
            checksum="a" * 64,
            validation_state=ValidationState.PASSED,
            quality_score=99.0,
            row_count=100,
        )
    )
    response = DataResolver(catalog).resolve(request())
    assert response.status == DatasetStatus.READY
    assert response.dataset is not None
