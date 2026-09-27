from collections.abc import Sequence

from qi_data_wrapper.domain.models import Candle, Instrument


def normalize_candles(
    candles: Sequence[Candle], instrument: Instrument, timeframe: str, source: str
) -> list[Candle]:
    """Enforce the QI canonical identity and deterministic chronological ordering."""
    normalized = [
        candle.model_copy(
            update={
                "instrument_id": instrument.instrument_id,
                "timeframe": timeframe,
                "source": source,
            }
        )
        for candle in candles
    ]
    return sorted(normalized, key=lambda candle: candle.timestamp)
