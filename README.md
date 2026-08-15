# Human Layer

Human Layer is a local document-intelligence MVP. This first backend milestone exposes a health endpoint for checking that the API is running.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

## Local setup

From the repository root, copy the example environment file and set any values needed for your local run:

```powershell
Copy-Item backend/.env.example backend/.env
```

The supported environment variables are:

- `HUMAN_LAYER_ENV` — application environment; defaults to `development`.
- `HUMAN_LAYER_HOST` — local server host; defaults to `127.0.0.1`.
- `HUMAN_LAYER_PORT` — local server port; defaults to `8000`.

Start the API:

```powershell
cd backend
uv run --python 3.12 python -m app.main
```

Check its status at `http://127.0.0.1:8000/health`.

Run the backend test suite:

```powershell
cd backend
uv run --python 3.12 pytest tests/test_health.py -v
```
