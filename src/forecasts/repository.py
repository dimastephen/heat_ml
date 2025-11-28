from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, desc

from src.database import BaseRepository, SQLAlchemyRepository
from src.forecasts.models import ForecastJob, ForecastSeries, ForecastHouseSeries


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


class IForecastHouseSeriesRepository(BaseRepository[ForecastHouseSeries]):
    def bulk_create(self, points: list[dict]) -> None: ...
    def list_points(self, job_id: UUID, house_id: str, limit: int = 500) -> List[ForecastHouseSeries]: ...
    def list_house_summaries(self, job_id: UUID) -> list[dict]: ...


class ForecastHouseSeriesRepository(SQLAlchemyRepository[ForecastHouseSeries], IForecastHouseSeriesRepository):
    def bulk_create(self, points: list[dict]) -> None:
        instances = [ForecastHouseSeries(**point) for point in points]
        self.db.add_all(instances)
        self.db.commit()

    def list_points(self, job_id: UUID, house_id: str, limit: int = 500) -> List[ForecastHouseSeries]:
        stmt = (
            select(ForecastHouseSeries)
            .where(
                ForecastHouseSeries.job_id == job_id,
                ForecastHouseSeries.house_id == house_id,
            )
            .order_by(ForecastHouseSeries.timestamp)
            .limit(limit)
        )
        return self.db.scalars(stmt).all()

    def list_house_summaries(self, job_id: UUID) -> list[dict]:
        stmt = (
            select(
                ForecastHouseSeries.house_id,
                func.min(ForecastHouseSeries.timestamp).label("date_start"),
                func.max(ForecastHouseSeries.timestamp).label("date_end"),
                func.sum(ForecastHouseSeries.value).label("total"),
                func.avg(ForecastHouseSeries.value).label("avg"),
                func.max(ForecastHouseSeries.value).label("peak"),
            )
            .where(ForecastHouseSeries.job_id == job_id)
            .group_by(ForecastHouseSeries.house_id)
            .order_by(desc("total"))
        )
        rows = self.db.execute(stmt).all()
        return [dict(row._mapping) for row in rows]
