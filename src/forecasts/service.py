import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from redis import Redis
from rq import Queue

from src.config import settings
from src.core.errors import ValidationError, NotFoundError
from src.files.repository import IIngestionBatchRepository
from src.forecasts.models import ForecastJob, ForecastStatus
from src.forecasts.repository import IForecastJobRepository, IForecastSeriesRepository
from src.forecasts.schemas import ForecastCreate, ForecastRead, ForecastList, ForecastSeriesResponse, ForecastSeriesPoint
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


class ForecastService(IForecastService):
    def __init__(
        self,
        job_repo: IForecastJobRepository,
        series_repo: IForecastSeriesRepository,
        batch_repo: IIngestionBatchRepository,
    ):
        self.job_repo = job_repo
        self.series_repo = series_repo
        self.batch_repo = batch_repo

    def create_job(self, payload: ForecastCreate, user_id: int) -> ForecastRead:
        batch = self.batch_repo.get_for_user(payload.batch_id, user_id)
        if not batch:
            raise NotFoundError("Dataset not found")
        if not batch.prepared_path:
            raise ValidationError("Dataset is not prepared", code="dataset_not_ready")
        job = self.job_repo.create({
            "batch_id": payload.batch_id,
            "user_id": user_id,
            "status": ForecastStatus.pending.value,
            "params": payload.params or {},
        })
        forecast_queue.enqueue(tasks.run_forecast, job.id)
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

    def _get_job_for_user(self, job_id: uuid.UUID, user_id: int) -> ForecastJob:
        job = self.job_repo.get(job_id)
        if not job or job.user_id != user_id:
            raise NotFoundError("Forecast job not found")
        return job
