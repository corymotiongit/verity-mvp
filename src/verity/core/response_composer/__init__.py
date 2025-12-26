"""
Response Composer - Explicación de resultados usando LLM controlado

Responsabilidad:
- Recibir checkpoints + contexto
- Generar explicación en lenguaje natural
- NO decidir datos
- NO ejecutar lógica
- NO recomendar queries adicionales
- Solo explicar lo que ya se ejecutó

Usa LLM con prompt template estricto.
"""

from typing import Any
from verity.core.checkpoint_logger import Checkpoint


RESPONSE_COMPOSER_PROMPT = '''
Eres un asistente de datos. Tu trabajo es explicar resultados, NO inventar.

REGLAS OBLIGATORIAS:
1. Solo menciona datos que aparecen en los checkpoints
2. No hagas recomendaciones de negocio
3. No sugieras queries adicionales
4. Si hay error, explica el error sin inventar causas
5. Responde en el idioma del usuario
6. Sé conciso y preciso

CHECKPOINTS:
{checkpoints_json}

PREGUNTA ORIGINAL:
{user_question}

INSTRUCCIONES ADICIONALES PARA RANKINGS:
Si el resultado tiene "result_metadata" con "result_type": "ranking":
1. Usa el "limit" real para el título (ej: "Top 5...").
2. Genera una tabla Markdown limpia con columnas: #, [Entidad], [Valor].
3. No trunques la lista arbitrariamente, muestra todas las filas retornadas (hasta el limit).
4. Formatea los números (miles con comas).

RESPUESTA (solo explicación de los datos):
'''


