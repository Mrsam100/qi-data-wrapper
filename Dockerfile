FROM python:3.13-slim

# Install CA certificates so Python can verify HTTPS/TLS peers.
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests
COPY scripts ./scripts

RUN pip install --no-cache-dir ".[dev]"

CMD ["python", "-m", "uvicorn", "qi_data_wrapper.main:app", "--host", "0.0.0.0", "--port", "8001"]
