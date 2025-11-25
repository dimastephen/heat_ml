from typing import Optional, List
from uuid import UUID

from sqlalchemy import select

from src.database import BaseRepository, SQLAlchemyRepository
from src.forecasts.models import ForecastJob, ForecastSeries


class IForecastJobRepository(BaseRepository[ForecastJob]):
    def list_jobs(self, *, user_id: int, limit: int = 50, offset: int = 0) -> list[ForecastJob]: ...


class ForecastJobRepository(SQLAlchemyRepository[ForecastJob], IForecastJobRepository):
    def list_jobs(self, *, user_id: int, limit: int = 50, offset: int = 0) -> list[ForecastJob]:
        stmt = select(ForecastJob).where(ForecastJob.user_id == user_id).limit(limit).offset(offset)
        return self.db.scalars(stmt).all()


class IForecastSeriesRepository(BaseRepository[ForecastSeries]):
    def list_points(self, job_id: UUID, limit: int = 500) -> List[ForecastSeries]: ...
    def bulk_create(self, points: list[dict]) -> None: ...


class ForecastSeriesRepository(SQLAlchemyRepository[ForecastSeries], IForecastSeriesRepository):
    def list_points(self, job_id: UUID, limit: int = 500) -> List[ForecastSeries]:
        stmt = select(ForecastSeries).where(ForecastSeries.job_id == job_id).order_by(ForecastSeries.timestamp).limit(limit)
        return self.db.scalars(stmt).all()

    def bulk_create(self, points: list[dict]) -> None:
        instances = [ForecastSeries(**point) for point in points]
        self.db.add_all(instances)
        self.db.commit()
