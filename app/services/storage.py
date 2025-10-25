"""Storage service abstraction backed by Google Cloud Storage."""
from __future__ import annotations

import os
from io import BytesIO
from typing import BinaryIO

from fastapi import UploadFile
from google.api_core.exceptions import NotFound
from google.cloud import storage
from google.oauth2 import service_account


class StorageService:
    """Persist files to Google Cloud Storage."""

    def __init__(self, bucket_name: str) -> None:
        project_id = os.getenv("GCP_PROJECT_ID")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        credentials = None
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(credentials_path)

        client_kwargs = {}
        if project_id:
            client_kwargs["project"] = project_id
        if credentials is not None:
            client_kwargs["credentials"] = credentials

        self.client = storage.Client(**client_kwargs)
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name

    def _blob_path(self, deal_id: str, filename: str) -> str:
        return f"{deal_id}/{filename}"

    def upload_uploadfile(
        self, deal_id: str, upload: UploadFile, *, destination: str | None = None
    ) -> str:
        """Persist an :class:`UploadFile` to storage and return a gs:// URL."""

        target_name = destination or upload.filename or "file"
        blob = self.bucket.blob(self._blob_path(deal_id, target_name))
        upload.file.seek(0)
        blob.upload_from_file(upload.file, content_type=upload.content_type)
        upload.file.seek(0)
        return f"gs://{self.bucket_name}/{deal_id}/{target_name}"

    def upload_bytes(
        self, deal_id: str, filename: str, data: bytes, *, content_type: str | None = None
    ) -> str:
        blob = self.bucket.blob(self._blob_path(deal_id, filename))
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket_name}/{deal_id}/{filename}"

    def upload_fileobj(self, deal_id: str, filename: str, fileobj: BinaryIO) -> str:
        blob = self.bucket.blob(self._blob_path(deal_id, filename))
        fileobj.seek(0)
        blob.upload_from_file(fileobj)
        fileobj.seek(0)
        return f"gs://{self.bucket_name}/{deal_id}/{filename}"

    def download_file(self, deal_id: str, filename: str) -> tuple[BytesIO, str]:
        blob = self.bucket.get_blob(self._blob_path(deal_id, filename))
        if blob is None:
            raise FileNotFoundError(f"Object {filename} for deal {deal_id} not found")
        data = blob.download_as_bytes()
        file_obj = BytesIO(data)
        file_obj.seek(0)
        content_type = blob.content_type or "application/octet-stream"
        return file_obj, content_type

    def delete_file(self, deal_id: str, filename: str) -> None:
        blob = self.bucket.blob(self._blob_path(deal_id, filename))
        try:
            blob.delete()
        except NotFound:
            pass

    def delete_folder(self, deal_id: str) -> None:
        prefix = f"{deal_id}/"
        for blob in self.bucket.list_blobs(prefix=prefix):
            try:
                blob.delete()
            except NotFound:
                continue

