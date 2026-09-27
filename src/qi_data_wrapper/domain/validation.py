from collections.abc import Sequence
from datetime import datetime, timedelta
from itertools import pairwise

from qi_data_wrapper.domain.models import Candle


class CandleValidationError(ValueError):
    """Candle data violates an invariant required before publication."""


def validate_candles(candles: Sequence[Candle]) -> None:
    if not candles:
        raise CandleValidationError("provider returned no candles")
    timestamps = [candle.timestamp for candle in candles]
    if len(set(timestamps)) != len(timestamps):
        raise CandleValidationError("duplicate candle timestamps")
    if timestamps != sorted(timestamps):
        raise CandleValidationError("candle timestamps are not monotonic")


def expected_interval(timeframe: str) -> timedelta:
    intervals = {
        "1m": timedelta(minutes=1), "5m": timedelta(minutes=5), "15m": timedelta(minutes=15),
        "30m": timedelta(minutes=30), "1h": timedelta(hours=1), "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
    }
    return intervals[timeframe]


def detect_coverage_gaps(
    candles: Sequence[Candle], start: datetime, end: datetime, interval: timedelta
) -> list[tuple[datetime, datetime]]:
    """Return missing interior and edge ranges for timeframe-aligned UTC requests."""
    if not candles:
        return [(start, end)]
    gaps: list[tuple[datetime, datetime]] = []
    if candles[0].timestamp > start:
        gaps.append((start, candles[0].timestamp))
    for previous, current in pairwise(candles):
        if current.timestamp - previous.timestamp > interval:
            gaps.append((previous.timestamp + interval, current.timestamp))
    if candles[-1].timestamp + interval < end:
        gaps.append((candles[-1].timestamp + interval, end))
    return gaps


def repair_coverage_gaps(candles: Sequence[Candle], interval: timedelta) -> tuple[list[Candle], int]:
    """Forward-fill interior missing candle gaps by zeroing volume and copying close price."""
    from decimal import Decimal

    if not candles:
        return list(candles), 0

    repaired: list[Candle] = [candles[0]]
    repaired_count = 0
    for current in candles[1:]:
        previous = repaired[-1]
        missing_timestamp = previous.timestamp + interval
        while missing_timestamp < current.timestamp:
            repaired_count += 1
            repaired.append(
                Candle(
                    instrument_id=previous.instrument_id,
                    timestamp=missing_timestamp,
                    timeframe=previous.timeframe,
                    open=previous.close,
                    high=previous.close,
                    low=previous.close,
                    close=previous.close,
                    volume=Decimal(0),
                    source=previous.source,
                    ingestion_timestamp=previous.ingestion_timestamp,
                )
            )
            missing_timestamp += interval
        repaired.append(current)
    return repaired, repaired_count
