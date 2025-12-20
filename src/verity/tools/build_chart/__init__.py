"""
build_chart@2.0 - Construcción de especificaciones de gráficas

Responsabilidad:
- Convertir tabla de datos a spec de gráfica (Plotly/Recharts)
- Usar chart_kind provisto (hard-coded por core según Intent)
- Aplicar formato de ejes según especificación
- NO recomendar visualizaciones
- NO agregar series no solicitadas

Input: table_id + chart_kind + x_axis + y_axes + color_column + format + title
Output: chart_spec + library + chart_id

REGLA CRÍTICA: chart_kind es hard-coded por core, NUNCA decidido por LLM.
Ver schema.json para contrato completo.
"""

from verity.tools.base import BaseTool, ToolDefinition
from typing import Any
import json
from pathlib import Path
from uuid import uuid4

from verity.core.table_store import TABLE_STORE


class BuildChartTool(BaseTool):
    """
    Tool determinista para construir especificaciones de gráficas.
    
    NO usa LLM para decidir tipo de gráfica.
    NO recomienda visualizaciones.
    Solo traduce datos a spec según chart_kind provisto.
    """
    
    @property
    def definition(self) -> ToolDefinition:
        """Carga definición desde schema.json"""
        schema_path = Path(__file__).parent / "schema.json"
        with open(schema_path) as f:
            schema = json.load(f)
        
        return ToolDefinition(
            name="build_chart",
            version="2.0",
            input_schema=schema["input"],
            output_schema=schema["output"],
            is_deterministic=True,
            execution_mode="local"
        )
    
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Construye especificación de gráfica.
        
        TODO:
        1. Recuperar tabla usando table_id
        2. Validar que x_axis y y_axes existen
        3. Mapear chart_kind a spec (Plotly o Recharts)
        4. Aplicar formato de ejes
        5. Generar chart_spec completo
        6. Retornar con chart_id único
        """
        table_id = input_data["table_id"]
        chart_kind = input_data["chart_kind"]
        x_axis = input_data["x_axis"]
        y_axes = input_data.get("y_axes") or []
        color_column = input_data.get("color_column")
        fmt = input_data.get("format") or {}
        title = input_data.get("title") or ""

        table = TABLE_STORE.get(table_id)
        if not table:
            raise ValueError(f"Unknown table_id: {table_id}")

        columns = table.columns
        rows = table.rows

        # Fallback determinista: si el pipeline pasó un x_axis válido pero no hay y_axes
        # (p.ej. tabla agregada de 1 columna), interpretamos x_axis como el valor Y
        # y usamos el índice de fila como eje X.
        use_index_x = False
        if isinstance(y_axes, list) and len(y_axes) == 0:
            use_index_x = True
            y_axes = [x_axis]

        if not use_index_x and x_axis not in columns:
            raise ValueError(f"x_axis '{x_axis}' not found in table columns")
        if not isinstance(y_axes, list) or len(y_axes) == 0:
            raise ValueError("y_axes must be a non-empty list")
        for y in y_axes:
            if y not in columns:
                raise ValueError(f"y_axis '{y}' not found in table columns")
        if color_column and color_column not in columns:
            raise ValueError(f"color_column '{color_column}' not found in table columns")

        col_idx = {c: i for i, c in enumerate(columns)}
        x_vals = list(range(len(rows))) if use_index_x else [r[col_idx[x_axis]] for r in rows]

        def _axis_format(axis: str) -> dict[str, Any]:
            axis_fmt = (fmt.get(axis) or "").lower()
            if axis_fmt == "currency":
                return {"tickprefix": "$", "tickformat": ",.2f"}
            if axis_fmt == "percent":
                return {"tickformat": ".0%"}
            if axis_fmt == "number":
                return {"tickformat": ","}
            if axis_fmt == "date":
                return {"type": "date"}
            return {}

        data: list[dict[str, Any]] = []

        if chart_kind in {"bar", "stacked_bar", "line", "scatter", "area"}:
            plotly_type = "bar" if chart_kind in {"bar", "stacked_bar"} else "scatter"
            default_mode = "lines" if chart_kind in {"line", "area"} else "markers"

            for y in y_axes:
                y_vals = [r[col_idx[y]] for r in rows]
                trace: dict[str, Any] = {
                    "type": plotly_type,
                    "name": y,
                    "x": x_vals,
                    "y": y_vals,
                }
                if plotly_type == "scatter":
                    trace["mode"] = default_mode
                    if chart_kind == "area":
                        trace["fill"] = "tozeroy"
                data.append(trace)

            layout: dict[str, Any] = {
                "title": {"text": title, "x": 0},
                "xaxis": {"title": "index" if use_index_x else x_axis, **_axis_format("x_format")},
                "yaxis": {"title": y_axes[0], **_axis_format("y_format")},
                "margin": {"l": 56, "r": 24, "t": 56, "b": 56},
            }
            if chart_kind == "stacked_bar":
                layout["barmode"] = "stack"

            chart_spec = {"data": data, "layout": layout}

        elif chart_kind == "pie":
            y = y_axes[0]
            values = [r[col_idx[y]] for r in rows]
            labels = x_vals
            chart_spec = {
                "data": [
                    {
                        "type": "pie",
                        "labels": labels,
                        "values": values,
                        "name": y,
                    }
                ],
                "layout": {"title": {"text": title, "x": 0}},
            }
        else:
            raise ValueError(f"Unsupported chart_kind: {chart_kind}")

        return {
            "chart_spec": chart_spec,
            "library": "plotly",
            "chart_id": f"ch_{uuid4().hex[:8]}",
        }


__all__ = ["BuildChartTool"]
