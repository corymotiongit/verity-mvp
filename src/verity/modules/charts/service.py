"""
Verity Charts - Service.

Business logic for chart generation. Does NOT persist by default.
"""

from typing import Any
from uuid import UUID, uuid4

from verity.auth.schemas import User
from verity.modules.charts.repository import ChartsRepository
from verity.modules.charts.schemas import (
    ChartFormat,
    ChartGenerateRequest,
    ChartGenerateResponse,
    ChartResponse,
    ChartType,
)


class ChartsService:
    """Service for chart operations."""

    def __init__(self, repository: ChartsRepository | None = None):
        self.repository = repository or ChartsRepository()

    async def generate_chart(
        self,
        request: ChartGenerateRequest,
        user: User,
    ) -> ChartGenerateResponse | ChartResponse:
        """
        Generate a chart spec from data.

        Does NOT persist by default. Only saves if save=True.
        """
        # Determine chart type if auto
        chart_type = request.chart_type
        if chart_type == "auto":
            chart_type = self._infer_chart_type(request.data)

        # Generate spec based on format
        if request.format == "vega-lite":
            spec = self._generate_vega_lite_spec(
                request.data, chart_type, request.title
            )
        else:
            spec = self._generate_chartjs_spec(
                request.data, chart_type, request.title
            )

        # Only save if explicitly requested
        if request.save:
            chart_id = uuid4()
            chart_data = {
                "id": str(chart_id),
                "title": request.title,
                "spec": spec,
                "format": request.format,
                "created_by": str(user.id),
            }
            saved = await self.repository.create(chart_data)
            return ChartResponse(
                id=UUID(saved["id"]),
                title=saved.get("title"),
                spec=saved["spec"],
                format=saved["format"],
                created_at=saved["created_at"],
                created_by=UUID(saved["created_by"]),
            )

        return ChartGenerateResponse(
            spec=spec,
            format=request.format,
            saved=False,
        )

    async def get_chart(self, chart_id: UUID) -> ChartResponse:
        """Get a saved chart by ID."""
        chart = await self.repository.get_by_id_or_raise(chart_id)
        return ChartResponse(
            id=UUID(chart["id"]),
            title=chart.get("title"),
            spec=chart["spec"],
            format=chart["format"],
            created_at=chart["created_at"],
            created_by=UUID(chart["created_by"]),
        )

    async def delete_chart(self, chart_id: UUID) -> None:
        """Delete a saved chart."""
        await self.repository.delete(chart_id)

    async def list_charts(
        self,
        user: User,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> tuple[list[ChartResponse], str | None, int]:
        """List saved charts."""
        items, next_token = await self.repository.list(
            page_size=page_size,
            page_token=page_token,
        )

        charts = [
            ChartResponse(
                id=UUID(c["id"]),
                title=c.get("title"),
                spec=c["spec"],
                format=c["format"],
                created_at=c["created_at"],
                created_by=UUID(c["created_by"]),
            )
            for c in items
        ]

        return charts, next_token, len(items)

    def _infer_chart_type(self, data: list[dict[str, Any]]) -> ChartType:
        """Infer best chart type based on data structure."""
        if not data:
            return "bar"

        first_row = data[0]
        keys = list(first_row.keys())

        # Check for time series (date/time field)
        time_fields = ["date", "time", "timestamp", "fecha", "created_at"]
        has_time = any(k.lower() in time_fields for k in keys)
        if has_time:
            return "line"

        # Check for categorical data (few unique string values)
        if len(data) <= 10:
            return "pie" if len(data) <= 6 else "bar"

        return "bar"

    def _generate_vega_lite_spec(
        self, data: list[dict[str, Any]], chart_type: ChartType, title: str | None
    ) -> dict[str, Any]:
        """Generate Vega-Lite specification."""
        if not data:
            return {"$schema": "https://vega.github.io/schema/vega-lite/v5.json"}

        keys = list(data[0].keys())
        x_field = keys[0]
        y_field = keys[1] if len(keys) > 1 else keys[0]

        mark_type_map = {
            "bar": "bar",
            "line": "line",
            "pie": "arc",
            "scatter": "point",
            "area": "area",
        }

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": title or "Chart",
            "data": {"values": data},
            "mark": mark_type_map.get(chart_type, "bar"),
            "encoding": {
                "x": {"field": x_field, "type": "nominal"},
                "y": {"field": y_field, "type": "quantitative"},
            },
        }

        if chart_type == "pie":
            spec["encoding"] = {
                "theta": {"field": y_field, "type": "quantitative"},
                "color": {"field": x_field, "type": "nominal"},
            }

        return spec

    def _generate_chartjs_spec(
        self, data: list[dict[str, Any]], chart_type: ChartType, title: str | None
    ) -> dict[str, Any]:
        """Generate Chart.js specification."""
        if not data:
            return {"type": "bar", "data": {"labels": [], "datasets": []}}

        keys = list(data[0].keys())
        x_field = keys[0]
        y_field = keys[1] if len(keys) > 1 else keys[0]

        labels = [str(row.get(x_field, "")) for row in data]
        values = [row.get(y_field, 0) for row in data]

        chartjs_type_map = {
            "bar": "bar",
            "line": "line",
            "pie": "pie",
            "scatter": "scatter",
            "area": "line",  # Area is line with fill
        }

        return {
            "type": chartjs_type_map.get(chart_type, "bar"),
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": y_field,
                        "data": values,
                        "fill": chart_type == "area",
                    }
                ],
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {
                        "display": bool(title),
                        "text": title or "",
                    }
                },
            },
        }
