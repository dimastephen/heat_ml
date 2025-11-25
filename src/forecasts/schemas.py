from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, Field

from src.forecasts.models import ForecastStatus


class ForecastCreate(BaseModel):
    batch_id: UUID
    params: dict[str, Any] | None = None


class ForecastRead(BaseModel):
    id: UUID
    batch_id: UUID
    user_id: int
    status: ForecastStatus
    params: dict[str, Any]
    metrics: dict[str, Any]
    errors: list | None = None
    artifact_path: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ForecastList(BaseModel):
    items: list[ForecastRead]


class ForecastSeriesPoint(BaseModel):
    timestamp: datetime
    value: float


class ForecastSeriesResponse(BaseModel):
    job_id: UUID
    points: list[ForecastSeriesPoint] = Field(default_factory=list)
