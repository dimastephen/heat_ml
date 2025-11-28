import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, JSON, Float, func, PrimaryKeyConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class ForecastStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ForecastJob(Base):
    __tablename__ = "forecast_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ForecastStatus.pending.value, index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    artifact_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True, onupdate=func.now()
    )


class ForecastSeries(Base):
    __tablename__ = "forecast_series"
    __table_args__ = (
        PrimaryKeyConstraint("job_id", "timestamp", name="forecast_series_pkey"),
        Index("ix_forecast_series_job_id", "job_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)


class ForecastHouseSeries(Base):
    __tablename__ = "forecast_house_series"
    __table_args__ = (
        PrimaryKeyConstraint("job_id", "house_id", "timestamp", name="forecast_house_series_pkey"),
        Index("ix_forecast_house_series_house", "house_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    house_id: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
