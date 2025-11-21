from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_pg_db
from src.files.repository import (
    IFileUploadRepository,
    FileUploadRepository,
    IIngestionBatchRepository,
    IngestionBatchRepository,
)
from src.files.service import IFileService, FileService
from src.files.models import FileUpload, IngestionBatch


def get_file_repo(db: Session = Depends(get_pg_db)) -> IFileUploadRepository:
    return FileUploadRepository(db, FileUpload)


def get_batch_repo(db: Session = Depends(get_pg_db)) -> IIngestionBatchRepository:
    return IngestionBatchRepository(db, IngestionBatch)


def get_file_service(
    file_repo: IFileUploadRepository = Depends(get_file_repo),
    batch_repo: IIngestionBatchRepository = Depends(get_batch_repo),
) -> IFileService:
    return FileService(file_repo, batch_repo)
