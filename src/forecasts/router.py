from uuid import UUID

from fastapi import APIRouter, Depends, Query

from src.forecasts.schemas import (
    ForecastCreate,
    ForecastRead,
    ForecastList,
    ForecastSeriesResponse,
    ForecastHouseSummaryList,
    ForecastHouseSeriesResponse,
)
from src.forecasts.service import IForecastService
from src.forecasts.deps import get_forecast_service
from src.users.schemas import UserRead
from src.users.deps import get_current_user

forecasts_router = APIRouter(prefix="/forecasts", tags=["Forecasts"])


@forecasts_router.post("", response_model=ForecastRead, status_code=201)
def create_forecast(
    payload: ForecastCreate,
    current_user: UserRead = Depends(get_current_user),
    service: IForecastService = Depends(get_forecast_service),
):
    return service.create_job(payload, current_user.id)


@forecasts_router.get("", response_model=ForecastList)
def list_forecasts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserRead = Depends(get_current_user),
    service: IForecastService = Depends(get_forecast_service),
):
    return service.list_jobs(current_user.id, limit=limit, offset=offset)


@forecasts_router.get("/{job_id}", response_model=ForecastRead)
def get_forecast(
    job_id: UUID,
    current_user: UserRead = Depends(get_current_user),
    service: IForecastService = Depends(get_forecast_service),
):
    return service.get_job(job_id, current_user.id)


@forecasts_router.get("/{job_id}/series", response_model=ForecastSeriesResponse)
def get_forecast_series(
    job_id: UUID,
    limit: int = Query(500, ge=1, le=5000),
    current_user: UserRead = Depends(get_current_user),
    service: IForecastService = Depends(get_forecast_service),
):
    return service.get_series(job_id, current_user.id, limit=limit)


@forecasts_router.get("/{job_id}/houses", response_model=ForecastHouseSummaryList)
def list_forecast_houses(
    job_id: UUID,
    current_user: UserRead = Depends(get_current_user),
    service: IForecastService = Depends(get_forecast_service),
):
    return service.list_house_summaries(job_id, current_user.id)


@forecasts_router.get("/{job_id}/houses/{house_id}", response_model=ForecastHouseSeriesResponse)
def get_house_series(
    job_id: UUID,
    house_id: str,
    limit: int = Query(500, ge=1, le=5000),
    current_user: UserRead = Depends(get_current_user),
    service: IForecastService = Depends(get_forecast_service),
):
    return service.get_house_series(job_id, house_id, current_user.id, limit=limit)
