from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.database import BaseRepository, SQLAlchemyRepository
from src.files.models import FileUpload


class IFileUploadRepository(BaseRepository[FileUpload]):
    def get(self, id: UUID) -> Optional[FileUpload]: ...
    def create(self, obj: dict) -> FileUpload: ...
    def update(self, db_obj: FileUpload, obj_in: dict) -> FileUpload: ...
    def delete(self, id: UUID) -> None: ...

    def list(self, limit: int = 50, offset: int = 0) -> list[FileUpload]: ...


class FileUploadRepository(SQLAlchemyRepository[FileUpload], IFileUploadRepository):
    def list(self, limit: int = 50, offset: int = 0) -> list[FileUpload]:
        stmt = select(FileUpload).limit(limit).offset(offset)
        return self.db.scalars(stmt).all()
