import uuid
from abc import ABC, abstractmethod

from src.core.errors import NotFoundError
from src.files.repository import IIngestionBatchRepository
from src.reports.models import DataQualityReport
from src.reports.repository import IDataQualityReportRepository
from src.reports.schemas import DataQualityReportRead, DataQualityReportList


class IReportService(ABC):
    @abstractmethod
    def get_by_batch(self, batch_id: uuid.UUID, user_id: int) -> DataQualityReportRead:
        raise NotImplementedError

    @abstractmethod
    def list_reports(self, user_id: int, limit: int = 50, offset: int = 0) -> DataQualityReportList:
        raise NotImplementedError


class ReportService(IReportService):
    def __init__(
        self,
        repo: IDataQualityReportRepository,
        batch_repo: IIngestionBatchRepository,
    ):
        self.repo = repo
        self.batch_repo = batch_repo

    def get_by_batch(self, batch_id: uuid.UUID, user_id: int) -> DataQualityReportRead:
        batch = self.batch_repo.get_for_user(batch_id, user_id)
        if not batch:
            raise NotFoundError("Dataset not found")
        report = self.repo.get_by_batch(batch_id)
        if not report:
            raise NotFoundError("Report not found")
        return DataQualityReportRead.model_validate(report)

    def list_reports(self, user_id: int, limit: int = 50, offset: int = 0) -> DataQualityReportList:
        reports = self.repo.list_reports(user_id=user_id, limit=limit, offset=offset)
        return DataQualityReportList(items=[DataQualityReportRead.model_validate(r) for r in reports])
