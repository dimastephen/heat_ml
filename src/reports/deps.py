from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_pg_db
from src.reports.repository import IDataQualityReportRepository, DataQualityReportRepository
from src.reports.models import DataQualityReport
from src.reports.service import IReportService, ReportService
from src.files.repository import IIngestionBatchRepository
from src.files.deps import get_batch_repo
from src.reports.forecast_service import ForecastReportService
from src.forecasts.repository import (
    IForecastJobRepository,
    IForecastSeriesRepository,
    IForecastHouseSeriesRepository,
)
from src.forecasts.deps import (
    get_forecast_job_repo,
    get_forecast_series_repo,
    get_forecast_house_series_repo,
)


def get_report_repo(db: Session = Depends(get_pg_db)) -> IDataQualityReportRepository:
    return DataQualityReportRepository(db, DataQualityReport)


def get_report_service(
    repo: IDataQualityReportRepository = Depends(get_report_repo),
    batch_repo: IIngestionBatchRepository = Depends(get_batch_repo),
) -> IReportService:
    return ReportService(repo, batch_repo)


def get_forecast_report_service(
    job_repo: IForecastJobRepository = Depends(get_forecast_job_repo),
    series_repo: IForecastSeriesRepository = Depends(get_forecast_series_repo),
    house_repo: IForecastHouseSeriesRepository = Depends(get_forecast_house_series_repo),
) -> ForecastReportService:
    return ForecastReportService(job_repo, series_repo, house_repo)
