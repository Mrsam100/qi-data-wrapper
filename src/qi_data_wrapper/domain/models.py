from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DataMode(StrEnum):
    HISTORICAL = "HISTORICAL"
    LIVE = "LIVE"
    AUTO = "AUTO"


class DatasetStatus(StrEnum):
    READY = "READY"
    FAILED = "FAILED"


class ValidationState(StrEnum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class Instrument(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: str = Field(pattern=r"^[A-Z0-9_:-]{3,80}$")
    symbol: str = Field(pattern=r"^[A-Z0-9/:-]{3,40}$")
    base_asset: str = Field(pattern=r"^[A-Z0-9]{2,15}$")
    quote_asset: str = Field(pattern=r"^[A-Z0-9]{2,15}$")
    exchange: str = Field(pattern=r"^[a-z0-9_-]{2,40}$")
    market_type: str = Field(default="spot", pattern=r"^[a-z_]{2,30}$")


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument_id: str
    timestamp: datetime
    timeframe: str = Field(pattern=r"^(1m|5m|15m|30m|1h|4h|1d)$")
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)
    source: str = Field(pattern=r"^[a-z0-9_-]{2,40}$")
    ingestion_timestamp: datetime

    @field_validator("timestamp", "ingestion_timestamp")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware UTC values")
        return value

    @model_validator(mode="after")
    def validate_ohlc(self) -> "Candle":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be greater than or equal to open, close and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be less than or equal to open, close and high")
        return self


class ResolveDataRequest(BaseModel):
    instrument_id: str = Field(pattern=r"^[A-Z0-9_:-]{3,80}$")
    timeframe: str = Field(pattern=r"^(1m|5m|15m|30m|1h|4h|1d)$")
    start: datetime
    end: datetime
    mode: DataMode = DataMode.AUTO

    @model_validator(mode="after")
    def validate_range(self) -> "ResolveDataRequest":
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware UTC values")
        if self.start >= self.end:
            raise ValueError("start must be earlier than end")
        return self


class DatasetVersion(BaseModel):
    dataset_version_id: UUID
    instrument_id: str
    timeframe: str
    start: datetime
    end: datetime
    source: str
    checksum: str
    validation_state: ValidationState
    quality_score: float = Field(ge=0, le=100)
    row_count: int = Field(ge=0)
    storage_uri: str | None = None
    raw_storage_uri: str | None = None
    raw_checksum: str | None = None
    gap_count: int = Field(default=0, ge=0)
    repaired_candle_count: int = Field(default=0, ge=0)


class DatasetCatalog(Protocol):
    def add(self, dataset: DatasetVersion) -> None: ...

    def all(self) -> Iterable[DatasetVersion]: ...

    def find_covering(
        self, instrument_id: str, timeframe: str, start: datetime, end: datetime
    ) -> DatasetVersion | None: ...


class ResolveDataResponse(BaseModel):
    status: DatasetStatus
    dataset: DatasetVersion | None = None
    missing_start: datetime | None = None
    missing_end: datetime | None = None
    error_code: str | None = None
