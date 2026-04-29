"""Stable, non-domain constants. Anything domain-specific (degradation rates,
emission factors, etc.) must NOT live here — it belongs to the
AssumptionProviderTool with its source metadata.
"""

API_TITLE = "SolarLife AI Backend"
API_VERSION = "0.1.0"
API_DESCRIPTION = "Conversational solar planning agent (ODS 7)."

REQUEST_ID_HEADER = "X-Request-ID"
TRACE_ID_HEADER = "X-Trace-ID"
