from typing import List, Optional
from uuid import UUID

from sqlalchemy import select

from src.database import BaseRepository, SQLAlchemyRepository
from src.reports.models import DataQualityReport


class IDataQualityReportRepository(BaseRepository[DataQualityReport]):
    def list_reports(self, *, user_id: int, limit: int = 50, offset: int = 0) -> List[DataQualityReport]: ...
    def get_by_batch(self, batch_id: UUID) -> Optional[DataQualityReport]: ...


class DataQualityReportRepository(SQLAlchemyRepository[DataQualityReport], IDataQualityReportRepository):
    def list_reports(self, *, user_id: int, limit: int = 50, offset: int = 0) -> List[DataQualityReport]:
        stmt = select(DataQualityReport).where(DataQualityReport.user_id == user_id).limit(limit).offset(offset)
        return self.db.scalars(stmt).all()

    def get_by_batch(self, batch_id: UUID) -> Optional[DataQualityReport]:
        stmt = select(DataQualityReport).where(DataQualityReport.batch_id == batch_id)
        return self.db.scalars(stmt).first()
