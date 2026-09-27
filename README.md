# QI Data Wrapper

**Universal Market Data Acquisition & Historical Data Engine for Quantinfinium / QI (Part C)**

`qi-data-wrapper` is a standalone market-data normalization, quality validation, Parquet storage, and high-performance serving microservice. It serves as the authoritative boundary between raw market datasets and the QI Backtester.

---

## Key Capabilities

- **Multi-Asset Support**: Normalizes and serves crypto spot assets (`BTC/USD`, `ETH/USD`, `XRP/BTC`).
- **Dynamic Data Ingestion**: Flexible Volume column detection (`Volume BTC`, `Volume ETH`, `Volume XRP`, `volume`).
- **Automated Gap Repair & Quality Validation**: `repair_coverage_gaps()` detects interior timestamp gaps in historical candle sequences, forward-fills price data, sets gap volume to `0`, and logs validation provenance.
- **Offline Parquet Partitioning**: Stores datasets in partitioned Apache Parquet format (`data/normalized/{instrument_id}/1h/{year}/{month}/{dataset_id}.parquet`) with SHA-256 raw and normalized checksums.
- **Zero-API Runtime**: Backtests execute strictly against local validated Parquet stores with no runtime broker API dependency.

---

## Architecture & Data Pipeline

```text
User/Source CSV 
   │
   ▼
[local_import.py] ──> Immutable Raw Archive Storage (`data/raw/`)
   │
   ▼
[validation.py]   ──> Candle Integrity Checks (OHLC Bounds, Volume ≥ 0)
   │                  Gap Detection & Repair (`repair_coverage_gaps`)
   ▼
[Parquet Storage] ──> Partitioned Parquet Engine (`data/normalized/`)
   │                  Catalog Registration (`data/catalog/datasets.json`)
   ▼
[FastAPI Engine]  ──> `/v1/data/resolve` & `/v1/datasets/{id}/candles`
   │
   ▼
QI Backtester / qi-mcp
```

---

## Repository Structure

```text
qi-data-wrapper/
├── Data_source/                     # Source CSV drop folder (BTCUSD, ETHUSD, XRPBTC)
├── data/                            # Local storage (Parquet files, catalog JSON)
│   ├── raw/                         # Raw archived source files
│   ├── normalized/                  # Partitioned Parquet datasets
│   └── catalog/                     # Dataset metadata catalog
├── scripts/
│   ├── import_all_datasets.py       # Bulk importer for all datasets
│   ├── import_bitstamp_btcusd_1h.py # Single asset Bitstamp importer
│   └── e2e_smoke.py                 # Isolated container smoke test
├── src/qi_data_wrapper/
│   ├── api/                         # FastAPI routes and dependency container
│   ├── application/                 # Local import, resolver, gap repair workflows
│   ├── core/                        # Configuration settings
│   ├── domain/                      # Models, candle validation, quality rules
│   └── infrastructure/              # Catalog storage and Parquet reader/writer
├── tests/                           # Unit and integration tests
├── Dockerfile                       # Production container definition
├── docker-compose.yml               # Container deployment spec
└── pyproject.toml                   # Project metadata and dependencies
```

---

## Quick Start & Installation

### Requirements
- Python 3.11 - 3.13 (PyArrow compatibility)
- Package Manager: `uv` or `pip`

### Setup Environment
```powershell
cd C:\Users\Admin\BactestInfra\qi-data-wrapper
uv sync
```

### Import Historical Datasets
Import all CSV datasets from `Data_source/` into the local Parquet store:
```powershell
uv run --project qi-data-wrapper python scripts/import_all_datasets.py
```

### Launch the Service
```powershell
uv run --project qi-data-wrapper uvicorn qi_data_wrapper.main:app --port 8001
```

The service will run at `http://localhost:8001`.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | Health check endpoint |
| `/v1/instruments` | `GET` | List all supported canonical instruments (`BTC/USD`, `ETH/USD`, `XRP/BTC`) |
| `/v1/data/resolve` | `POST` | Resolves a dataset version for a requested instrument and timeframe |
| `/v1/datasets/{version_id}/metadata` | `GET` | Returns dataset checksums, date range, and candle counts |
| `/v1/datasets/{version_id}/candles` | `GET` | Retrieves validated OHLCV candles for backtesting |

---

## Unit & Integration Testing

Run the test suite:
```powershell
uv run --project qi-data-wrapper pytest tests --basetemp=.pytest_temp
```

Run isolated Docker container smoke test:
```powershell
docker build -t qi-data-wrapper-e2e .
docker run --rm -v "${PWD}/Data_source:/input:ro" qi-data-wrapper-e2e python scripts/e2e_smoke.py /input/BTCUSD_bitstamp_hourly_2012-2026.csv
```
