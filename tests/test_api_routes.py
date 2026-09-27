from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qi_data_wrapper.api.container import Container
from qi_data_wrapper.api.routes import build_router
from qi_data_wrapper.domain.models import Candle, DatasetVersion, ValidationState


class _Catalog:
    def __init__(self, dataset: DatasetVersion) -> None:
        self._dataset = dataset

    def all(self) -> list[DatasetVersion]:
        return [self._dataset]


class _Store:
    def __init__(self, candles: list[Candle]) -> None:
        self._candles = candles

    def read(self, storage_uri: str) -> list[Candle]:
        assert storage_uri == "normalized/test.parquet"
        return self._candles


def _candle(timestamp: datetime) -> Candle:
    return Candle(
        instrument_id="CRYPTO_BITSTAMP_BTC_USD_SPOT",
        timestamp=timestamp,
        timeframe="1h",
        open=100,
        high=101,
        low=99,
        close=100,
        volume=1,
        source="bitstamp",
        ingestion_timestamp=timestamp,
    )


def test_candle_range_query_returns_only_the_requested_half_open_interval() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    dataset = DatasetVersion(
        dataset_version_id=uuid4(),
        instrument_id="CRYPTO_BITSTAMP_BTC_USD_SPOT",
        timeframe="1h",
        start=start,
        end=start + timedelta(hours=3),
        source="bitstamp",
        checksum="a" * 64,
        validation_state=ValidationState.PASSED,
        quality_score=100,
        row_count=3,
        storage_uri="normalized/test.parquet",
    )
    app = FastAPI()
    candles = [_candle(start + timedelta(hours=offset)) for offset in range(3)]
    container = Container(
        catalog=_Catalog(dataset),  # type: ignore[arg-type]
        store=_Store(candles),  # type: ignore[arg-type]
        resolver=None,  # type: ignore[arg-type]
    )
    app.include_router(build_router(container))

    response = TestClient(app).get(
        f"/v1/datasets/{dataset.dataset_version_id}/candles",
        params={"start": start.isoformat(), "end": (start + timedelta(hours=2)).isoformat()},
    )

    assert response.status_code == 200
    assert [item["timestamp"] for item in response.json()] == [
        "2020-01-01T00:00:00Z",
        "2020-01-01T01:00:00Z",
    ]
