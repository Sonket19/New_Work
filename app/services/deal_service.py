"""High level orchestration for deal workflows."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException, UploadFile

from app.models.deal_models import DealWeightage
from app.services.doc_builder import DocxBuilder
from app.services.extraction import DocumentExtractor, MetadataExtractor, default_weightage
from app.services.firestore_repository import DealRepository
from app.services.memo_generator import MemoGenerator
from app.services.storage import StorageService


class DealService:
    def __init__(
        self,
        repository: DealRepository,
        storage: StorageService,
        extractor: DocumentExtractor,
        metadata_extractor: MetadataExtractor,
        memo_generator: MemoGenerator,
        doc_builder: DocxBuilder,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.extractor = extractor
        self.metadata_extractor = metadata_extractor
        self.memo_generator = memo_generator
        self.doc_builder = doc_builder

    async def process_upload(self, upload: UploadFile) -> Dict[str, Any]:
        deal_id = uuid.uuid4().hex[:6]
        file_bytes = await upload.read()
        filename = upload.filename or f"upload_{deal_id}"
        storage_url = self.storage.upload_bytes(deal_id, filename, file_bytes)

        extracted_text_raw = self.extractor.extract_text(
            deal_id=deal_id,
            file_bytes=file_bytes,
            content_type=upload.content_type or "application/octet-stream",
        )
        company_name, founders, sector = self.metadata_extractor.extract(
            deal_id=deal_id, extracted_text=extracted_text_raw
        )

        weightage = default_weightage()
        memo_body, generated_at = self.memo_generator.generate(
            company_name=company_name,
            sector=sector,
            founders=founders,
            extracted_text=extracted_text_raw,
            weightage=weightage,
        )
        docx_path = self.doc_builder.build(deal_id, memo_body)
        docx_url = self.storage.upload_bytes(
            deal_id,
            "memo.docx",
            docx_path.read_bytes(),
        )

        created_at = datetime.utcnow()
        processed_at = datetime.utcnow()

        deal_document = {
            "raw_files": {"pitch_deck_url": storage_url},
            "public_data": {
                "competitors": [],
                "news": [],
                "market_stats": {},
                "founder_profile": [],
            },
            "metadata": {
                "weightage": weightage,
                "created_at": created_at.isoformat() + "Z",
                "status": "processed",
                "deal_id": deal_id,
                "company_name": company_name,
                "processed_at": processed_at.isoformat() + "Z",
                "error": None,
                "sector": sector,
                "founder_names": founders,
            },
            "extracted_text": {
                "pitch_deck": {
                    "raw_text": extracted_text_raw.get("pitch_deck", ""),
                }
            },
            "memo": {
                "draft_v1": memo_body,
                "generated_at": generated_at.isoformat() + "Z",
                "docx_url": docx_url,
            },
            "founder_chat": [],
            "founder_invite": None,
        }

        self.repository.upsert(deal_id, deal_document)
        return deal_document

    def regenerate_memo(self, deal_id: str, payload: DealWeightage) -> Dict[str, Any]:
        deal = self.repository.get(deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        extracted = deal.get("extracted_text", {}).get("pitch_deck", {})
        memo_body, generated_at = self.memo_generator.generate(
            company_name=deal.get("metadata", {}).get("company_name", deal_id),
            sector=deal.get("metadata", {}).get("sector", "General"),
            founders=deal.get("metadata", {}).get("founder_names", []),
            extracted_text={"pitch_deck": extracted.get("raw_text", "")},
            weightage=payload.dict(),
        )

        docx_path = self.doc_builder.build(deal_id, memo_body)
        docx_url = self.storage.upload_bytes(
            deal_id,
            "memo.docx",
            docx_path.read_bytes(),
        )

        deal["metadata"]["weightage"] = payload.dict()
        deal["memo"] = {
            "draft_v1": memo_body,
            "generated_at": generated_at.isoformat() + "Z",
            "docx_url": docx_url,
        }
        self.repository.upsert(deal_id, deal)
        return deal

    def get_deal(self, deal_id: str) -> Dict[str, Any]:
        deal = self.repository.get(deal_id)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        return deal

    def list_deals(self) -> Any:
        return self.repository.get_all()

    def delete_deal(self, deal_id: str) -> None:
        if not self.repository.get(deal_id):
            raise HTTPException(status_code=404, detail="Deal not found")
        self.repository.delete(deal_id)
        self.storage.delete_folder(deal_id)

    def download_memo(self, deal_id: str) -> Path:
        self.get_deal(deal_id)
        return self.storage.get_local_path(deal_id, "memo.docx")

    def download_pitch_deck(self, deal_id: str) -> Path:
        deal = self.get_deal(deal_id)
        raw_url = deal.get("raw_files", {}).get("pitch_deck_url")
        if not raw_url:
            raise HTTPException(status_code=404, detail="Pitch deck not available")
        filename = raw_url.split("/")[-1]
        return self.storage.get_local_path(deal_id, filename)

    def create_founder_invite(
        self, deal_id: str, *, founder_email: str, expires_in_minutes: int
    ) -> Dict[str, Any]:
        if not self.repository.get(deal_id):
            raise HTTPException(status_code=404, detail="Deal not found")
        token = uuid.uuid4().hex
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        invite_url = f"https://founder-chat.example.com/invite/{token}"
        invite = {
            "token": token,
            "founder_email": founder_email,
            "expires_at": expires_at.isoformat() + "Z",
            "used": False,
            "invite_url": invite_url,
        }
        self.repository.set_invite(deal_id, invite)
        return invite

    def record_founder_chat(self, deal_id: str, transcript: Dict[str, Any]) -> None:
        if not self.repository.get(deal_id):
            raise HTTPException(status_code=404, detail="Deal not found")
        self.repository.append_chat_transcript(deal_id, transcript)

