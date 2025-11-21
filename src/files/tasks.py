import logging
import shutil
import pandas as pd
import numpy as np
from pathlib import Path
from uuid import UUID

from redis import Redis
from rq import Queue

from src.config import settings
from src.database import PgSessionLocal
from src.files.models import (
    FileUpload,
    IngestionBatch,
    FileType,
    BatchStatus,
    REQUIRED_FILE_TYPES,
)
from src.files.repository import FileUploadRepository, IngestionBatchRepository

logger = logging.getLogger(__name__)

redis_conn = Redis.from_url(settings.REDIS_URL)
merge_queue = Queue("datasets", connection=redis_conn)


def process_upload(upload_id: UUID):
    """
    Валидация и подготовка отдельного файла (houses/consumption/temperature).
    """
    db = PgSessionLocal()
    file_repo = FileUploadRepository(db, FileUpload)
    batch_repo = IngestionBatchRepository(db, IngestionBatch)

    upload = file_repo.get(upload_id)
    if not upload:
        logger.error("Upload not found", extra={"upload_id": str(upload_id)})
        db.close()
        return

    try:
        file_repo.update(upload, {"status": "processing"})
        prepared_path = _process_file(upload)
        file_repo.update(upload, {
            "status": "validated",
            "prepared_path": str(prepared_path),
            "errors": [],
        })
        logger.info("Upload processed", extra={"upload_id": str(upload_id), "file_type": upload.file_type})
        _maybe_schedule_merge(batch_repo, file_repo, upload.batch_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Upload processing failed", extra={"upload_id": str(upload_id)})
        file_repo.update(upload, {
            "status": "failed",
            "errors": [{"code": "processing_error", "msg": str(exc)}],
        })
        batch = batch_repo.get(upload.batch_id)
        if batch:
            batch_repo.update(batch, {
                "status": BatchStatus.failed.value,
                "errors": [{"code": "file_processing_failed", "msg": str(exc)}],
            })
    finally:
        db.close()


def merge_batch(batch_id: UUID):
    """
    Объединение трёх подготовленных файлов в единый датасет (заглушка).
    """
    db = PgSessionLocal()
    file_repo = FileUploadRepository(db, FileUpload)
    batch_repo = IngestionBatchRepository(db, IngestionBatch)

    batch = batch_repo.get(batch_id)
    if not batch:
        logger.error("Batch not found", extra={"batch_id": str(batch_id)})
        db.close()
        return

    try:
        batch_repo.update(batch, {"status": BatchStatus.processing.value})

        uploads = {u.file_type: u for u in file_repo.list_by_batch(batch_id)}
        houses_path = Path(uploads[FileType.house_features.value].prepared_path)
        consumption_path = Path(uploads[FileType.consumption.value].prepared_path)
        temperature_path = Path(uploads[FileType.temperature.value].prepared_path)

        temp_data = pd.read_csv(temperature_path, sep=';', decimal='.')
        heat_data = pd.read_csv(consumption_path, sep=';', decimal='.')
        home_chars = pd.read_csv(houses_path, sep=';',decimal='.')
        merged_data = pd.merge(heat_data, temp_data, on='date', how='left')
        final_data = pd.merge(merged_data, home_chars, on='address_uuid', how='left')
        final_data.index = final_data['date']
        final_data = final_data.drop(columns='date')
        if "is_unreliable" in final_data.columns:
            final_data = final_data.drop(columns='is_unreliable')
        prepared_dir = _prepared_dir(batch_id)
        prepared_dir.mkdir(parents=True, exist_ok=True)
        output_path = prepared_dir / "prepared_dataset.csv"

        final_data.to_csv(output_path, index=False)
        batch_repo.update(batch, {
            "status": BatchStatus.prepared.value,
            "prepared_path": str(output_path),
            "errors": [],
        })
        logger.info("Batch merged", extra={"batch_id": str(batch_id)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Batch merge failed", extra={"batch_id": str(batch_id)})
        batch_repo.update(batch, {
            "status": BatchStatus.failed.value,
            "errors": [{"code": "merge_error", "msg": str(exc)}],
        })
    finally:
        db.close()


def _process_file(upload: FileUpload) -> Path:
    raw_path = Path(upload.storage_path)
    prepared_dir = _prepared_dir(upload.batch_id)
    prepared_dir.mkdir(parents=True, exist_ok=True)

    if upload.file_type == FileType.house_features.value:
        destination = prepared_dir / "house_features_prepared.csv"
        data=pd.read_csv(raw_path, sep=';', decimal='.')
        data.to_csv(destination, index=False, sep=";", decimal='.')
    elif upload.file_type == FileType.consumption.value:
        destination = prepared_dir / "consumption_prepared.csv"
        data = pd.read_csv(raw_path,sep=';',decimal='.')
        data.loc[data['is_unreliable'] == 1, 'value'] = np.nan
        data['value'] = data.groupby('address_uuid')['value'].transform(lambda x: x.interpolate(method='linear'))
        data.to_csv(destination, index=False,sep=";",decimal='.')
    elif upload.file_type == FileType.temperature.value:
        destination = prepared_dir / "temperature_prepared.csv"
        data = pd.read_csv(raw_path,decimal=',',sep=";")
        data['date_start'] = pd.to_datetime(data['date_start'], errors='coerce')
        data['temp'] = pd.to_numeric(data['temp'], errors='coerce')
        data['humidity'] = pd.to_numeric(data['humidity'], errors='coerce')
        data['date'] = data['date_start'].dt.date
        daily_data = data.groupby('date').agg(
            temp_avg=('temp', 'mean'),
            humidity_avg=('humidity', 'mean')
        ).reset_index()
        daily_data['date'] = pd.to_datetime(daily_data['date'], errors='coerce')
        daily_data.to_csv(destination, index=False, sep=";", decimal='.')
    else:
        raise ValueError(f"Unknown file type {upload.file_type}")

    return destination


def _maybe_schedule_merge(
    batch_repo: IngestionBatchRepository,
    file_repo: FileUploadRepository,
    batch_id: UUID,
) -> None:
    batch = batch_repo.get(batch_id)
    if not batch:
        return
    uploads = file_repo.list_by_batch(batch_id)
    validated_types = {upload.file_type for upload in uploads if upload.status == "validated"}
    required_types = {ft.value for ft in REQUIRED_FILE_TYPES}
    if required_types.issubset(validated_types):
        if batch.status in (BatchStatus.processing.value, BatchStatus.prepared.value):
            return
        batch_repo.update(batch, {"status": BatchStatus.ready.value})
        merge_queue.enqueue(merge_batch, batch_id)


def _prepared_dir(batch_id: UUID) -> Path:
    root = Path(settings.FILE_PREPARED_PATH)
    return root / str(batch_id)
