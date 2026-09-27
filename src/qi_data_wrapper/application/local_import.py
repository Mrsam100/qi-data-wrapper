import csv
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from qi_data_wrapper.domain.models import (
    Candle,
    DatasetCatalog,
    DatasetVersion,
    Instrument,
    ValidationState,
)
from qi_data_wrapper.domain.normalization import normalize_candles
from qi_data_wrapper.domain.quality import calculate_quality_score
from qi_data_wrapper.domain.validation import (
    CandleValidationError,
    detect_coverage_gaps,
    expected_interval,
    repair_coverage_gaps,
    validate_candles,
)
from qi_data_wrapper.infrastructure.parquet_store import ParquetStore
from qi_data_wrapper.infrastructure.source_archive import SourceArchive

BITSTAMP_BTC_USD_1H = Instrument(
    instrument_id="CRYPTO_BITSTAMP_BTC_USD_SPOT",
    symbol="BTC/USD",
    base_asset="BTC",
    quote_asset="USD",
    exchange="bitstamp",
)

BITSTAMP_ETH_USD_1H = Instrument(
    instrument_id="CRYPTO_BITSTAMP_ETH_USD_SPOT",
    symbol="ETH/USD",
    base_asset="ETH",
    quote_asset="USD",
    exchange="bitstamp",
)

BITSTAMP_XRP_BTC_1H = Instrument(
    instrument_id="CRYPTO_BITSTAMP_XRP_BTC_SPOT",
    symbol="XRP/BTC",
    base_asset="XRP",
    quote_asset="BTC",
    exchange="bitstamp",
)

INSTRUMENT_REGISTRY_BY_SYMBOL: dict[str, Instrument] = {
    "BTC/USD": BITSTAMP_BTC_USD_1H,
    "ETH/USD": BITSTAMP_ETH_USD_1H,
    "XRP/BTC": BITSTAMP_XRP_BTC_1H,
}

ALL_INSTRUMENTS: list[Instrument] = [
    BITSTAMP_BTC_USD_1H,
    BITSTAMP_ETH_USD_1H,
    BITSTAMP_XRP_BTC_1H,
]


class LocalImportError(RuntimeError):
    """A supplied historical file cannot safely become a published local dataset."""


