"""
Intent Resolver - Clasificador de intención del usuario

Responsabilidad:
- Recibir pregunta del usuario
- Clasificar en Intent enum (taxonomía cerrada)
- NO ejecutar tools
- NO decidir sobre datos

Input: Pregunta del usuario (string)
Output: Intent + confidence + needs

Usa LLM ligero solo para clasificación.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Literal


class Intent(Enum):
    """Taxonomía cerrada de intenciones."""
    QUERY_DATA = "query_data"           # SELECT sobre tablas
    AGGREGATE_METRICS = "aggregate"     # GROUP BY, sumas, promedios
    COMPARE_PERIODS = "compare"         # YoY, MoM, WoW
    FORECAST = "forecast"               # Predicción (requiere addon)
    EXPLAIN_DATA = "explain"            # Solo texto, sin query
    UNKNOWN = "unknown"                 # Fallback explícito


@dataclass
class IntentResolution:
    """Resultado de la resolución de intención."""
    intent: Intent
    confidence: float  # 0.0 - 1.0
    needs: list[Literal["data", "chart", "forecast"]]
    raw_question: str


class IntentResolver:
    """
    Resuelve intención del usuario usando LLM ligero.
    
    NO ejecuta tools.
    NO toma decisiones sobre datos.
    Solo clasifica.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.model_name = model_name
    
    def resolve(self, question: str) -> IntentResolution:
        """
        Clasifica pregunta del usuario en Intent.
        
        Si no encaja en ninguna categoría, retorna Intent.UNKNOWN
        y solicita clarificación.
        """
        from verity.config import get_settings

        settings = get_settings()

        # Fallback determinista para entornos locales sin API key.
        # Esto permite validar el pipeline v2 (semantic_resolution → run_table_query)
        # sin depender de servicios externos.
        api_key = (settings.gemini.api_key or "").strip()
        if not api_key:
            q = (question or "").lower()

            compare_markers = [
                " vs ",
                " vs.",
                "versus",
                "comparar",
                "comparación",
                "comparacion",
                "contra",
                "yoy",
                "mom",
                "wow",
                "año pasado",
                "ano pasado",
                "year over year",
                "mes pasado",
                "last month",
                "last week",
                "semana pasada",
            ]

            aggregate_markers = [
                "total",
                "suma",
                "sum",
                "promedio",
                "avg",
                "average",
                "count",
                "cuantos",
                "cuántos",
                "cuantas",
                "cuántas",
                "cantidad",
                "ingresos",
                "ventas",
                "revenue",
                "aov",
                "ticket",
                "retention",
                "recurrent",
                "recurrentes",
                "clientes recurrentes",
                "returning",
                # Music-related markers
                "canciones",
                "escuchado",
                "escuchadas",
                "plays",
                "reproducciones",
                "artistas",
                "tracks",
                "horas",
                "tiempo",
                "listening",
                "musica",
                "música",
            ]
            query_markers = [
                "lista",
                "listar",
                "mostrar",
                "ver",
                "detalle",
                "registros",
                "filas",
            ]

            if any(m in q for m in compare_markers):
                return IntentResolution(
                    intent=Intent.COMPARE_PERIODS,
                    confidence=0.6,
                    needs=["data", "chart"],
                    raw_question=question,
                )

            if any(m in q for m in aggregate_markers):
                return IntentResolution(
                    intent=Intent.AGGREGATE_METRICS,
                    confidence=0.6,
                    needs=["data"],
                    raw_question=question,
                )
            if any(m in q for m in query_markers):
                return IntentResolution(
                    intent=Intent.QUERY_DATA,
                    confidence=0.6,
                    needs=["data"],
                    raw_question=question,
                )
            return IntentResolution(
                intent=Intent.UNKNOWN,
                confidence=0.2,
                needs=[],
                raw_question=question,
            )

        import google.generativeai as genai

        genai.configure(api_key=api_key)
        
        # Prompt estricto para clasificación
        prompt = f"""Clasifica esta pregunta del usuario en EXACTAMENTE UNA de estas categorías:

CATEGORÍAS PERMITIDAS:
- QUERY_DATA: El usuario quiere ver datos crudos (SELECT, listar, mostrar)
- AGGREGATE_METRICS: El usuario quiere métricas agregadas (total, promedio, suma, count)
- COMPARE_PERIODS: El usuario quiere comparar períodos de tiempo (vs año pasado, mes vs mes)
- FORECAST: El usuario quiere predicciones futuras (proyección, forecast, predicción)
- EXPLAIN_DATA: El usuario quiere explicación conceptual sin ejecutar queries
- UNKNOWN: No encaja en ninguna categoría anterior

PREGUNTA DEL USUARIO:
"{question}"

RESPONDE EN JSON CON ESTE FORMATO EXACTO:
{{
  "intent": "NOMBRE_DE_CATEGORIA",
  "confidence": 0.XX,
  "needs": ["data", "chart", "forecast"],
  "reasoning": "breve explicación de por qué clasificaste así"
}}

Solo retorna el JSON, nada más."""

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            # Parsear respuesta
            import json
            import re
            
            # Extraer JSON de la respuesta
            text = response.text.strip()
            # Intentar encontrar JSON en la respuesta
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                result = json.loads(text)
            
            # Mapear string a Intent enum
            intent_str = result["intent"]
            intent_mapping = {
                "QUERY_DATA": Intent.QUERY_DATA,
                "AGGREGATE_METRICS": Intent.AGGREGATE_METRICS,
                "COMPARE_PERIODS": Intent.COMPARE_PERIODS,
                "FORECAST": Intent.FORECAST,
                "EXPLAIN_DATA": Intent.EXPLAIN_DATA,
                "UNKNOWN": Intent.UNKNOWN
            }
            
            intent = intent_mapping.get(intent_str, Intent.UNKNOWN)
            confidence = result.get("confidence", 0.5)
            needs = result.get("needs", [])
            
            return IntentResolution(
                intent=intent,
                confidence=confidence,
                needs=needs,
                raw_question=question
            )
        
        except Exception as e:
            # Si falla la clasificación, retornar UNKNOWN
            return IntentResolution(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                needs=[],
                raw_question=question
            )


__all__ = ["Intent", "IntentResolution", "IntentResolver"]
