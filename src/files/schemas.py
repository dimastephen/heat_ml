from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class FileUploadRead(BaseModel):
    id: UUID
    filename: str
    size_bytes: int
    status: str
    errors: list | None = None
    storage_path: str
    prepared_path: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class FileUploadList(BaseModel):
    items: list[FileUploadRead]
