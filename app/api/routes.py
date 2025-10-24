"""API routes for the AI startup analyst backend."""
from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.dependencies import get_deal_service
from app.models.deal_models import (
    DealDocument,
    FounderChatTranscript,
    FounderInviteRequest,
    FounderInviteResponse,
    MemoRegenerationRequest,
    OperationResponse,
    UploadResponse,
)
from app.services.deal_service import DealService


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_deal(
    file: UploadFile = File(...),
    service: DealService = Depends(get_deal_service),
) -> UploadResponse:
    deal = await service.process_upload(file)
    metadata = deal.get("metadata", {})
    return UploadResponse(deal_id=metadata.get("deal_id", ""), status=metadata.get("status", "pending"))


@router.post("/generate_memo/{deal_id}", response_model=OperationResponse)
def regenerate_memo(
    deal_id: str,
    payload: MemoRegenerationRequest,
    service: DealService = Depends(get_deal_service),
) -> OperationResponse:
    service.regenerate_memo(deal_id, payload)
    return OperationResponse(message="Memo regenerated successfully")


@router.get("/deals/{deal_id}", response_model=DealDocument)
def get_deal(
    deal_id: str,
    service: DealService = Depends(get_deal_service),
) -> DealDocument:
    deal = service.get_deal(deal_id)
    return DealDocument.model_validate(deal)


@router.get("/deals", response_model=List[DealDocument])
def list_deals(
    service: DealService = Depends(get_deal_service),
) -> List[DealDocument]:
    deals = service.list_deals()
    return [DealDocument.model_validate(deal) for deal in deals]


@router.delete("/deals/{deal_id}", response_model=OperationResponse)
def delete_deal(
    deal_id: str,
    service: DealService = Depends(get_deal_service),
) -> OperationResponse:
    service.delete_deal(deal_id)
    return OperationResponse(message="Deal deleted successfully")


@router.get("/download_memo/{deal_id}")
def download_memo(
    deal_id: str,
    service: DealService = Depends(get_deal_service),
) -> FileResponse:
    path = service.download_memo(deal_id)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@router.get("/download_pitch_deck/{deal_id}")
def download_pitch_deck(
    deal_id: str,
    service: DealService = Depends(get_deal_service),
) -> FileResponse:
    path = service.download_pitch_deck(deal_id)
    return FileResponse(path)


@router.post("/deals/{deal_id}/founder_invite", response_model=FounderInviteResponse)
def create_founder_invite(
    deal_id: str,
    payload: FounderInviteRequest,
    service: DealService = Depends(get_deal_service),
) -> FounderInviteResponse:
    invite = service.create_founder_invite(
        deal_id,
        founder_email=payload.founder_email,
        expires_in_minutes=payload.expires_in_minutes,
    )
    return FounderInviteResponse(
        invite_url=invite.get("invite_url", ""),
        expires_at=datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00")),
    )


@router.post("/deals/{deal_id}/founder_chat", response_model=OperationResponse)
def record_founder_chat(
    deal_id: str,
    transcript: FounderChatTranscript,
    service: DealService = Depends(get_deal_service),
) -> OperationResponse:
    service.record_founder_chat(
        deal_id,
        {
            "participant": transcript.participant,
            "message": transcript.message,
            "timestamp": transcript.timestamp.isoformat(),
        },
    )
    return OperationResponse(message="Chat transcript stored")

