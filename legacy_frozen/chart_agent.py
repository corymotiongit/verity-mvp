raise RuntimeError(
    "LEGACY CODE IS FROZEN - This file has been moved to legacy_frozen/ and must not be imported. "
    "Use tools/build_chart for deterministic chart generation instead. See /src/verity/core/ for new implementation."
)

# The code below is preserved for reference only and will never execute
# ============================================================================

import json
import logging
from typing import Dict, Any, Optional

from google import genai
from google.genai import types
from pydantic import ValidationError

from verity.core.gemini import get_gemini_client
from .schemas import ChartGenerationResponse

logger = logging.getLogger(__name__)

CHART_SYSTEM_PROMPT = """Eres "Chart". Tu trabajo es convertir una tabla ya calculada (agregada) en una especificación de gráfica.
No calculas datos, no inventas valores, no consultas documentos. Solo decides "cómo graficar" y devuelves un ChartSpec.

Input que recibirás siempre:
- question: pregunta del usuario
- table: filas + columnas (ya agregadas por Data Executor)
- table_schema: nombres y tipos de columnas
- evidence_ref: referencia del cálculo (operation, filters, group_by, file/canonical_file_id, row_ids_or_ranges)

Reglas duras:
1. Prohibido inventar datos. Solo puedes usar columnas presentes en table.
2. Si table está vacía o no tiene columnas suficientes, responde needs_recalc=true con instrucción concreta.
3. Si hay demasiadas categorías (default > 20), pide recálculo con top_n=10 y others=true antes de graficar.
4. Debes elegir el tipo de gráfica más legible:
   - bar: comparaciones por categoría
   - line: series temporales (fecha/periodo ordenable)
   - stacked_bar: composición por serie
    - scatter: relación entre dos variables (x numérica, y numérica)
   - heatmap: matriz 2D (cat x cat)
   - treemap: proporciones jerárquicas (solo si hay 2 niveles)

Formato:
- Si y parece dinero (monto, pagado, precio): format=currency y unit si se conoce.
- Si es tasa/porcentaje: format=percent
- Si es conteo: format=number

Output Schema (ChartGenerationResponse):
{
  "needs_recalc": false,
  "recalc_request": null,
  "chart_spec": {
    "version": "1.0",
        "chart_type": "bar|line|stacked_bar|scatter|heatmap|treemap",
    "title": "string",
    "subtitle": "string|null",
    "x": { "field": "col_name", "type": "category|date|number", "label": "string" },
    "y": { "field": "col_name", "type": "number", "label": "string" },
    "series": { "field": "col_name", "type": "category", "label": "string" } | null,
    "sort": { "by": "y|x", "order": "asc|desc" } | null,
    "limits": { "top_n": 10, "others": true } | null,
    "format": { "type": "currency|percent|number", "unit": "MXN|USD|null", "decimals": 0 },
    "tooltips": ["col1","col2","col3"],
    "notes": ["string"]
  }
}

Cuando pedir recálculo (needs_recalc=true):
- Falta columna de métrica (y) o categoría (x)
- x tiene > 20 categorías y no hay limits
- El usuario pide "top" pero la tabla no está recortada
- Piden serie temporal y x no es ordenable (fecha/periodo)

Nota: el renderer Plotly debe graficar EXACTAMENTE table y también mostrar debajo table_source (la misma tabla) y evidence_ref para auditoría.
"""

class ChartAgent:
    """Agent responsible for generating visualization specifications from tabular data."""
    
    def __init__(self):
        self.client = get_gemini_client()
        self.model = "gemini-2.0-flash-exp"

    async def generate_spec(
        self,
        query: str,
        table_data: Dict[str, Any],
        evidence_ref: str
    ) -> ChartGenerationResponse:
        """
        Generate chart specification from data.
        
        Args:
            query: User's original question.
            table_data: Dict with 'columns' (list[str]) and 'rows' (list[list]).
            evidence_ref: String describing how data was generated.
            
        Returns:
            ChartGenerationResponse with spec or recalc request.
        """
        if not table_data or not table_data.get("rows"):
            logger.info("Skipping chart generation: empty table")
            return ChartGenerationResponse(needs_recalc=False)

        # Build context
        context = self._build_context(query, table_data, evidence_ref)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=CHART_SYSTEM_PROMPT + "\n\n" + context,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ChartGenerationResponse,
                    temperature=0.1,
                )
            )
            
            # Parse response
            # Note: With response_schema, the text is guaranteed JSON matching schema
            spec = ChartGenerationResponse.model_validate_json(response.text)
            
            if spec.chart_spec:
                 logger.info(f"Generated chart spec: type={spec.chart_spec.chart_type}, title='{spec.chart_spec.title}'")
            elif spec.needs_recalc:
                 logger.info(f"Chart requests recalc: {spec.recalc_request}")
                 
            return spec

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            # Fail gracefully -> no chart
            return ChartGenerationResponse(needs_recalc=False)

    def _build_context(
        self,
        query: str,
        table_data: Dict[str, Any],
        evidence_ref: str
    ) -> str:
        """Construct prompt context."""
        
        # Prepare table sample/schema
        columns = table_data.get("columns", [])
        rows = table_data.get("rows", [])
        total_rows = table_data.get("total_rows", len(rows))
        
        # We pass full table if small enough, otherwise sample + stats
        # For charts, we ideally want the aggregated table. If it's huge, charts might be bad anyway.
        # But we pass top 20 rows to let agent decide if it needs recalc.
        
        display_rows = rows[:20]
        
        table_json = json.dumps({
            "columns": columns,
            "rows": display_rows,
            "total_rows": total_rows
        }, default=str, ensure_ascii=False)
        
        return f"""INPUT DATA:

question: "{query}"

evidence_ref: "{evidence_ref}"

table_schema: Columns={columns}, Row Count={total_rows}

table:
{table_json}
"""
