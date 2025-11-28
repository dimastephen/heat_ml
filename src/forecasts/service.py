import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from datetime import datetime, timezone

from redis import Redis
from rq import Queue

from src.config import settings
from src.core.errors import ValidationError, NotFoundError
from src.files.repository import IIngestionBatchRepository
from src.forecasts.models import ForecastJob, ForecastStatus
from src.forecasts.repository import (
    IForecastJobRepository,
    IForecastSeriesRepository,
    IForecastHouseSeriesRepository,
)
from src.forecasts.schemas import (
    ForecastCreate,
    ForecastRead,
    ForecastList,
    ForecastSeriesResponse,
    ForecastSeriesPoint,
    ForecastHouseSummaryList,
    ForecastHouseSummary,
    ForecastHouseSeriesResponse,
)
from src.forecasts import tasks

redis_conn = Redis.from_url(settings.REDIS_URL)
forecast_queue = Queue("forecasts", connection=redis_conn)


class IForecastService(ABC):
    @abstractmethod
    def create_job(self, payload: ForecastCreate, user_id: int) -> ForecastRead:
        raise NotImplementedError

    @abstractmethod
    def list_jobs(self, user_id: int, limit: int = 50, offset: int = 0) -> ForecastList:
        raise NotImplementedError

    @abstractmethod
    def get_job(self, job_id: uuid.UUID, user_id: int) -> ForecastRead:
        raise NotImplementedError

    @abstractmethod
    def get_series(self, job_id: uuid.UUID, user_id: int, limit: int = 500) -> ForecastSeriesResponse:
        raise NotImplementedError

    @abstractmethod
    def list_house_summaries(self, job_id: uuid.UUID, user_id: int) -> ForecastHouseSummaryList:
        raise NotImplementedError

    @abstractmethod
    def get_house_series(self, job_id: uuid.UUID, house_id: str, user_id: int, limit: int = 500) -> ForecastHouseSeriesResponse:
        raise NotImplementedError


class ForecastService(IForecastService):
    def __init__(
        self,
        job_repo: IForecastJobRepository,
        series_repo: IForecastSeriesRepository,
        house_series_repo: IForecastHouseSeriesRepository,
        batch_repo: IIngestionBatchRepository,
    ):
        self.job_repo = job_repo
        self.series_repo = series_repo
        self.house_series_repo = house_series_repo
        self.batch_repo = batch_repo

    def create_job(self, payload: ForecastCreate, user_id: int) -> ForecastRead:
        batch = self.batch_repo.get_for_user(payload.batch_id, user_id)
        if not batch:
            raise NotFoundError("Dataset not found")
        if not batch.prepared_path:
            raise ValidationError("Dataset is not prepared", code="dataset_not_ready")
        now_utc = datetime.now(timezone.utc)
        job = self.job_repo.create({
            "batch_id": payload.batch_id,
            "user_id": user_id,
            "status": ForecastStatus.pending.value,
            "params": payload.params or {},
            "created_at": now_utc,
            "updated_at": now_utc,
        })
        # Без явного ограничения времени задачи (используется глобальный default RQ или бесконечность)
        forecast_queue.enqueue(tasks.run_forecast, job.id, job_timeout=-1)
        return ForecastRead.model_validate(job)

    def list_jobs(self, user_id: int, limit: int = 50, offset: int = 0) -> ForecastList:
        jobs = self.job_repo.list_jobs(user_id=user_id, limit=limit, offset=offset)
        return ForecastList(items=[ForecastRead.model_validate(job) for job in jobs])

    def get_job(self, job_id: uuid.UUID, user_id: int) -> ForecastRead:
        job = self._get_job_for_user(job_id, user_id)
        return ForecastRead.model_validate(job)

    def get_series(self, job_id: uuid.UUID, user_id: int, limit: int = 500) -> ForecastSeriesResponse:
        job = self._get_job_for_user(job_id, user_id)
        points = self.series_repo.list_points(job_id=job.id, limit=limit)
        return ForecastSeriesResponse(
            job_id=job.id,
            points=[ForecastSeriesPoint(timestamp=p.timestamp, value=p.value) for p in points],
        )

    def list_house_summaries(self, job_id: uuid.UUID, user_id: int) -> ForecastHouseSummaryList:
        job = self._get_job_for_user(job_id, user_id)
        rows = self.house_series_repo.list_house_summaries(job.id)
        summaries = [
            ForecastHouseSummary(
                house_id=row["house_id"],
                total=row["total"] or 0.0,
                average=row["avg"] or 0.0,
                peak=row["peak"] or 0.0,
                date_start=row["date_start"],
                date_end=row["date_end"],
            )
            for row in rows
        ]
        return ForecastHouseSummaryList(items=summaries)

    def get_house_series(self, job_id: uuid.UUID, house_id: str, user_id: int, limit: int = 500) -> ForecastHouseSeriesResponse:
        job = self._get_job_for_user(job_id, user_id)
        points = self.house_series_repo.list_points(job.id, house_id, limit=limit)
        return ForecastHouseSeriesResponse(
            job_id=job.id,
            house_id=house_id,
            points=[ForecastSeriesPoint(timestamp=p.timestamp, value=p.value) for p in points],
        )

    def _get_job_for_user(self, job_id: uuid.UUID, user_id: int) -> ForecastJob:
        job = self.job_repo.get(job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError("Forecast job not found")
        return job
