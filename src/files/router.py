from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Query

from src.files.schemas import FileUploadRead, FileUploadList
from src.files.service import IFileService
from src.files.deps import get_file_service

files_router = APIRouter(prefix="/files", tags=["Files"])


@files_router.post("/upload", response_model=FileUploadRead, status_code=201)
def upload_file(
    file: UploadFile = File(...),
    service: IFileService = Depends(get_file_service),
):
    return service.upload_file(file)


@files_router.get("/{upload_id}", response_model=FileUploadRead)
def get_upload(
    upload_id: UUID,
    service: IFileService = Depends(get_file_service),
):
    return service.get_upload(upload_id)


@files_router.get("", response_model=FileUploadList)
def list_uploads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: IFileService = Depends(get_file_service),
):
    items = service.list_uploads(limit=limit, offset=offset)
    return FileUploadList(items=items)
