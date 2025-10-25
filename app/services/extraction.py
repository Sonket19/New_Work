"""Utilities for parsing uploaded artefacts and extracting metadata."""
from __future__ import annotations

import logging
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


logger = logging.getLogger(__name__)


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
        process_options = self._build_imageless_options()

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

    def _build_imageless_options(self) -> Optional[documentai.ProcessOptions]:
        """Construct ProcessOptions that force imageless OCR mode when supported."""

        if not hasattr(documentai, "ProcessOptions"):
            logger.warning(
                "google-cloud-documentai %s does not expose ProcessOptions; skipping imageless mode",
                getattr(documentai, "__version__", "unknown"),
            )
            return None

        try:
            process_options = documentai.ProcessOptions()
        except TypeError:  # pragma: no cover - legacy client that can't init without args
            logger.warning(
                "google-cloud-documentai %s cannot instantiate ProcessOptions without args; skipping imageless mode",
                getattr(documentai, "__version__", "unknown"),
            )
            return None

        config_paths = self._imageless_config_candidates(process_options)
        if not config_paths:
            logger.warning(
                "ProcessOptions missing ocr_config/document_ocr_config; skipping imageless mode",
                extra={"documentai_version": getattr(documentai, "__version__", "unknown")},
            )
            return None

        for attr_name, config_cls in config_paths:
            config = self._instantiate_ocr_config(config_cls)
            if config is None:
                continue

            if not self._apply_imageless_flags(config):
                continue

            try:
                setattr(process_options, attr_name, config)
            except Exception:  # pragma: no cover - defensive guard against proto attr changes
                logger.debug(
                    "Failed to set %s on ProcessOptions", attr_name, exc_info=True
                )
                continue

            logger.info(
                "Applied imageless mode via %s", attr_name,
                extra={
                    "documentai_version": getattr(documentai, "__version__", "unknown"),
                    "config_cls": getattr(config_cls, "__name__", str(config_cls)),
                },
            )
            return process_options

        logger.warning(
            "google-cloud-documentai %s does not support imageless mode toggles; continuing without it",
            getattr(documentai, "__version__", "unknown"),
        )
        return None

    def _imageless_config_candidates(self, process_options: Any) -> List[Tuple[str, Any]]:
        """Return potential ProcessOptions attributes and constructors for imageless OCR."""

        candidates: List[Tuple[str, Any]] = []

        ocr_config_cls = getattr(documentai, "OcrConfig", None)
        if hasattr(process_options, "ocr_config") and ocr_config_cls is not None:
            candidates.append(("ocr_config", ocr_config_cls))

        if hasattr(process_options, "document_ocr_config"):
            document_ocr_cls = getattr(documentai, "DocumentOcrConfig", None)
            if document_ocr_cls is not None:
                candidates.append(("document_ocr_config", document_ocr_cls))
            elif ocr_config_cls is not None:
                candidates.append(("document_ocr_config", ocr_config_cls))

        return candidates

    def _instantiate_ocr_config(self, config_cls: Any) -> Optional[Any]:
        """Instantiate the given OCR config proto, logging if the client is too old."""

        try:
            return config_cls()
        except TypeError:  # pragma: no cover - legacy client that can't init without args
            logger.warning(
                "google-cloud-documentai %s cannot instantiate %s without args; skipping imageless mode",
                getattr(documentai, "__version__", "unknown"),
                getattr(config_cls, "__name__", str(config_cls)),
            )
        except Exception:  # pragma: no cover - defensive guard against proto attr changes
            logger.debug(
                "Unexpected error instantiating %s for imageless mode", config_cls,
                exc_info=True,
            )
        return None

    def _apply_imageless_flags(self, config: Any) -> bool:
        """Attempt to switch imageless mode on for the provided OCR config proto."""

        applied = False

        if hasattr(config, "enable_imageless_mode"):
            try:
                setattr(config, "enable_imageless_mode", True)
            except Exception:  # pragma: no cover - defensive guard against proto attr changes
                logger.debug(
                    "Failed to set enable_imageless_mode on %s", config.__class__.__name__,
                    exc_info=True,
                )
            else:
                applied = True

        advanced_options = getattr(config, "advanced_ocr_options", None)
        if advanced_options is not None:
            try:
                if hasattr(advanced_options, "append"):
                    if "ENABLE_IMAGELESS_MODE" not in advanced_options:
                        advanced_options.append("ENABLE_IMAGELESS_MODE")
                else:  # pragma: no cover - fallback for immutable containers
                    updated = list(advanced_options)
                    if "ENABLE_IMAGELESS_MODE" not in updated:
                        updated.append("ENABLE_IMAGELESS_MODE")
                    setattr(config, "advanced_ocr_options", updated)
            except Exception:  # pragma: no cover - defensive guard against proto attr changes
                logger.debug(
                    "Failed to append ENABLE_IMAGELESS_MODE to advanced_ocr_options on %s",
                    config.__class__.__name__,
                    exc_info=True,
                )
            else:
                applied = True

        return applied

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

