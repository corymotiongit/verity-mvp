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
        """Genera respuesta básica sin LLM en caso de error."""
        if not checkpoints:
            return f"No pude procesar tu pregunta: '{question}'. Intenta reformularla."
        
        last_checkpoint = checkpoints[-1]
        
        if last_checkpoint.status == "ok":
            return f"Procesé tu pregunta exitosamente. Se ejecutaron {len(checkpoints)} pasos."
        else:
            return f"Hubo un error al procesar tu pregunta. Revisa los logs para más detalles."


__all__ = ["ResponseComposer", "RESPONSE_COMPOSER_PROMPT"]
