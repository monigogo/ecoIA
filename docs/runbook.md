# Runbook

## Start the backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The API exposes:

- `POST /chat`
- `GET /chat/{thread_id}/history`
- `GET /traces/{trace_id}`
- `GET /health`

## Example chat request

```powershell
curl -X POST http://127.0.0.1:8000/chat `
  -H "Content-Type: application/json" `
  -d "{\"message\":\"Vivo en Sevilla y quiero una estimación orientativa de paneles y ayudas.\",\"include_trace\":true}"
```

## Fetch the persisted trace

Take the `trace_id` returned by `/chat` and query:

```powershell
curl http://127.0.0.1:8000/traces/<trace_id>
```

Use the trace to inspect:

- message receipt
- tool calls and delegations
- warnings
- recovery attempts and partial results
- final answer generation

## Tests

Offline tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Smoke tests with a real LLM:

```powershell
.\.venv\Scripts\python.exe -m pytest -m smoke -q
```

The smoke suite is skipped automatically unless the configured provider has credentials:
`NVIDIA_API_KEY` for `LLM_PROVIDER=nvidia`, or `OPENAI_API_KEY` for `LLM_PROVIDER=openai`.

## Network requirements

These tools require outbound network access:

- `geocode_location`
- `estimate_solar_production_with_pvgis`
- `search_subsidies`
- `get_pvpc_surplus_compensation_price`
- `get_pvpc_import_reference_price`
- `get_market_sale_reference_price`

## Failure handling

Expected graceful-recovery behavior:

- ask for the smallest missing input
- use explicit assumption candidates when allowed
- return partial results when safe
- never fabricate missing domain values
