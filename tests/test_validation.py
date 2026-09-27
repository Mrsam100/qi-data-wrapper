from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qi_data_wrapper.domain.models import Candle
from qi_data_wrapper.domain.validation import (
    CandleValidationError,
    detect_coverage_gaps,
    validate_candles,
)


def candle(at: datetime) -> Candle:
    return Candle(
        instrument_id="CRYPTO_KRAKEN_BTC_USD_SPOT",
        timestamp=at,
        timeframe="1h",
        open=Decimal(100),
        high=Decimal(110),
        low=Decimal(90),
        close=Decimal(105),
        volume=Decimal(4),
        source="bitstamp",
        ingestion_timestamp=at,
    )


def test_detects_gap() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    gaps = detect_coverage_gaps(
        [candle(start), candle(start + timedelta(hours=2))], start, start + timedelta(hours=3), timedelta(hours=1)
    )
    assert len(gaps) == 1


def test_rejects_duplicate_timestamps() -> None:
    start = datetime(2025, 1, 1, tzinfo=UTC)
    with pytest.raises(CandleValidationError, match="duplicate"):
        validate_candles([candle(start), candle(start)])
