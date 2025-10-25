"""Utilities for parsing uploaded artefacts and extracting metadata."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from google.cloud import documentai_v1 as documentai
except ImportError:  # pragma: no cover - support environments with older client versions
    try:
        from google.cloud import documentai  # type: ignore[no-redef]
    except ImportError as import_error:  # pragma: no cover - surfaced at runtime
        documentai = None  # type: ignore[assignment]
        _DOCUMENT_AI_IMPORT_ERROR = import_error  # type: ignore[name-defined]
    else:  # pragma: no cover - only executed with legacy package layout
        _DOCUMENT_AI_IMPORT_ERROR = None  # type: ignore[name-defined]
else:
    _DOCUMENT_AI_IMPORT_ERROR = None  # type: ignore[name-defined]

from google.oauth2 import service_account


class DocumentExtractor:
    """Extract rich text insights using Google Document AI."""

    def __init__(
        self,
        *,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        processor_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        client: Optional[documentai.DocumentProcessorServiceClient] = None,
    ) -> None:
        if documentai is None:  # pragma: no cover - runtime guard for missing dependency
            raise RuntimeError(
                "google-cloud-documentai is required for DocumentExtractor. "
                "Install the library and ensure it is available to the application."
            ) from _DOCUMENT_AI_IMPORT_ERROR

        env_project = project_id or os.getenv("GCP_PROJECT_ID")
        env_location = location or os.getenv("GCP_LOCATION")
        env_processor = processor_id or os.getenv("DOCUMENT_AI_PROCESSOR")

        if not env_project or not env_location or not env_processor:
            raise RuntimeError(
                "DocumentExtractor requires GCP project, location, and Document AI processor configuration."
            )

        credentials = None
        path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if path:
            credentials = service_account.Credentials.from_service_account_file(path)

        client_kwargs: Dict[str, Any] = {}
        if credentials is not None:
            client_kwargs["credentials"] = credentials

        self.client = client or documentai.DocumentProcessorServiceClient(**client_kwargs)
        if "/" in env_processor:
            # Fully-qualified processor name supplied via configuration.
            self.processor_name = env_processor
        else:
            self.processor_name = self.client.processor_path(env_project, env_location, env_processor)

    def extract_text(
        self, *, deal_id: str, file_bytes: bytes, content_type: str
    ) -> Dict[str, Any]:
        """Invoke Document AI and return raw text plus structured analysis."""

        mime_type = content_type or "application/pdf"
        raw_document = documentai.RawDocument(content=file_bytes, mime_type=mime_type)
        process_options = None
        if hasattr(documentai, "ProcessOptions") and hasattr(documentai, "OcrConfig"):
            try:
                ocr_config = documentai.OcrConfig(enable_imageless_mode=True)
            except TypeError:  # pragma: no cover - older client libraries
                ocr_config = None
            if ocr_config is not None:
                try:
                    process_options = documentai.ProcessOptions(ocr_config=ocr_config)
                except TypeError:  # pragma: no cover - older client libraries
                    process_options = None

        request_kwargs = {"name": self.processor_name, "raw_document": raw_document}
        if process_options is not None:
            request_kwargs["process_options"] = process_options

        request = documentai.ProcessRequest(**request_kwargs)
        result = self.client.process_document(request=request)

        document = result.document
        if document is None:
            return {"pitch_deck": "", "analysis": {"entities": [], "pages": []}}

        text = document.text or ""
        entities = getattr(document, "entities", []) or []
        pages = getattr(document, "pages", []) or []
        analysis = {
            "entities": [self._serialize_entity(entity) for entity in entities],
            "pages": [self._serialize_page(page, text) for page in pages],
        }
        return {"pitch_deck": text, "analysis": analysis}

    def _serialize_entity(self, entity: documentai.Document.Entity) -> Dict[str, Any]:
        return {
            "type": entity.type_,
            "mention_text": entity.mention_text,
            "confidence": entity.confidence,
            "mention_id": entity.mention_id,
        }

    def _serialize_page(self, page: documentai.Document.Page, document_text: str) -> Dict[str, Any]:
        return {
            "page_number": page.page_number,
            "layout_confidence": page.layout.confidence if page.layout else None,
            "tables": [self._serialize_table(table, document_text) for table in page.tables],
            "paragraphs": [
                self._serialize_paragraph(paragraph, document_text) for paragraph in page.paragraphs
            ],
        }

    def _serialize_table(
        self, table: documentai.Document.Page.Table, document_text: str
    ) -> Dict[str, Any]:
        rows = []
        for row in table.body_rows:
            cells = [self._layout_to_text(cell.layout, document_text) for cell in row.cells]
            rows.append(cells)
        header_rows = []
        for row in table.header_rows:
            cells = [self._layout_to_text(cell.layout, document_text) for cell in row.cells]
            header_rows.append(cells)
        return {"header_rows": header_rows, "body_rows": rows}

    def _serialize_paragraph(
        self, paragraph: documentai.Document.Page.Paragraph, document_text: str
    ) -> str:
        return self._layout_to_text(paragraph.layout, document_text)

    def _layout_to_text(
        self, layout: Optional[documentai.Document.Page.Layout], document_text: str
    ) -> str:
        if layout is None:
            return ""
        text_anchor = layout.text_anchor
        if text_anchor is None:
            return ""
        if text_anchor.content:
            return text_anchor.content
        segments = getattr(text_anchor, "text_segments", []) or []
        pieces: List[str] = []
        for segment in segments:
            start_index = int(getattr(segment, "start_index", 0) or 0)
            end_index = int(getattr(segment, "end_index", 0) or 0)
            pieces.append(document_text[start_index:end_index])
        return "".join(pieces)


class MetadataExtractor:
    """Derive company level metadata from raw text."""

    def extract(self, *, deal_id: str, extracted_text: Dict[str, Any]) -> Tuple[str, List[str], str]:
        text_payload = extracted_text.get("pitch_deck", "")
        if isinstance(text_payload, dict):
            text = text_payload.get("raw_text", "")
        else:
            text = str(text_payload)
        company = self._guess_company_name(text) or f"Deal {deal_id}"
        founders = self._guess_founders(text)
        sector = self._guess_sector(text)
        return company, founders, sector

    def _guess_company_name(self, text: str) -> str:
        for line in text.splitlines():
            line = line.strip()
            if line and len(line.split()) <= 5:
                return line
        return ""

    def _guess_founders(self, text: str) -> List[str]:
        founders: List[str] = []
        for line in text.splitlines():
            clean = line.strip()
            if clean.lower().startswith("founder") or clean.lower().startswith("team"):
                parts = [segment.strip() for segment in clean.split(":", 1)[-1].split(",")]
                founders.extend([p for p in parts if p])
        return founders[:5]

    def _guess_sector(self, text: str) -> str:
        keywords = {
            "ai": "Artificial Intelligence",
            "health": "Healthcare",
            "fintech": "FinTech",
            "agri": "Agriculture",
            "edtech": "Education Technology",
        }
        lowered = text.lower()
        for key, value in keywords.items():
            if key in lowered:
                return value
        return "General"


def default_weightage() -> Dict[str, int]:
    return {
        "traction": 20,
        "team_strength": 20,
        "claim_credibility": 20,
        "financial_health": 20,
        "market_opportunity": 20,
    }


def utcnow_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

