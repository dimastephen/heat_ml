import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from redis import Redis
from rq import Queue

from src.config import settings
from src.core.errors import ValidationError, NotFoundError, ConflictError
from src.files.repository import (
    IFileUploadRepository,
    IIngestionBatchRepository,
)
from src.files.schemas import FileUploadRead, BatchRead, BatchCreate
from src.files.models import FileType, BatchStatus, IngestionBatch
from src.files import tasks

redis_conn = Redis.from_url(settings.REDIS_URL)
rq_queue = Queue("files", connection=redis_conn)


class IFileService(ABC):
    @abstractmethod
    def create_batch(self, payload: BatchCreate, user_id: int) -> BatchRead:
        raise NotImplementedError

    @abstractmethod
    def get_batch(self, batch_id: uuid.UUID, user_id: int) -> BatchRead:
        raise NotImplementedError

    @abstractmethod
    def list_batches(self, user_id: int, limit: int = 50, offset: int = 0) -> list[BatchRead]:
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, batch_id: uuid.UUID, file_type: FileType, file: UploadFile, user_id: int) -> FileUploadRead:
        raise NotImplementedError

    @abstractmethod
    def get_upload(self, upload_id: uuid.UUID, user_id: int) -> FileUploadRead:
        raise NotImplementedError

    @abstractmethod
    def list_uploads(self, user_id: int, limit: int = 50, offset: int = 0) -> list[FileUploadRead]:
        raise NotImplementedError


class FileService(IFileService):
    def __init__(self, file_repo: IFileUploadRepository, batch_repo: IIngestionBatchRepository):
        self.file_repo = file_repo
        self.batch_repo = batch_repo

    def create_batch(self, payload: BatchCreate, user_id: int) -> BatchRead:
        batch = self.batch_repo.create({
            "name": payload.name,
            "user_id": user_id,
            "status": BatchStatus.waiting_files.value,
            "errors": [],
        })
        return self._build_batch_read(batch)

    def get_batch(self, batch_id: uuid.UUID, user_id: int) -> BatchRead:
        batch = self._get_batch(batch_id, user_id)
        return self._build_batch_read(batch)

    def list_batches(self, user_id: int, limit: int = 50, offset: int = 0) -> list[BatchRead]:
        batches = self.batch_repo.list_batches(limit=limit, offset=offset, user_id=user_id)
        return [self._build_batch_read(batch) for batch in batches]

    def upload_file(self, batch_id: uuid.UUID, file_type: FileType, file: UploadFile, user_id: int) -> FileUploadRead:
        batch = self._get_batch(batch_id, user_id)

        if not file.filename.lower().endswith(".csv"):
            raise ValidationError("Only CSV files are supported", code="invalid_file_type")

        existing = self.file_repo.get_by_batch_and_type(batch_id, file_type.value)
        if existing:
            raise ConflictError("File for this type already uploaded", code="file_exists")

        storage_root = Path(settings.FILE_STORAGE_PATH) / str(batch_id) / file_type.value
        storage_root.mkdir(parents=True, exist_ok=True)

        upload_id = uuid.uuid4()
        raw_path = storage_root / file.filename
        size_bytes = self._save_file_to_disk(file, raw_path)
        if size_bytes == 0:
            raise ValidationError("Uploaded file is empty", code="empty_file")

        db_obj = self.file_repo.create({
            "id": upload_id,
            "batch_id": batch_id,
            "user_id": user_id,
            "file_type": file_type.value,
            "filename": file.filename,
            "size_bytes": size_bytes,
            "status": "pending",
            "storage_path": str(raw_path),
            "prepared_path": None,
        })

        rq_queue.enqueue(tasks.process_upload, upload_id)

        return FileUploadRead.model_validate(db_obj)

    def get_upload(self, upload_id: uuid.UUID, user_id: int) -> FileUploadRead:
        db_obj = self.file_repo.get_for_user(upload_id, user_id)
        if not db_obj:
            raise NotFoundError("Upload not found")
        return FileUploadRead.model_validate(db_obj)

    def list_uploads(self, user_id: int, limit: int = 50, offset: int = 0) -> list[FileUploadRead]:
        uploads = self.file_repo.list_uploads(limit=limit, offset=offset, user_id=user_id)
        return [FileUploadRead.model_validate(u) for u in uploads]

    def _get_batch(self, batch_id: uuid.UUID, user_id: int) -> IngestionBatch:
        batch = self.batch_repo.get_for_user(batch_id, user_id)
        if not batch:
            raise NotFoundError("Batch not found")
        return batch

    def _build_batch_read(self, batch: IngestionBatch) -> BatchRead:
        files = self.file_repo.list_by_batch(batch.id)
        batch_schema = BatchRead.model_validate(batch)
        batch_schema.files = [FileUploadRead.model_validate(f) for f in files]
        return batch_schema

    @staticmethod
    def _save_file_to_disk(file: UploadFile, destination: Path) -> int:
        size = 0
        with destination.open("wb") as f:
            for chunk in iter(lambda: file.file.read(8192), b""):
                size += len(chunk)
                f.write(chunk)
        file.file.close()
        return size
