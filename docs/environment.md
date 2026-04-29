# Environment

## Core variables

Copy `.env.example` to `.env` and configure at least:

```env
LLM_PROVIDER=nvidia
LLM_MODEL=nvidia/nemotron-3-super-120b-a12b
NVIDIA_API_KEY=...
NVIDIA_BASE_URL=
DATABASE_URL=sqlite:///./solarlife.db
MEMORY_STORAGE_BACKEND=sqlite
TRACE_ENABLED=true
```

`NVIDIA_BASE_URL` is optional and is only needed when targeting a self-hosted NVIDIA NIM instead of the hosted NVIDIA API Catalog.

For compatibility during migration, the backend still accepts `OPENAI_API_KEY` plus an NVIDIA `OPENAI_BASE_URL`, but the preferred path is the native NVIDIA integration with `NVIDIA_API_KEY`.

## External providers

Network-backed tools depend on these providers:

- `GEOCODING_BASE_URL`: Nominatim / OpenStreetMap
- `PVGIS_BASE_URL`: PVGIS PVcalc
- `BDNS_API_BASE_URL`: BDNS / SNPSAP
- `ESIOS_API_BASE_URL`: ESIOS / REE
- `OMIE_BASE_URL`: OMIE

## Tokens and credentials

- `NVIDIA_API_KEY`: required for the real agent when `LLM_PROVIDER=nvidia`.
- `OPENAI_API_KEY`: required only when `LLM_PROVIDER=openai`.
- `ESIOS_API_TOKEN`: required for live PVPC reference price queries.
- BDNS, PVGIS, OMIE and public Nominatim do not require a project secret, but they do require outbound network access.

## Guardrails

The runtime supports these agent guardrail flags:

```env
AGENT_PII_GUARDRAILS_ENABLED=true
AGENT_PROMPT_GUARDRAILS_ENABLED=true
AGENT_OUTPUT_GUARDRAILS_ENABLED=true
AGENT_HUMAN_IN_THE_LOOP_ENABLED=false
AGENT_HUMAN_IN_THE_LOOP_TOOLS=[]
```

Enable human-in-the-loop only for specific tools that should require manual approval.
