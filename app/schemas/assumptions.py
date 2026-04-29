"""Schemas for the AssumptionProvider subsystem.

Design rule: this module does not encode domain-specific values. It only
defines the shape of requests and candidate responses. Generation of
candidates is reasoned by the LLM via ``AssumptionService``.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class AssumptionConfidence(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class AssumptionSourceType(StrEnum):
    user_provided = "user_provided"
    external_api = "external_api"
    uploaded_document = "uploaded_document"
    technical_reference = "technical_reference"


class AssumptionRequest(BaseModel):
    """Request issued by the agent to the AssumptionProvider.

    ``domain`` is a free-form key (e.g. ``solar_degradation``,
    ``system_losses``, ``battery_depth_of_discharge``). It is NOT enumerated
    on purpose so the system stays open and the LLM reasons over the
    request, not a closed switch.
    """

    domain: str = Field(description="Free-form domain key the agent needs candidates for.")
    context: str = Field(description="Natural-language context provided by the agent.")


class AssumptionCandidate(BaseModel):
    """A candidate assumption returned by the provider.

    The agent receives a list of these and MUST pick one explicitly,
    recording the rationale in the natural trace. Candidates are never
    applied silently.
    """

    id: str = Field(description="Stable identifier unique within the response.")
    domain: str = Field(description="Echoed from the request.")
    label: str = Field(description="Short scenario name, e.g. 'residential conservative'.")
    value: float | int | str = Field(description="The candidate value itself.")
    unit: str | None = Field(default=None, description="Unit, if applicable (e.g. '%/year').")
    source_type: AssumptionSourceType
    source_name: str = Field(description="Human-readable source name, datasheet, or registry source_id.")
    source_url: str | None = Field(default=None, description="Citable URL when the source is web-accessible.")
    confidence: AssumptionConfidence
    reasoning: str = Field(description="Why this candidate is plausible for the request context.")
    limitations: str = Field(description="Caveats; under what conditions this candidate is unreliable.")
    requires_user_disclosure: bool = Field(
        default=True,
        description="Whether the agent must declare this candidate when used.",
    )


class AssumptionResponse(BaseModel):
    """Response from the AssumptionProvider.

    Never carries a selected candidate. Selection is the agent's job.
    """

    candidates: list[AssumptionCandidate] = Field(
        description="Two or more candidate scenarios. The agent picks one and explains the choice.",
    )
    notes: str | None = Field(
        default=None,
        description="Free-form caveats or guidance from the provider. Not a directive.",
    )


class ReferenceSource(BaseModel):
    """An entry in ``reference_sources.json``.

    This is a citable registry, not a defaults table. Values are NOT stored
    here — only pointers to authoritative sources the LLM may cite when
    proposing candidates.
    """

    source_id: str
    title: str
    organization: str
    url: str | None = None
    source_type: AssumptionSourceType
    last_checked: str | None = None
    notes: str | None = None
