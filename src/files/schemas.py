from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.files.models import BatchStatus, FileType


class FileUploadRead(BaseModel):
    id: UUID
    batch_id: UUID
    user_id: int
    file_type: FileType
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


class BatchCreate(BaseModel):
    name: str


class BatchRead(BaseModel):
    id: UUID
    name: str
    user_id: int
    status: BatchStatus
    prepared_path: str | None = None
    errors: list | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    files: list[FileUploadRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class BatchList(BaseModel):
    items: list[BatchRead]
