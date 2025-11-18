import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from src.database import PgSessionLocal
from src.files.models import FileUpload
from src.files.repository import FileUploadRepository

logger = logging.getLogger(__name__)


def process_upload(upload_id: UUID, raw_path: str):
    """
    RQ task: validate/prepare uploaded CSV.
    Placeholder: marks file as validated; add real processing/validation here.
    """
    db = PgSessionLocal()
    repo = FileUploadRepository(db, FileUpload)

    db_obj = repo.get(upload_id)
    if not db_obj:
        logger.error("Upload not found", extra={"upload_id": str(upload_id)})
        return

    try:
        repo.update(db_obj, {"status": "processing"})

        # TODO: add real CSV validation/normalization here
        prepared_path = Path(raw_path)  # currently passthrough

        repo.update(db_obj, {
            "status": "validated",
            "prepared_path": str(prepared_path),
            "errors": [],
        })
        logger.info("Upload processed", extra={"upload_id": str(upload_id)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upload processing failed", extra={"upload_id": str(upload_id)})
        repo.update(db_obj, {
            "status": "failed",
            "errors": [{"code": "processing_error", "msg": str(exc)}],
        })
    finally:
        db.close()
