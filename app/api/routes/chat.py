from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import RequestIdDep
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services.conversation_service import ConversationService, get_conversation_service

router = APIRouter(tags=["chat"])

ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: ConversationServiceDep,
    request_id: RequestIdDep,
) -> ChatResponse:
    return await service.chat(payload, request_id=request_id or None)


@router.get("/chat/{thread_id}/history", response_model=ChatHistoryResponse)
async def chat_history(
    thread_id: str,
    service: ConversationServiceDep,
) -> ChatHistoryResponse:
    return await service.get_history(thread_id)
