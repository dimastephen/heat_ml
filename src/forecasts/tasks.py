import logging
from pathlib import Path
from uuid import UUID

import pandas as pd

from src.config import settings
from src.database import PgSessionLocal
from src.files.repository import IngestionBatchRepository
from src.files.models import IngestionBatch
from src.forecasts.models import ForecastJob, ForecastStatus, ForecastSeries
from src.forecasts.repository import ForecastJobRepository, ForecastSeriesRepository

logger = logging.getLogger(__name__)


def run_forecast(job_id: UUID):
    db = PgSessionLocal()
    job_repo = ForecastJobRepository(db, ForecastJob)
    batch_repo = IngestionBatchRepository(db, IngestionBatch)
    series_repo = ForecastSeriesRepository(db, ForecastSeries)

    job = job_repo.get(job_id)
    if not job:
        logger.error("Forecast job not found", extra={"job_id": str(job_id)})
        db.close()
        return

    batch = batch_repo.get(job.batch_id)
    if not batch or not batch.prepared_path:
        logger.error("Prepared dataset missing", extra={"job_id": str(job_id)})
        job_repo.update(job, {"status": ForecastStatus.failed.value, "errors": [{"msg": "dataset missing"}]})
        db.close()
        return

    try:
        job_repo.update(job, {"status": ForecastStatus.processing.value})
        dataset_path = Path(batch.prepared_path)
        df = pd.read_csv(dataset_path)
        timestamp_col = _detect_column(df, ["date", "timestamp", "datetime"])
        value_col = _detect_column(df, ["forecast", "value", "consumption", "target"])
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df = df.sort_values(timestamp_col)
        df["prediction"] = df[value_col].rolling(window=3, min_periods=1).mean()

        model_dir = Path(settings.MODEL_STORAGE_PATH) / str(job.id)
        model_dir.mkdir(parents=True, exist_ok=True)
        output_path = model_dir / "forecast.csv"
        df[[timestamp_col, "prediction"]].to_csv(output_path, index=False)

        points = [
            {
                "job_id": job.id,
                "timestamp": row[timestamp_col],
                "value": float(row["prediction"]),
            }
            for _, row in df[[timestamp_col, "prediction"]].iterrows()
        ]
        series_repo.bulk_create(points)

        job_repo.update(job, {
            "status": ForecastStatus.completed.value,
            "artifact_path": str(output_path),
            "metrics": {"points": len(points)},
            "errors": [],
        })
        logger.info("Forecast completed", extra={"job_id": str(job.id), "points": len(points)})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Forecast failed", extra={"job_id": str(job_id)})
        job_repo.update(job, {
            "status": ForecastStatus.failed.value,
            "errors": [{"code": "forecast_error", "msg": str(exc)}],
        })
    finally:
        db.close()


def _detect_column(df: pd.DataFrame, candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return df.columns[0]
