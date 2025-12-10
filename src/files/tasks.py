import shutil
import pandas as pd
import numpy as np
from pathlib import Path
from uuid import UUID

from redis import Redis
from rq import Queue
from sklearn.linear_model import LinearRegression
from src.config import settings
from src.database import PgSessionLocal
from src.files.models import (
    FileUpload,
    IngestionBatch,
    FileType,
    BatchStatus,
    REQUIRED_FILE_TYPES,
)
from src.core.logger import logger
from src.files.repository import FileUploadRepository, IngestionBatchRepository
from src.reports.models import DataQualityReport
from src.reports.repository import DataQualityReportRepository
from src.reports.quality import build_quality_metrics


redis_conn = Redis.from_url(settings.REDIS_URL)
merge_queue = Queue("datasets", connection=redis_conn)


def process_upload(upload_id: UUID):
    db = PgSessionLocal()
    file_repo = FileUploadRepository(db, FileUpload)
    batch_repo = IngestionBatchRepository(db, IngestionBatch)
    report_repo = DataQualityReportRepository(db, DataQualityReport)

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
    except Exception as exc:
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
    Объединение трёх подготовленных файлов.
    """

    db = PgSessionLocal()
    file_repo = FileUploadRepository(db, FileUpload)
    batch_repo = IngestionBatchRepository(db, IngestionBatch)
    report_repo = DataQualityReportRepository(db, DataQualityReport)

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
        data = pd.merge(merged_data, home_chars, on='address_uuid', how='left')
        data['date'] = pd.to_datetime(data['date'], errors='coerce')
        data = data.sort_values(['address_uuid', 'date'])

        data['heating_year'] = data['date'].dt.year
        data.loc[data['date'].dt.month < 10, 'heating_year'] -= 1

        season_start = pd.to_datetime(data['heating_year'].astype(str) + '-10-01',errors='coerce')

        data['day_of_season'] = (data['date'] - season_start).dt.days + 1
        data['day_sin'] = np.sin(2 * np.pi * data['day_of_season'] / 212)
        data['day_cos'] = np.cos(2 * np.pi * data['day_of_season'] / 212)
        static_num = ['build_year', 'floor_number', 'residential_area', 'roof_area_total', 'roof_area_metal',
                      'roof_area_web', 'roof_area_piece_goods']
        static_str = ['wall_type']
        data[static_num] = data[static_num].fillna(-1)
        data[static_str] = data[static_str].fillna('unknown')
        data.interpolate(method='linear', limit_direction='both', inplace=True)

        data = IQR_check(data)

        quality_metrics = build_quality_metrics(data)
        existing_report = report_repo.get_by_batch(batch_id)
        report_payload = {
            "batch_id": batch.id,
            "user_id": batch.user_id,
            "metrics": quality_metrics,
        }
        if existing_report:
            report_repo.update(existing_report, report_payload)
        else:
            report_repo.create(report_payload)

        if 'is_anomaly' in data.columns:
            data = data.drop(columns=['is_anomaly'])

        prepared_dir = _prepared_dir(batch_id)
        prepared_dir.mkdir(parents=True, exist_ok=True)
        output_path = prepared_dir / "prepared_dataset.csv"

        data.to_csv(output_path, index=False)
        batch_repo.update(batch, {
            "status": BatchStatus.prepared.value,
            "prepared_path": str(output_path),
            "errors": [],
        })
        logger.info("Batch merged", extra={"batch_id": str(batch_id)})
    except Exception as exc:
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
        if 'is_unreliable' in data.columns:
            data.loc[data['is_unreliable'] == 1, 'value'] = np.nan
            data = data.drop(columns=['is_unreliable'])
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


def get_heating_day(row):
    year_start = pd.Timestamp(f'{row.year}-10-01')

    if row < year_start:
        year_start = pd.Timestamp(f'{row.year - 1}-10-01')

    return (row - year_start).days + 1


def IQR_check(data: pd.DataFrame) -> pd.DataFrame:
    value_series = data['value'].dropna()
    if value_series.empty:
        return data

    Q1 = value_series.quantile(0.25)
    Q3 = value_series.quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR

    data['is_anomaly'] = ((data['value'] < lower_bound) | (data['value'] > upper_bound) | (data['value'] < 0))

    normal_data = data[~data['is_anomaly']].dropna(subset=['temp_avg', 'humidity_avg', 'value'])
    outlier_data = data[data['is_anomaly']]

    if len(normal_data) < 10:
        return data

    X_train = normal_data[['temp_avg', 'humidity_avg']]
    y_train = normal_data['value']
    model = LinearRegression()
    model.fit(X_train, y_train)

    X_outliers = outlier_data[['temp_avg', 'humidity_avg']]
    data.loc[data['is_anomaly'], 'value'] = model.predict(X_outliers)
    return data
