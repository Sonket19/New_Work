"""Firestore repository abstraction with in-memory fallback."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class DealRepository:
    """Wrapper around Firestore with an in-memory fallback implementation."""

    def __init__(self, client: Optional[Any] = None, collection: str = "deals") -> None:
        self.client = client
        self.collection = collection
        self._memory_store: Dict[str, Dict[str, Any]] = {}

    def upsert(self, deal_id: str, data: Dict[str, Any]) -> None:
        if self.client:
            self.client.collection(self.collection).document(deal_id).set(data)
        else:
            self._memory_store[deal_id] = data

    def get(self, deal_id: str) -> Optional[Dict[str, Any]]:
        if self.client:
            doc = self.client.collection(self.collection).document(deal_id).get()
            return doc.to_dict() if doc.exists else None
        return self._memory_store.get(deal_id)

    def get_all(self) -> List[Dict[str, Any]]:
        if self.client:
            docs = self.client.collection(self.collection).stream()
            return [doc.to_dict() for doc in docs]
        return list(self._memory_store.values())

    def delete(self, deal_id: str) -> None:
        if self.client:
            self.client.collection(self.collection).document(deal_id).delete()
        else:
            self._memory_store.pop(deal_id, None)

    def append_chat_transcript(self, deal_id: str, transcript: Dict[str, Any]) -> None:
        if self.client:
            doc_ref = self.client.collection(self.collection).document(deal_id)
            snapshot = doc_ref.get()
            chat = []
            if snapshot.exists:
                data = snapshot.to_dict()
                chat = list(data.get("founder_chat", []))
            chat.append(transcript)
            doc_ref.update({"founder_chat": chat})
        else:
            deal = self._memory_store.setdefault(deal_id, {})
            chat = deal.setdefault("founder_chat", [])
            chat.append(transcript)

    def set_invite(self, deal_id: str, invite: Dict[str, Any]) -> None:
        if self.client:
            self.client.collection(self.collection).document(deal_id).update({"founder_invite": invite})
        else:
            deal = self._memory_store.setdefault(deal_id, {})
            deal["founder_invite"] = invite

    def touch_timestamp(self, deal_id: str, field: str, value: Optional[datetime] = None) -> None:
        value = value or datetime.utcnow()
        if self.client:
            self.client.collection(self.collection).document(deal_id).update({field: value})
        else:
            deal = self._memory_store.setdefault(deal_id, {})
            deal[field] = value.isoformat()

