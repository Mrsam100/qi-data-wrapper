from qi_data_wrapper.domain.models import (
    DatasetCatalog,
    DatasetStatus,
    ResolveDataRequest,
    ResolveDataResponse,
)


class DataResolver:
    """Resolve only already-imported, validated local data."""

    def __init__(self, catalog: DatasetCatalog) -> None:
        self._catalog = catalog

    def resolve(self, request: ResolveDataRequest) -> ResolveDataResponse:
        dataset = self._catalog.find_covering(
            request.instrument_id, request.timeframe, request.start, request.end
        )
        if dataset is not None:
            return ResolveDataResponse(status=DatasetStatus.READY, dataset=dataset)
        return ResolveDataResponse(
            status=DatasetStatus.FAILED,
            missing_start=request.start,
            missing_end=request.end,
            error_code="INSUFFICIENT_LOCAL_HISTORY",
        )