class LocalCsvImporter:
    """One-time/offline ingestion of known CSV layouts into QI's canonical local store."""

    def __init__(self, catalog: DatasetCatalog, store: ParquetStore, archive: SourceArchive) -> None:
        self._catalog = catalog
        self._store = store
        self._archive = archive

    def import_bitstamp_csv(self, source_file: Path) -> DatasetVersion:
        instrument, candles = self._read_cryptodatadownload_csv(source_file)
        candles = normalize_candles(candles, instrument, "1h", "bitstamp")
        try:
            validate_candles(candles)
        except CandleValidationError as error:
            raise LocalImportError(f"CSV validation failed: {error}") from error

        interval = expected_interval("1h")
        candles, repaired_count = repair_coverage_gaps(candles, interval)
        start = candles[0].timestamp
        end = candles[-1].timestamp + interval
        gaps = detect_coverage_gaps(candles, start, end, interval)
        if gaps:
            raise LocalImportError(f"CSV contains {len(gaps)} missing candle range(s); refusing to publish")

        dataset_id = uuid4()
        raw_storage_uri, raw_checksum = self._archive.archive(dataset_id, source_file)
        storage_uri, checksum = self._store.write(dataset_id, candles)
        dataset = DatasetVersion(
            dataset_version_id=dataset_id,
            instrument_id=instrument.instrument_id,
            timeframe="1h",
            start=start,
            end=end,
            source="bitstamp",
            checksum=checksum,
            raw_storage_uri=raw_storage_uri,
            raw_checksum=raw_checksum,
            validation_state=ValidationState.PASSED,
            quality_score=calculate_quality_score(repaired_candle_count=repaired_count, provider_count=1),
            row_count=len(candles),
            storage_uri=storage_uri,
            repaired_candle_count=repaired_count,
        )
        self._catalog.add(dataset)
        return dataset

    def import_bitstamp_btcusd_1h(self, source_file: Path) -> DatasetVersion:
        return self.import_bitstamp_csv(source_file)

    @staticmethod
    def _read_cryptodatadownload_csv(source_file: Path) -> tuple[Instrument, list[Candle]]:
        try:
            lines = source_file.read_text(encoding="utf-8-sig").splitlines()
        except UnicodeDecodeError as error:
            raise LocalImportError("CSV must be UTF-8 encoded") from error
        if lines and lines[0].startswith("datetime_utc,"):
            return BITSTAMP_BTC_USD_1H, LocalCsvImporter._read_datetime_utc_csv(lines)

        header_index = next((index for index, line in enumerate(lines) if line.startswith("unix,")), None)
        if header_index is None:
            raise LocalImportError("unsupported CSV header; expected unix/date or datetime_utc layout")

        ingested_at = datetime.now(UTC)
        candles: list[Candle] = []
        reader = csv.DictReader(lines[header_index:])
        instrument: Instrument | None = None
        volume_key: str | None = None

        for line_number, row in enumerate(reader, start=header_index + 2):
            try:
                if instrument is None:
                    symbol = row.get("symbol")
                    if not symbol or symbol not in INSTRUMENT_REGISTRY_BY_SYMBOL:
                        raise LocalImportError(f"line {line_number}: unsupported symbol '{symbol}'")
                    instrument = INSTRUMENT_REGISTRY_BY_SYMBOL[symbol]
                    possible_vol_keys = [f"Volume {instrument.base_asset}", "volume", "Volume"]
                    volume_key = next((k for k in possible_vol_keys if k in row), None)
                    if volume_key is None:
                        volume_key = next((k for k in row if k.lower().startswith("volume")), None)
                    if volume_key is None:
                        raise LocalImportError(f"line {line_number}: volume column not found")

                timestamp = datetime.fromtimestamp(int(row["unix"]), tz=UTC)
                candles.append(
                    Candle(
                        instrument_id=instrument.instrument_id,
                        timestamp=timestamp,
                        timeframe="1h",
                        open=Decimal(row["open"]),
                        high=Decimal(row["high"]),
                        low=Decimal(row["low"]),
                        close=Decimal(row["close"]),
                        volume=Decimal(row[volume_key]),
                        source="bitstamp",
                        ingestion_timestamp=ingested_at,
                    )
                )
            except (KeyError, ValueError, InvalidOperation) as error:
                raise LocalImportError(f"line {line_number}: malformed candle") from error

        if not candles or instrument is None:
            raise LocalImportError("CSV contains no candle rows")
        return instrument, candles

    @staticmethod
    def _read_datetime_utc_csv(lines: list[str]) -> list[Candle]:
        """Read standard chronological OHLCV exports with datetime_utc/open/high/low/close/volume fields."""
        ingested_at = datetime.now(UTC)
        candles: list[Candle] = []
        for line_number, row in enumerate(csv.DictReader(lines), start=2):
            try:
                timestamp = datetime.fromisoformat(row["datetime_utc"])
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    raise LocalImportError(f"line {line_number}: datetime_utc is not timezone-aware")
                candles.append(
                    Candle(
                        instrument_id=BITSTAMP_BTC_USD_1H.instrument_id,
                        timestamp=timestamp.astimezone(UTC),
                        timeframe="1h",
                        open=Decimal(row["open"]),
                        high=Decimal(row["high"]),
                        low=Decimal(row["low"]),
                        close=Decimal(row["close"]),
                        volume=Decimal(row["volume"]),
                        source="bitstamp",
                        ingestion_timestamp=ingested_at,
                    )
                )
            except (KeyError, ValueError, InvalidOperation) as error:
                raise LocalImportError(f"line {line_number}: malformed candle") from error
        if not candles:
            raise LocalImportError("CSV contains no candle rows")
        return candles
