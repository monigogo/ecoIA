from __future__ import annotations

import anyio
from fastapi import APIRouter

from app.api.dependencies import TraceRepositoryDep
from app.schemas.trace import TraceResponse

router = APIRouter(tags=["traces"])


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    repository: TraceRepositoryDep,
) -> TraceResponse:
    return await anyio.to_thread.run_sync(lambda: repository.get_trace(trace_id))
