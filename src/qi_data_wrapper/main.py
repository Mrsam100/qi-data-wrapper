from fastapi import FastAPI

from qi_data_wrapper.api.container import build_container
from qi_data_wrapper.api.routes import build_router
from qi_data_wrapper.core.config import settings

app = FastAPI(
    title="QI Data Wrapper",
    version="0.1.0",
    description="Provider-independent, validated market-data access for QI services.",
)

app.include_router(build_router(build_container(settings)))
