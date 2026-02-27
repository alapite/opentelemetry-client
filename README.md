# Load-Testing Client

[![Python application](https://github.com/alapite/opentelemetry-client/actions/workflows/python-app.yml/badge.svg)](https://github.com/alapite/opentelemetry-client/actions/workflows/python-app.yml)

This project contains code for generating OpenTelemetry-instrumented load tests
for a backend which has also been instrumented with OpenTelemetry. The intention 
is to be able to generate tests with a variety of load profiles, from constant to
linear to more sophisticated traffic patterns. While the project-name suggests
the client will only be generating requests for prime-numbers, I envisage a wider
remit for the sorts of requests which the client should be able to make in the future.

## Run Locally (Without Docker)

Use this flow when you want to run the project directly on your machine.

### Prerequisites

- Python 3.12+
- A running backend service that exposes:
  - `GET /api/primes/getPrime`
  - `GET /openapi.json`

Or you could simply use [the one](https://github.com/alapite/primes-backend) I've implemented.

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -e .
```

### 3) Configure environment variables

Set `SERVICE_URL` to your backend URL:

```bash
export SERVICE_URL=http://localhost:8080
```

### 4) Run the FastAPI control API locally

```bash
PYTHONPATH=src uvicorn primes.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

- API docs: `http://localhost:8000/docs`
- UI: `http://localhost:8000/ui`

## Testing

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_example.py

# Run a specific test
pytest tests/test_example.py::test_function_name

# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# Run tests in Docker
docker compose run --rm api pytest

## Web UI

The UI is served by the FastAPI app at `/ui`.

```bash
# Install UI dependencies
cd ui
npm install

# Build UI assets into src/primes/ui/dist
npm run build
```

Then run the API server and visit `http://localhost:8000/ui`.

## Docker Deployment

### Quick Start

Run the entire stack with a single command:

```bash
docker compose up -d
```

This starts three services:
- **API** (port 8000): FastAPI server for test management
- **Locust** (port 8089): Web UI for load testing at http://localhost:8089
- **Client**: CLI client for load generation

Access the Locust web UI at http://localhost:8089

### Configuration

Copy the example environment file and configure as needed:

```bash
cp .env.docker.example .env.docker
# Edit .env.docker with your settings
```

Key environment variables:
- `SERVICE_URL`: Backend API URL (use `http://api:8000` for Docker networking)
- `OPENAPI_SPEC_URL`: Optional OpenAPI spec URL (defaults to `${SERVICE_URL}/v3/api-docs`)
- `LOCUST_MODE`: Execution mode (`standalone` or `distributed`)
- `SPAWN_RATE`: Users spawned per second
- `WORKERS`: Number of worker processes for distributed mode

Note: the client expects the backend to expose an `/api/primes` endpoint. If the
OpenAPI spec does not include that path, the client will log a warning and exit
to avoid noisy 404s.


