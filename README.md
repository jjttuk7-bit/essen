# Human Layer

Human Layer is a local document-intelligence MVP. It analyzes a long document into semantic
slots, scores its signal quality, and renders human-ready outputs with source provenance.

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+

## Deployment configuration

Three variables are needed to run this in the cloud, all on the backend:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
CORS_ORIGIN=https://app.example.com
```

The frontend needs no deployment variables. It defaults to the deployed backend URL in
`DEPLOYED_API_BASE_URL` (`lib/api.ts`) and to `http://127.0.0.1:8000` in development. Set
`NEXT_PUBLIC_API_BASE_URL` only to point a build somewhere else, such as a staging API —
it is inlined at build time, so changing it requires a rebuild, not just a restart.

- `OPENAI_API_KEY` — **backend deployment only.** Never set it on the frontend and never copy it
  into a `NEXT_PUBLIC_` variable, which is inlined into the browser bundle. When it is unset the
  backend falls back to a deterministic local analyzer that makes no network calls.
- `OPENAI_MODEL` — optional; defaults to `gpt-5-mini`.
- `CORS_ORIGIN` — the one exact browser origin allowed to call the API, with no trailing slash.
  It must match the browser's `Origin` header exactly; requests from any other origin are
  rejected.

The OpenAI base URL is fixed in code at `https://api.openai.com/v1`.

## Local setup

Copy the example environment file and adjust as needed:

```powershell
Copy-Item backend/.env.example backend/.env
```

Local runs also support `HUMAN_LAYER_ENV` (default `development`), `HUMAN_LAYER_HOST`
(default `127.0.0.1`), and `HUMAN_LAYER_PORT` (default `8000`). These are development-only
conveniences and are not part of the deployment contract above.

Start the API:

```powershell
cd backend
uv run --python 3.12 python -m app.main
```

Check its status at `http://127.0.0.1:8000/health`.

Start the frontend:

```powershell
npm install
npm run dev
```

## Tests

Backend:

```powershell
cd backend
uv run --python 3.12 pytest -q
```

The backend suite is hermetic: it clears `OPENAI_API_KEY` so a developer key in the shell never
sends test runs to the real API.

Frontend:

```powershell
npm test
```
