import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from redis import Redis
from rq import Queue

from src.config import settings
from src.core.errors import ValidationError, NotFoundError
from src.files.repository import IFileUploadRepository
from src.files.schemas import FileUploadRead
from src.files import tasks


redis_conn = Redis.from_url(settings.REDIS_URL)
rq_queue = Queue("files", connection=redis_conn)


class IFileService(ABC):
    @abstractmethod
    def upload_file(self, file: UploadFile) -> FileUploadRead:
        raise NotImplementedError

    @abstractmethod
    def get_upload(self, upload_id: uuid.UUID) -> Optional[FileUploadRead]:
        raise NotImplementedError

    @abstractmethod
    def list_uploads(self, limit: int = 50, offset: int = 0) -> list[FileUploadRead]:
        raise NotImplementedError


class FileService(IFileService):
    def __init__(self, repo: IFileUploadRepository):
        self.repo = repo

    def upload_file(self, file: UploadFile) -> FileUploadRead:
        if not file.filename.lower().endswith(".csv"):
            raise ValidationError("Only CSV files are supported", code="invalid_file_type")

        storage_root = Path(settings.FILE_STORAGE_PATH)
        storage_root.mkdir(parents=True, exist_ok=True)

        upload_id = uuid.uuid4()
        upload_dir = storage_root / str(upload_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        raw_path = upload_dir / file.filename
        size_bytes = self._save_file_to_disk(file, raw_path)
        if size_bytes == 0:
            raise ValidationError("Uploaded file is empty", code="empty_file")

        db_obj = self.repo.create({
            "id": upload_id,
            "filename": file.filename,
            "size_bytes": size_bytes,
            "status": "pending",
            "storage_path": str(raw_path),
            "prepared_path": None,
        })

        rq_queue.enqueue(tasks.process_upload, upload_id, str(raw_path))

        return FileUploadRead.model_validate(db_obj)

    def get_upload(self, upload_id: uuid.UUID) -> Optional[FileUploadRead]:
        db_obj = self.repo.get(upload_id)
        if not db_obj:
            raise NotFoundError("Upload not found")
        return FileUploadRead.model_validate(db_obj)

    def list_uploads(self, limit: int = 50, offset: int = 0) -> list[FileUploadRead]:
        uploads = self.repo.list(limit=limit, offset=offset)
        return [FileUploadRead.model_validate(u) for u in uploads]

    @staticmethod
    def _save_file_to_disk(file: UploadFile, destination: Path) -> int:
        size = 0
        with destination.open("wb") as f:
            for chunk in iter(lambda: file.file.read(8192), b""):
                size += len(chunk)
                f.write(chunk)
        file.file.close()
        return size
