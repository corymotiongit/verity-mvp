"""
Verity Charts - Router.

API endpoints for chart operations.
"""

from typing import Union
from uuid import UUID

from fastapi import APIRouter, Depends

from verity.auth import User, get_current_user
from verity.deps import require_charts
from verity.modules.charts.schemas import (
    ChartGenerateRequest,
    ChartGenerateResponse,
    ChartListResponse,
    ChartResponse,
)
from verity.modules.charts.service import ChartsService
from verity.schemas import PaginationMeta

router = APIRouter(
    prefix="/charts",
    tags=["charts"],
    dependencies=[require_charts],
)


def get_service() -> ChartsService:
    """Get charts service instance."""
    return ChartsService()


@router.post(
    "/generate",
    response_model=Union[ChartGenerateResponse, ChartResponse],
    responses={
        200: {"model": ChartGenerateResponse, "description": "Generated (not saved)"},
        201: {"model": ChartResponse, "description": "Generated and saved"},
    },
)
async def generate_chart(
    request: ChartGenerateRequest,
    user: User = Depends(get_current_user),
    service: ChartsService = Depends(get_service),
):
    """
    Generate a chart spec from data.

    Does NOT persist by default. Set save=true to persist.
    Returns 200 if not saved, 201 if saved.
    """
    result = await service.generate_chart(request, user)

    # FastAPI handles the response model based on return type
    return result


@router.get("/{chart_id}", response_model=ChartResponse)
async def get_chart(
    chart_id: UUID,
    user: User = Depends(get_current_user),
    service: ChartsService = Depends(get_service),
):
    """Get a saved chart."""
    return await service.get_chart(chart_id)


@router.delete("/{chart_id}", status_code=204)
async def delete_chart(
    chart_id: UUID,
    user: User = Depends(get_current_user),
    service: ChartsService = Depends(get_service),
):
    """Delete a saved chart."""
    await service.delete_chart(chart_id)


@router.get("", response_model=ChartListResponse)
async def list_charts(
    page_size: int = 20,
    page_token: str | None = None,
    user: User = Depends(get_current_user),
    service: ChartsService = Depends(get_service),
):
    """List saved charts."""
    items, next_token, total = await service.list_charts(user, page_size, page_token)
    return ChartListResponse(
        items=items,
        meta=PaginationMeta(
            total_count=total,
            page_size=page_size,
            next_page_token=next_token,
            has_more=next_token is not None,
        ),
    )
