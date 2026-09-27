from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from qi_data_wrapper.api.container import Container
from qi_data_wrapper.application.local_import import ALL_INSTRUMENTS
from qi_data_wrapper.domain.models import (
    Candle,
    DatasetVersion,
    Instrument,
    ResolveDataRequest,
    ResolveDataResponse,
)

def build_router(container: Container) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "qi-data-wrapper"}

    @router.get("/v1/instruments", response_model=list[Instrument])
    async def list_instruments() -> list[Instrument]:
        return ALL_INSTRUMENTS

    @router.post("/v1/data/resolve", response_model=ResolveDataResponse, status_code=status.HTTP_202_ACCEPTED)
    async def resolve_data(request: ResolveDataRequest) -> ResolveDataResponse:
        return container.resolver.resolve(request)

    @router.get("/v1/datasets/{dataset_version_id}/metadata", response_model=DatasetVersion)
    async def dataset_metadata(dataset_version_id: str) -> DatasetVersion:
        dataset = next((item for item in container.catalog.all() if str(item.dataset_version_id) == dataset_version_id), None)
        if dataset is None:
            raise HTTPException(status_code=404, detail={"code": "DATASET_NOT_FOUND"})
        return dataset

    @router.get("/v1/datasets/{dataset_version_id}/candles", response_model=list[Candle])
    async def dataset_candles(
        dataset_version_id: str,
        start: Annotated[datetime | None, Query()] = None,
        end: Annotated[datetime | None, Query()] = None,
    ) -> list[Candle]:
        if (start is None) != (end is None) or (start is not None and start >= end):
            raise HTTPException(status_code=422, detail={"code": "INVALID_CANDLE_RANGE"})
        dataset = next((item for item in container.catalog.all() if str(item.dataset_version_id) == dataset_version_id), None)
        if dataset is None or dataset.storage_uri is None:
            raise HTTPException(status_code=404, detail={"code": "DATASET_NOT_FOUND"})
        candles = container.store.read(dataset.storage_uri)
        return candles if start is None else [candle for candle in candles if start <= candle.timestamp < end]

    return router
