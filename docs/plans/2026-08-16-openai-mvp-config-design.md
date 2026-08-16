# OpenAI MVP Configuration Simplification Design

## Decision

Human Layer will use OpenAI as its sole hosted LLM integration for the MVP. The previous provider abstraction exposed provider, base URL, API key, and model variables even though the product has no current non-OpenAI deployment path.

## Deployment contract

The backend accepts only these deployment-facing variables:

```text
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
CORS_ORIGIN=https://<dashboard>.vercel.app
```

`OPENAI_MODEL` defaults to `gpt-5-mini`. The OpenAI base URL is a code constant, `https://api.openai.com/v1`, and is not configurable for this MVP. `CORS_ORIGIN` is a single exact production dashboard origin.

The frontend remains unchanged: it separately requires `NEXT_PUBLIC_API_BASE_URL` because it is deployed independently from the API.

## Runtime behavior

- When `OPENAI_API_KEY` is present, the semantic extraction factory creates the existing OpenAI-compatible adapter using the fixed OpenAI API base URL and configured/default model.
- When it is absent, the factory uses the deterministic rule-based adapter. This keeps local development and automated tests credential-free.
- No endpoint, request schema, or stored data changes.

## Scope

- Simplify `Settings`, adapter factory, CORS wiring, environment example, README, and focused configuration/factory tests.
- Remove the configurable provider and base URL variables; do not keep aliases for the old names.
- Keep `HUMAN_LAYER_HOST` and `HUMAN_LAYER_PORT` as local server controls, but do not present them as required cloud deployment variables.

## Acceptance criteria

- With only `OPENAI_API_KEY`, the factory creates an adapter aimed at OpenAI with default model `gpt-5-mini`.
- `OPENAI_MODEL` overrides the default.
- With no key, the deterministic rule-based adapter is used.
- `CORS_ORIGIN` enables only the exact configured dashboard origin.
- Docs list the short deployment contract and explicitly tell users that the API key belongs to the backend, never the frontend.
