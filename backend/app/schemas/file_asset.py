from __future__ import annotations

from pydantic import BaseModel


class FileUploadOut(BaseModel):
    file_url: str
    file_key: str
    storage: str
    original_filename: str
    content_type: str | None = None
    size_bytes: int
