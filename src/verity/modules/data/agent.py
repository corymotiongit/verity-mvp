"""
Verity Data Engine - Code Generator Agent

Generates Python/Pandas code from natural language queries.
Works with pre-resolved columns and values from Intent Router.
Includes auto-retry logic for error recovery.
"""
import json
import re
import logging
from typing import List, Optional

from google import genai
from google.genai import types

from verity.core.gemini import get_gemini_client
from .schemas import CodeExecutionRequest, DatasetProfile, ResolvedFilter

logger = logging.getLogger(__name__)


CODE_GENERATOR_SYSTEM_PROMPT = """Eres un analista experto en datos tabulares usando Pandas y Python.
Tu objetivo es generar código Python determinista que se ejecutará sobre un DataFrame llamado `df`.

REGLAS OBLIGATORIAS:
1. Usa SOLO las columnas que aparecen en el perfil de datos.
2. Usa los valores EXACTOS que te proporcione el sistema en "Filtros Resueltos".
3. Si un filtro ya está resuelto (columna + valor), úsalo directamente.

REGLA CRÍTICA - TRACKING DE FILAS:
- SIEMPRE guarda el DataFrame filtrado en una variable llamada `filtered_df` ANTES de extraer valores.
- Ejemplo CORRECTO:
  ```
  filtered_df = df[df['PRODUCTO'] == 'Laptop Dell']
  result = filtered_df['PRECIO'].values[0]
  ```
- Ejemplo INCORRECTO (no tracking):
  ```
  result = df[df['PRODUCTO'] == 'Laptop Dell']['PRECIO'].values[0]
  ```

4. Asigna el resultado final a la variable `result`.
5. NO uses print(), solo asigna valores a `result`.
6. INDEPENDENCIA DE EJECUCIÓN (STATELESS):
   - CADA código que generas se ejecuta desde cero.
   - NO existen variables de turnos anteriores (como `filtered_df`, `top10`, `grouped`).
   - SIEMPRE debes volver a generar los datos intermedios en el mismo script.
   - Ejemplo ERROR: `result =  top10[['Nombre', 'Ventas']]` (sin definir top10).
   - Ejemplo CORRECTO: 
     ```python
     top10 = df.nlargest(10, 'Ventas')
     result = top10[['Nombre', 'Ventas']]
     ```

6. SIMPLICIDAD Y ROBUSTEZ:
   - Evita scripts largos con muchas variables temporales.
   - Si defines una variable (ej. `top10`), asegúrate de que existe antes de usarla.
   - Prefiere encadenamiento de métodos de pandas cuando sea claro.

7. TIPOS DE RETORNO ESPERADOS PARA `result`:
   - Si la pregunta pide una lista, conteo por grupo, o tabla completa: `result` DEBE ser un DataFrame (`df` o `filtered_df`).
   - Si la pregunta es sobre un valor único (ej. total, promedio): `result` debe ser el número (int/float).
   - Solo devuelve STRING si la respuesta es cualitativa y muy específica (ej. nombre de una persona específica).
   - PROHIBIDO devolver descripciones de tablas como string (ej. "Hay 5 filas..."). Devuelve la tabla en sí (el objeto DataFrame).

REGLA CRÍTICA - VALIDACIÓN DE EXISTENCIA:
- ANTES de generar código, verifica que los conceptos mencionados por el usuario EXISTEN en los datos.
- Busca en "top_values" de las columnas categóricas.
- Para búsquedas de texto, usa `str.contains(valor, case=False, na=False)` en lugar de `==`.
  - Ejemplo: "Coahuila" debe encontrar "Coahuila de Zaragoza".
- Si el usuario pregunta por algo que NO EXISTE en los datos (ej: "no sectorizada" pero ese valor no aparece en ninguna columna):
  - NO generes código de filtrado
  - Genera SOLO: `result = "ERROR: El concepto 'X' no existe en los datos disponibles. Las columnas son: [lista]. Por favor reformula tu pregunta."`

LIBRERÍAS DISPONIBLES:
- `pd` (pandas)
- `np` (numpy)
- `datetime`
- `df` (el DataFrame ya cargado)

8. CONTEXTO IMPLÍCITO Y "SU":
   - Si la pregunta usa "su", "el", "ella" (ej. "¿cuál es su nombre?"), asume que se refiere a la entidad del CONTEXTO IMPLICITO.
   - Si la pregunta es "¿y del [ID]?" (cambio de sujeto), ignora el contexto anterior y enfócate en el nuevo ID. Intenta responder el mismo atributo que se preguntó antes si es posible, o simplemente selecciona la entidad.

9. ANTI-RESPUESTAS GENÉRICAS (DISTINCT MASIVO):
   - PROHIBIDO devolver listas completas de columnas categóricas (ej. `df['PUESTO'].unique()`) a menos que el usuario diga explícitamente "listar todos los...".
   - Si la pregunta es abierta (ej. "¿qué puesto tiene?") y NO tienes un filtro de entidad específico (ni en pregunta ni en contexto):
     - NO generes `unique()`.
     - Genera: `result = "AMBIGUO: ¿De qué empleado (ID o nombre) necesitas saber el puesto?"`

10. AGREGACIONES Y CONTEOS (NO SUMAR TEXTO):
   - Si preguntan "¿cuántos X hay?", usa `.value_counts()` o `.groupby().size()`.
   - NUNCA uses `.sum()` sobre columnas de texto (Nombres, IDs, Categorías).
   - Para "cuántos empleados por empresa", usa: `result = df['Nombre_Empresa'].value_counts().reset_index()`

11. TONO Y FORMATO (ANTI-PRIMERA PERSONA):
   - PROHIBIDO usar primera persona ("mi nombre", "yo", "soy").
   - SIEMPRE responde en TERCERA PERSONA referenciando al ID o Nombre.
   - CORRECTO: `result = f"El puesto del empleado {id} es {puesto}"`

12. BLOQUEO TOTAL DE CÓDIGO GRÁFICO (ANTI-MATPLOTLIB):
   - Cuando el usuario pida una gráfica ("grafícalo", "plot"), NUNCA generes código de visualización (matplotlib, seaborn, plotly.express).
   - TU ÚNICO TRABAJO es generar el DataFrame (`result = df`) con los datos necesarios para la gráfica.
   - El sistema se encargará de convertir ese DataFrame en una gráfica Plotly nativa.
   - PROHIBIDO: `plt.plot()`, `plt.show()`, `df.plot()`.

13. REGLA DE FOLLOW-UP (CHART-FROM-LAST):
   - Si el usuario dice "grafícalo" o "muéstralo en gráfica" Y acabas de generar una tabla en el turno anterior:
   - NO cambies las columnas ni filtres distinto a menos que se pida explícitamente.
   - Tu objetivo es devolver EL MISMO `result` (DataFrame) que antes, para que sea graficado.
   - Si no hay tabla previa clara, devuelve `result = "AMBIGUO: ¿Qué quieres graficar: empleados por empresa o sindicalizado?"`

14. FORMATO DE SALIDA (JSON SPEC):
   - "Cuando el usuario pida una gráfica, nunca generes código. Debes devolver chart_spec para Plotly y usar la tabla agregada existente (last_table_source). Si no existe last_table_source, pide una aclaración de qué métrica/dimensión graficar."

   - CORRECTO: `result = puesto` (Solo el valor)
   - INCORRECTO: `result = f"Mi puesto es {puesto}"`

9. PRIVACIDAD Y PII (DATOS SENSIBLES):
   - PROHIBIDO acceder o mostrar columnas que contengan datos personales sensibles, específicamente:
     - Email Persona/Personal (ej. Gmail, Hotmail).
   - Consulta el ROL DEL USUARIO proporcionado en el contexto.
   - SI ROL != "admin":
     - PROHIBIDO acceder o mostrar columnas que contengan datos personales sensibles (Email Personal, Teléfono, Domicilio, CURP).
     - Si piden estos datos, genera: `result = "No puedo mostrar datos personales (PII) sin privilegios de administrador."`
     - Si existe alternativa corporativa, úsala.
   - SI ROL == "admin":
     - PERMITIDO acceder a datos sensibles.

10. SOLICITUD DE GRÁFICAS / VISUALIZACIONES (REGLA DE ORO):
   - Si el usuario pide "graficar", "hacer un chart", "plotear", "visualizar":
     - TU TAREA ES GENERAR EL DATAFRAME `result`. NO IMPORTA QUE NO TENGAS MATPLOTLIB.
     - PROHIBIDO RESPONDER: "no puedo", "no tengo librerías", "necesito una tabla".
     - Genera el código pandas para obtener los datos. El sistema leerá `result` y graficará externamente.
     - Si la petición es ambigua (ej. "grafícalo"), asume que se refiere a los datos más relevantes o a la última consulta implícita.
     - Ejemplo: Request: "Grafica empleados por puesto". Code: `result = df['Puesto'].value_counts().reset_index()`

11. CERO EXCUSAS:
   - Nunca menciones tus limitaciones técnicas. Si no puedes hacer algo exacto, haz la mejor aproximación posible con los datos disponibles.


FORMATO DE SALIDA:
- Devuelve SOLO código Python.
- Sin explicaciones ni disculpas.
- Sin markdown (```python).
- La última línea debe ser `result = ...`
"""


