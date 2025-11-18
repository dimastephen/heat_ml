from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_pg_db
from src.files.repository import IFileUploadRepository, FileUploadRepository
from src.files.service import IFileService, FileService
from src.files.models import FileUpload


def get_file_repo(db: Session = Depends(get_pg_db)) -> IFileUploadRepository:
    return FileUploadRepository(db, FileUpload)


def get_file_service(repo: IFileUploadRepository = Depends(get_file_repo)) -> IFileService:
    return FileService(repo)
