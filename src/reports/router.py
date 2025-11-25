from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.reports.schemas import DataQualityReportRead, DataQualityReportList
from src.reports.service import IReportService
from src.reports.deps import get_report_service
from src.users.deps import get_current_user
from src.users.schemas import UserRead

reports_router = APIRouter(prefix="/reports", tags=["Reports"])


@reports_router.get("", response_model=DataQualityReportList)
def list_reports(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserRead = Depends(get_current_user),
    service: IReportService = Depends(get_report_service),
):
    return service.list_reports(current_user.id, limit=limit, offset=offset)


@reports_router.get("/datasets/{batch_id}", response_model=DataQualityReportRead)
def get_report_by_batch(
    batch_id: UUID,
    current_user: UserRead = Depends(get_current_user),
    service: IReportService = Depends(get_report_service),
):
    return service.get_by_batch(batch_id, current_user.id)
