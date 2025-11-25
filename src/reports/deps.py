from fastapi import Depends
from sqlalchemy.orm import Session

from src.database import get_pg_db
from src.reports.repository import IDataQualityReportRepository, DataQualityReportRepository
from src.reports.models import DataQualityReport
from src.reports.service import IReportService, ReportService
from src.files.repository import IIngestionBatchRepository
from src.files.deps import get_batch_repo


def get_report_repo(db: Session = Depends(get_pg_db)) -> IDataQualityReportRepository:
    return DataQualityReportRepository(db, DataQualityReport)


def get_report_service(
    repo: IDataQualityReportRepository = Depends(get_report_repo),
    batch_repo: IIngestionBatchRepository = Depends(get_batch_repo),
) -> IReportService:
    return ReportService(repo, batch_repo)