class ResponseComposer:
    """
    Compositor de respuestas usando LLM controlado.
    
    El LLM:
    - NO decide datos
    - NO ejecuta lógica
    - Solo explica resultados ya generados
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.model_name = model_name
    
    async def compose(
        self,
        user_question: str,
        checkpoints: list[Checkpoint],
        additional_context: dict[str, Any] = None
    ) -> str:
        """
        Genera explicación de resultados.
        
        Args:
            user_question: Pregunta original del usuario
            checkpoints: Lista de checkpoints ejecutados
            additional_context: Contexto adicional (opcional)
        
        Returns:
            Respuesta en lenguaje natural
        """
        import google.generativeai as genai
        from verity.config import get_settings
        
        settings = get_settings()
        genai.configure(api_key=settings.gemini.api_key)
        
        # Convertir checkpoints a JSON
        checkpoints_json = self._checkpoints_to_json(checkpoints)
        
        # Construir prompt con template estricto
        prompt = RESPONSE_COMPOSER_PROMPT.format(
            checkpoints_json=checkpoints_json,
            user_question=user_question
        )
        
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            
            return response.text.strip()
        
        except Exception as e:
            # Fallback: retornar resumen básico de checkpoints
            return self._fallback_response(user_question, checkpoints)
    
    def _checkpoints_to_json(self, checkpoints: list[Checkpoint]) -> str:
        """Convierte checkpoints a JSON para el prompt."""
        import json
        from dataclasses import asdict
        
        return json.dumps(
            [asdict(cp) for cp in checkpoints],
            indent=2,
            ensure_ascii=False
        )
    
    def _fallback_response(self, question: str, checkpoints: list[Checkpoint]) -> str:
        """Genera respuesta con valores explícitos sin LLM."""
        if not checkpoints:
            return f"No pude procesar tu pregunta: '{question}'. Intenta reformularla."
        
        # Buscar checkpoint de run_table_query con resultados
        query_checkpoint = None
        for cp in checkpoints:
            if "run_table_query" in cp.tool and cp.status == "ok":
                query_checkpoint = cp
                break
        
        if not query_checkpoint or not query_checkpoint.output:
            last_checkpoint = checkpoints[-1]
            if last_checkpoint.status == "ok":
                return f"Procesé tu pregunta. Se ejecutaron {len(checkpoints)} pasos."
            else:
                return f"Hubo un error al procesar tu pregunta. Revisa los logs para más detalles."
        
        # Extraer resultados del output
        output = query_checkpoint.output
        columns = output.get("columns", [])
        rows = output.get("rows", [])
        result_metadata = output.get("result_metadata", {})
        
        if not rows or not columns:
            return "La consulta se ejecutó pero no retornó resultados."
        
        # =====================================================================
        # Manejo de Rankings (Fallback determinista)
        # =====================================================================
        if result_metadata.get("result_type") == "ranking":
            limit = result_metadata.get("limit", len(rows))
            label_col = result_metadata.get("label_column", columns[0])
            value_col = result_metadata.get("value_column", columns[1] if len(columns) > 1 else columns[0])
            
            # Título
            response = f"Aquí está tu Top {limit} de {self._get_friendly_name(label_col)}:\n\n"
            
            # Tabla Markdown
            response += f"| # | {self._get_friendly_name(label_col)} | {self._get_friendly_name(value_col)} |\n"
            response += "|---|---|---|\n"
            
            for i, row in enumerate(rows[:limit]):
                # Asumimos orden: [label, value] o buscar índices
                label_val = row[0] # Simplificación: asumimos primera columna es label
                value_val = row[1] if len(row) > 1 else "N/A"
                
                # Formatear valor
                formatted_val = self._format_value(value_col, value_val)
                
                response += f"| {i+1} | {label_val} | {formatted_val} |\n"
            
            return response

        # =====================================================================
        # Manejo estándar (una sola fila o lista simple)
        # =====================================================================
        
        # Formatear respuesta con valores
        parts = []
        for i, col in enumerate(columns):
            if i < len(rows[0]):
                value = rows[0][i]
                formatted_value = self._format_value(col, value)
                # Mapear nombre de columna a texto amigable
                friendly_name = self._get_friendly_name(col)
                parts.append(f"**{friendly_name}**: {formatted_value}")
        
        if len(parts) == 1:
            # Respuesta simple para una sola métrica
            metric_name = columns[0]
            value = rows[0][0]
            return self._generate_natural_response(metric_name, value, question)
        
        # Múltiples métricas
        return "Aquí están los resultados:\n" + "\n".join(parts)
    
    def _format_value(self, column: str, value) -> str:
        """Formatea valor según el tipo de métrica."""
        if value is None:
            return "N/A"
        
        col_lower = column.lower()
        
        # Tiempo en horas
        if "listening_time" in col_lower or "horas" in col_lower:
            if isinstance(value, (int, float)):
                hours = value / 3600000 if value > 1000000 else value
                return f"{hours:,.1f} horas"
        
        # Duración promedio en minutos
        if "duration" in col_lower or "duracion" in col_lower:
            if isinstance(value, (int, float)):
                minutes = value / 60000 if value > 1000 else value
                return f"{minutes:,.1f} minutos"
        
        # Números enteros (conteos)
        if isinstance(value, (int, float)):
            if float(value).is_integer():
                return f"{int(value):,}"
            return f"{value:,.2f}"
        
        return str(value)
    
    def _get_friendly_name(self, column: str) -> str:
        """Convierte nombre de columna a texto amigable."""
        mapping = {
            "total_plays": "Reproducciones",
            "unique_tracks": "Canciones únicas",
            "unique_artists": "Artistas únicos",
            "total_listening_time": "Tiempo total",
            "avg_track_duration": "Duración promedio",
            "top_artist": "Artista más escuchado",
            "total_orders": "Total de órdenes",
            "total_revenue": "Ingresos",
            "artist_name": "Artista",
            "track_name": "Canción",
            "count": "Cantidad",
        }
        return mapping.get(column, column.replace("_", " ").title())
    
    def _generate_natural_response(self, metric: str, value, question: str) -> str:
        """Genera respuesta natural para una métrica."""
        formatted = self._format_value(metric, value)
        
        metric_lower = metric.lower()
        
        if "total_plays" in metric_lower:
            return f"Has escuchado **{formatted}** canciones."
        
        if "unique_tracks" in metric_lower:
            return f"Has escuchado **{formatted}** canciones únicas."
        
        if "unique_artists" in metric_lower:
            return f"Has escuchado a **{formatted}** artistas diferentes."
        
        if "listening_time" in metric_lower:
            return f"Has escuchado un total de **{formatted}** de música."
        
        if "avg" in metric_lower and "duration" in metric_lower:
            return f"La duración promedio de las canciones que escuchas es **{formatted}**."
        
        if "top_artist" in metric_lower:
            return f"Tu artista más escuchado es **{formatted}**."
        
        # Fallback genérico
        friendly = self._get_friendly_name(metric)
        return f"{friendly}: **{formatted}**"


__all__ = ["ResponseComposer", "RESPONSE_COMPOSER_PROMPT"]
