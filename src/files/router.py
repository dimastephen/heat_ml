from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Query

from src.files.schemas import (
    FileUploadRead,
    FileUploadList,
    BatchCreate,
    BatchRead,
    BatchList,
)
from src.files.models import FileType
from src.files.service import IFileService
from src.files.deps import get_file_service
from src.users.schemas import UserRead
from src.users.deps import get_current_user

files_router = APIRouter(prefix="/files", tags=["Files"])


@files_router.post("/datasets", response_model=BatchRead, status_code=201)
def create_dataset(
    payload: BatchCreate,
    current_user: UserRead = Depends(get_current_user),
    service: IFileService = Depends(get_file_service),
):
    return service.create_batch(payload, current_user.id)


@files_router.get("/datasets", response_model=BatchList)
def list_datasets(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserRead = Depends(get_current_user),
    service: IFileService = Depends(get_file_service),
):
    items = service.list_batches(current_user.id, limit=limit, offset=offset)
    return BatchList(items=items)


@files_router.get("/datasets/{batch_id}", response_model=BatchRead)
def get_dataset(
    batch_id: UUID,
    current_user: UserRead = Depends(get_current_user),
    service: IFileService = Depends(get_file_service),
):
    return service.get_batch(batch_id, current_user.id)


@files_router.post(
    "/datasets/{batch_id}/upload/{file_type}",
    response_model=FileUploadRead,
    status_code=201,
)
def upload_dataset_file(
    batch_id: UUID,
    file_type: FileType,
    file: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user),
    service: IFileService = Depends(get_file_service),
):
    return service.upload_file(batch_id, file_type, file, current_user.id)


@files_router.get("/uploads/{upload_id}", response_model=FileUploadRead)
def get_upload(
    upload_id: UUID,
    current_user: UserRead = Depends(get_current_user),
    service: IFileService = Depends(get_file_service),
):
    return service.get_upload(upload_id, current_user.id)


@files_router.get("/uploads", response_model=FileUploadList)
def list_uploads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserRead = Depends(get_current_user),
    service: IFileService = Depends(get_file_service),
):
    items = service.list_uploads(current_user.id, limit=limit, offset=offset)
    return FileUploadList(items=items)
