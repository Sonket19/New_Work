"""Storage service abstraction used for Google Cloud Storage integration."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO, Optional

from fastapi import UploadFile


class StorageService:
    """Persist files to a local directory while mimicking a GCS bucket."""

    def __init__(self, bucket_name: str = "investment_memo_ai", base_dir: Optional[Path] = None) -> None:
        self.bucket_name = bucket_name
        self.base_dir = base_dir or Path(".storage")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _object_path(self, deal_id: str, filename: str) -> Path:
        deal_dir = self.base_dir / deal_id
        deal_dir.mkdir(parents=True, exist_ok=True)
        return deal_dir / filename

    def upload_uploadfile(self, deal_id: str, upload: UploadFile, *, destination: Optional[str] = None) -> str:
        """Persist an :class:`UploadFile` to storage and return a pseudo gs:// url."""

        target_name = destination or upload.filename or "file"
        path = self._object_path(deal_id, target_name)
        data = upload.file.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        path.write_bytes(data)
        return f"gs://{self.bucket_name}/{deal_id}/{target_name}"

    def upload_bytes(self, deal_id: str, filename: str, data: bytes) -> str:
        path = self._object_path(deal_id, filename)
        path.write_bytes(data)
        return f"gs://{self.bucket_name}/{deal_id}/{filename}"

    def upload_fileobj(self, deal_id: str, filename: str, fileobj: BinaryIO) -> str:
        path = self._object_path(deal_id, filename)
        path.write_bytes(fileobj.read())
        return f"gs://{self.bucket_name}/{deal_id}/{filename}"

    def get_local_path(self, deal_id: str, filename: str) -> Path:
        path = self._object_path(deal_id, filename)
        if not path.exists():
            raise FileNotFoundError(f"Object {filename} for deal {deal_id} not found")
        return path

    def delete_folder(self, deal_id: str) -> None:
        deal_dir = self.base_dir / deal_id
        if deal_dir.exists():
            shutil.rmtree(deal_dir)

