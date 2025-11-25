from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_pg_db
from src.forecasts.repository import (
    IForecastJobRepository,
    ForecastJobRepository,
    IForecastSeriesRepository,
    ForecastSeriesRepository,
)
from src.forecasts.models import ForecastJob, ForecastSeries
from src.forecasts.service import IForecastService, ForecastService
from src.files.repository import IIngestionBatchRepository
from src.files.deps import get_batch_repo


def get_forecast_job_repo(db: Session = Depends(get_pg_db)) -> IForecastJobRepository:
    return ForecastJobRepository(db, ForecastJob)


def get_forecast_series_repo(db: Session = Depends(get_pg_db)) -> IForecastSeriesRepository:
    return ForecastSeriesRepository(db, ForecastSeries)


def get_forecast_service(
    job_repo: IForecastJobRepository = Depends(get_forecast_job_repo),
    series_repo: IForecastSeriesRepository = Depends(get_forecast_series_repo),
    batch_repo: IIngestionBatchRepository = Depends(get_batch_repo),
) -> IForecastService:
    return ForecastService(job_repo, series_repo, batch_repo)
