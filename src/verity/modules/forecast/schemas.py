"""
Verity Forecast - Schemas.

Pydantic models for forecast operations.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DataPoint(BaseModel):
    """Historical data point."""

    date: date
    value: float


class ForecastRequest(BaseModel):
    """Request to generate a forecast."""

    metric: str = Field(..., min_length=1)
    horizon: int = Field(..., ge=1, le=365, description="Days to forecast")
    historical_data: list[DataPoint] | None = Field(
        default=None, min_length=2
    )
    confidence_level: float = Field(default=0.95, ge=0.5, le=0.99)


class Prediction(BaseModel):
    """Single prediction point."""

    date: date
    value: float
    lower_bound: float
    upper_bound: float


class ModelInfo(BaseModel):
    """Model metadata."""

    name: str
    accuracy_score: float | None = None


class ForecastResponse(BaseModel):
    """Forecast response."""

    id: UUID
    metric: str
    predictions: list[Prediction]
    confidence_level: float
    model_info: ModelInfo | None = None
    created_at: datetime
