from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DataQualityReportRead(BaseModel):
    id: UUID
    batch_id: UUID
    user_id: int
    metrics: dict
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class DataQualityReportList(BaseModel):
    items: list[DataQualityReportRead] = Field(default_factory=list)
