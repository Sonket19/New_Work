"""Dependency wiring for FastAPI routes."""
from __future__ import annotations

import importlib
import os
from functools import lru_cache
from pathlib import Path

from app.services.deal_service import DealService
from app.services.doc_builder import DocxBuilder
from app.services.extraction import DocumentExtractor, MetadataExtractor
from app.services.firestore_repository import DealRepository
from app.services.memo_generator import MemoGenerator
from app.services.storage import StorageService


@lru_cache(maxsize=1)
def get_repository() -> DealRepository:
    firestore_client = None
    spec = importlib.util.find_spec("google.cloud.firestore")
    if spec is not None:
        firestore_module = importlib.import_module("google.cloud.firestore")
        firestore_client = firestore_module.Client()
    collection = os.getenv("FIRESTORE_COLLECTION", "deals")
    return DealRepository(client=firestore_client, collection=collection)


@lru_cache(maxsize=1)
def get_storage() -> StorageService:
    bucket_name = os.getenv("STORAGE_BUCKET", "investment_memo_ai")
    base_dir_env = os.getenv("STORAGE_LOCAL_PATH")
    base_dir = Path(base_dir_env) if base_dir_env else None
    return StorageService(bucket_name=bucket_name, base_dir=base_dir)


@lru_cache(maxsize=1)
def get_extractor() -> DocumentExtractor:
    return DocumentExtractor()


@lru_cache(maxsize=1)
def get_metadata_extractor() -> MetadataExtractor:
    return MetadataExtractor()


@lru_cache(maxsize=1)
def get_memo_generator() -> MemoGenerator:
    return MemoGenerator()


@lru_cache(maxsize=1)
def get_doc_builder() -> DocxBuilder:
    return DocxBuilder()


@lru_cache(maxsize=1)
def get_deal_service() -> DealService:
    invite_base_url = os.getenv("FOUNDER_INVITE_BASE_URL", "https://founder-chat.example.com/invite")
    return DealService(
        repository=get_repository(),
        storage=get_storage(),
        extractor=get_extractor(),
        metadata_extractor=get_metadata_extractor(),
        memo_generator=get_memo_generator(),
        doc_builder=get_doc_builder(),
        invite_base_url=invite_base_url,
    )