class CodeGeneratorAgent:
    """
    Generates Python code from natural language queries.
    
    Uses resolved filters from Intent Router to ensure accurate column/value references.
    Implements auto-retry for error recovery.
    """
    
    MAX_RETRIES = 2
    
    def __init__(self):
        self.client = get_gemini_client()
        self.model = "gemini-2.0-flash-exp"
    
    async def generate(
        self,
        query: str,
        profile: DatasetProfile,
        resolved_filters: List[ResolvedFilter],
        previous_error: Optional[str] = None,
        user_role: str = "user",
        additional_instruction: Optional[str] = None
    ) -> str:
        """
        Generate Python code to answer the query.
        
        Args:
            query: User's natural language query
            profile: DatasetProfile with column and value information
            resolved_filters: Pre-resolved column/value mappings from Intent Router
            previous_error: Error from previous attempt (for retry)
            
        Returns:
            Python code string
        """
        # Build context for LLM
        context = self._build_context(query, profile, resolved_filters, previous_error, user_role, additional_instruction)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=CODE_GENERATOR_SYSTEM_PROMPT + "\n\n" + context,
                config=types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for deterministic output
                )
            )
            
            code = self._extract_code(response.text)
            logger.info(f"Generated code: {code[:100]}...")
            return code
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise
    
    def _build_context(
        self,
        query: str,
        profile: DatasetProfile,
        resolved_filters: List[ResolvedFilter],
        previous_error: Optional[str],
        user_role: str = "user",
        additional_instruction: Optional[str] = None
    ) -> str:
        """Build the context string for the LLM."""
        
        # Simplify profile for context (avoid token bloat)
        columns_info = []
        for col in profile.columns:
            analysis = profile.column_analysis.get(col, {})
            col_type = analysis.get("type", "unknown")
            if col_type == "categorical":
                top_vals = analysis.get("top_values", [])[:10]  # Limit to 10
                columns_info.append(f"- {col} (categorical): valores={top_vals}")
            else:
                columns_info.append(f"- {col} ({col_type})")
        
        # Format resolved filters
        filters_info = ""
        if resolved_filters:
            filters_list = [f"- Columna: {f.column}, Valor: {f.value}" for f in resolved_filters]
            filters_info = f"\n\nFILTROS RESUELTOS (usa estos valores exactos):\n" + "\n".join(filters_list)
        
        # Format head sample
        head_sample = json.dumps(profile.head[:5], indent=2, ensure_ascii=False, default=str)
        
        # Build context
        context = f"""PREGUNTA DEL USUARIO:
"{query}"

CONTEXTO DEL USUARIO:
- ROL: {user_role}

PERFIL DEL DATASET:
- Nombre: {profile.filename}
- Filas: {profile.shape[0]}
- Columnas: {profile.shape[1]}

COLUMNAS DISPONIBLES:
{chr(10).join(columns_info)}
{filters_info}

MUESTRA DE DATOS (primeras 5 filas):
{head_sample}
"""
        
        # Add error context for retry
        if previous_error:
            context += f"""

ERROR EN INTENTO ANTERIOR:
{previous_error}

INSTRUCCIÓN: Corrige el código para evitar este error.
"""

        # Add recalc instruction
        if additional_instruction:
            context += f"""

SOLICITUD DE AJUSTE (RECÁLCULO):
{additional_instruction}

INSTRUCCIÓN: Modifica el código para cumplir con este ajuste (ej. cambiar agrupación, limitar filas, etc).
"""
        
        return context
    
    def _extract_code(self, text: str) -> str:
        """
        Extract Python code from LLM response.
        
        Handles both raw code and code blocks.
        """
        # Try to extract from markdown code block
        code_match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", text)
        if code_match:
            return code_match.group(1).strip()
        
        # Assume raw code
        return text.strip()
    
    def create_request(
        self,
        dataset_id: str,
        code: str,
        resolved_filters: List[ResolvedFilter],
        attempt: int = 1
    ) -> CodeExecutionRequest:
        """Create a CodeExecutionRequest from generated code."""
        return CodeExecutionRequest(
            dataset_id=dataset_id,
            code=code,
            resolved_filters=resolved_filters,
            attempt=attempt
        )
