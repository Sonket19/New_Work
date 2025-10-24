"""Utilities for parsing uploaded artefacts and extracting metadata."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple


class DocumentExtractor:
    """Simplified extractor that reads text from pdf/other binary payloads."""

    def extract_text(self, *, deal_id: str, file_bytes: bytes, content_type: str) -> Dict[str, str]:
        if content_type == "application/pdf":
            text = self._bytes_to_text(file_bytes)
            return {"pitch_deck": text}
        return {"pitch_deck": ""}

    def _bytes_to_text(self, file_bytes: bytes) -> str:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return "PDF extraction not implemented in local environment"


class MetadataExtractor:
    """Derive company level metadata from raw text."""

    def extract(self, *, deal_id: str, extracted_text: Dict[str, str]) -> Tuple[str, List[str], str]:
        text = extracted_text.get("pitch_deck", "")
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

