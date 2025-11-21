from typing import Optional, List
from uuid import UUID

from sqlalchemy import select

from src.database import BaseRepository, SQLAlchemyRepository
from src.files.models import FileUpload, IngestionBatch


class IFileUploadRepository(BaseRepository[FileUpload]):
    def get(self, id: UUID) -> Optional[FileUpload]: ...
    def create(self, obj: dict) -> FileUpload: ...
    def update(self, db_obj: FileUpload, obj_in: dict) -> FileUpload: ...
    def delete(self, id: UUID) -> None: ...

    def list_uploads(self, limit: int = 50, offset: int = 0, *, user_id: Optional[int] = None) -> List[FileUpload]: ...
    def list_by_batch(self, batch_id: UUID) -> List[FileUpload]: ...
    def get_by_batch_and_type(self, batch_id: UUID, file_type: str) -> Optional[FileUpload]: ...
    def get_for_user(self, upload_id: UUID, user_id: int) -> Optional[FileUpload]: ...


class FileUploadRepository(SQLAlchemyRepository[FileUpload], IFileUploadRepository):
    def list_uploads(self, limit: int = 50, offset: int = 0, *, user_id: Optional[int] = None) -> List[FileUpload]:
        stmt = select(FileUpload)
        if user_id is not None:
            stmt = stmt.where(FileUpload.user_id == user_id)
        stmt = stmt.limit(limit).offset(offset)
        return self.db.scalars(stmt).all()

    def list_by_batch(self, batch_id: UUID) -> List[FileUpload]:
        stmt = select(FileUpload).where(FileUpload.batch_id == batch_id)
        return self.db.scalars(stmt).all()

    def get_by_batch_and_type(self, batch_id: UUID, file_type: str) -> Optional[FileUpload]:
        stmt = select(FileUpload).where(
            FileUpload.batch_id == batch_id,
            FileUpload.file_type == file_type,
        )
        return self.db.scalars(stmt).first()

    def get_for_user(self, upload_id: UUID, user_id: int) -> Optional[FileUpload]:
        stmt = select(FileUpload).where(
            FileUpload.id == upload_id,
            FileUpload.user_id == user_id,
        )
        return self.db.scalars(stmt).first()


class IIngestionBatchRepository(BaseRepository[IngestionBatch]):
    def get(self, id: UUID) -> Optional[IngestionBatch]: ...
    def create(self, obj: dict) -> IngestionBatch: ...
    def update(self, db_obj: IngestionBatch, obj_in: dict) -> IngestionBatch: ...
    def delete(self, id: UUID) -> None: ...

    def list_batches(self, limit: int = 50, offset: int = 0, *, user_id: Optional[int] = None) -> List[IngestionBatch]: ...
    def get_for_user(self, batch_id: UUID, user_id: int) -> Optional[IngestionBatch]: ...


class IngestionBatchRepository(SQLAlchemyRepository[IngestionBatch], IIngestionBatchRepository):
    def list_batches(self, limit: int = 50, offset: int = 0, *, user_id: Optional[int] = None) -> List[IngestionBatch]:
        stmt = select(IngestionBatch)
        if user_id is not None:
            stmt = stmt.where(IngestionBatch.user_id == user_id)
        stmt = stmt.limit(limit).offset(offset)
        return self.db.scalars(stmt).all()

    def get_for_user(self, batch_id: UUID, user_id: int) -> Optional[IngestionBatch]:
        stmt = select(IngestionBatch).where(
            IngestionBatch.id == batch_id,
            IngestionBatch.user_id == user_id,
        )
        return self.db.scalars(stmt).first()
