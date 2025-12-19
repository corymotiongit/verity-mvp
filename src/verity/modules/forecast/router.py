"""
Verity Forecast - Router.

API endpoints for forecasting.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from verity.auth import User, get_current_user
from verity.deps import require_forecast
from verity.modules.forecast.schemas import ForecastRequest, ForecastResponse
from verity.modules.forecast.service import ForecastService

router = APIRouter(
    prefix="/forecast",
    tags=["forecast"],
    dependencies=[require_forecast],
)


def get_service() -> ForecastService:
    """Get forecast service instance."""
    return ForecastService()


@router.post("", response_model=ForecastResponse)
async def generate_forecast(
    request: ForecastRequest,
    user: User = Depends(get_current_user),
    service: ForecastService = Depends(get_service),
):
    """Generate a forecast for the specified metric."""
    return await service.generate_forecast(request, user)


@router.get("/{forecast_id}", response_model=ForecastResponse)
async def get_forecast(
    forecast_id: UUID,
    user: User = Depends(get_current_user),
    service: ForecastService = Depends(get_service),
):
    """Get a forecast by ID."""
    return await service.get_forecast(forecast_id)
