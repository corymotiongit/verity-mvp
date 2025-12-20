# Verity - Arquitectura Modular para un Data Analyst Impecable (v1)

Documento unico, completo y definitivo.
Disenado para refactor total, limpieza y crecimiento sin rupturas.
Integra diagnostico, decisiones, arquitectura, agentes, tools, addons, checkpoints, semantica, data dictionary y flujo final.

Fecha: 2025-12-20
Version: 1.1 (con mejoras de implementacion)

---

## 1. Contexto y problema real

### 1.1 El problema NO es el modelo

Gemini, GPT, Claude o modelos locales no fallan por capacidad, fallan porque:

- No entienden tablas
- No entienden columnas
- No entienden metricas
- No entienden semantica de negocio
- Solo ven strings

Ejemplos reales:
- rat_songs_pp
- olist_orders_dataset

Para un LLM eso no significa nada.

Resultado:
- SQL correcto
- Grafica bonita
- Insight incorrecto

Esto ocurre tanto en Verity actual como en LuminAI.

---

## 2. Diagnostico de por que se rompe todo

- Arquitectura monolitica
- Agentes con demasiada autonomia
- LLM decidiendo:
  - metricas
  - columnas
  - visualizaciones
- Falta de contratos duros
- Falta de checkpoints
- Falta de semantica explicita

Conclusion: Agregar features rompe cosas existentes.

---

## 3. Decision fundamental

### Nos quedamos con el agente?

Si, pero redefinido completamente.

- NO agente autonomo
- NO proceso vivo
- NO memoria global
- NO ejecucion de logica
- SI Agent = Policy + permisos

El agente no hace cosas.
Las cosas las hacen las tools.

---

## 4. Que NO vamos a hacer (reglas duras)

- LangGraph
- Planner / Verifier con libre albedrio
- Agentes que se llamen entre si
- LLM ejecutando logica
- LLM inventando metricas
- LLM recomendando graficas
- Parsing de JSON con regex
- Enviar schemas gigantes al modelo

---

## 5. Que SI vamos a hacer

- Tool Layer obligatoria
- Data Dictionary
- Semantic Resolver
- Tools deterministas
- Addons desacoplados (tipo microservicios)
- Checkpoints inmutables
- LLM limitado a:
  - resolver intencion
  - explicar resultados

---

## 6. Definiciones claras (sin ambiguedad)

### 6.1 Agent

Configuracion declarativa.

```json
{
  "agent": "data_analyst",
  "allowed_tools": [
    "resolve_semantics",
    "run_table_query",
    "build_chart",
    "compute_forecast"
  ],
  "addons_enabled": ["forecast"]
}
```

El agente:
- No ejecuta
- No decide datos
- No tiene estado
- Solo autoriza

Implementacion - Enforcement de permisos:

```python
class AgentPolicy:
    def __init__(self, config: dict):
        self.agent_id = config["agent"]
        self.allowed_tools = set(config["allowed_tools"])
        self.addons_enabled = set(config.get("addons_enabled", []))
    
    def can_execute(self, tool_name: str) -> bool:
        base_name = tool_name.split("@")[0]
        return base_name in self.allowed_tools
    
    def validate_or_raise(self, tool_name: str) -> None:
        if not self.can_execute(tool_name):
            raise PermissionError(
                f"Agent '{self.agent_id}' cannot execute tool '{tool_name}'"
            )
```

El Tool Executor llama policy.validate_or_raise(tool_name) antes de ejecutar.

### 6.2 Tool

Unidad minima de ejecucion.

Propiedades:
- Determinista
- Versionada
- Input schema
- Output schema
- Testeable
- Sin dependencias implicitas

Ejemplos:
- resolve_semantics@1.0
- run_table_query@1.1
- build_chart@2.0
- compute_forecast@1.0

### 6.3 Addon

Paquete opcional de tools.

- No modifica el core
- Se registra por manifest
- Puede vivir en otro servicio (Cloud Run)

Ejemplos:
- forecast_addon
- ocr_pdf_addon
- cohort_analysis_addon

### 6.4 Core

El core no debe romperse nunca.

El core:
- NO sabe de forecasting
- NO sabe de OCR
- NO sabe de charts especiales
- NO sabe de negocio

---

## 7. Core Components (estables)

```
src/verity/
  __init__.py
  config.py
  exceptions.py
  
  core/
    __init__.py
    intent_resolver.py
    agent_policy.py
    tool_registry.py
    tool_executor.py
    checkpoint_logger.py
    response_composer.py
    schema_validator.py
  
  tools/
    __init__.py
    base.py                    # ToolDefinition, BaseTool
    resolve_semantics.py
    run_table_query.py
    build_chart.py
  
  data/
    __init__.py
    dictionary.py              # DataDictionary class
    schemas/                   # JSON schemas por tabla
      orders.json
      customers.json
  
  addons/
    __init__.py
    forecast/
      __init__.py
      manifest.json
      tools/
        compute_forecast.py
  
  api/
    __init__.py
    routes/
      chat.py
      documents.py
```

---

## 8. Flujo inmutable del sistema

```
User Input
    |
Intent Resolver (LLM)
    |
Agent Policy
    |
Tool Registry
    |
Tool Executor
    |
Checkpoint Logger
    |
Response Composer (LLM)
```

Si este flujo no cambia, nada se rompe.

---

## 9. Intent Resolver

Usa LLM ligero. Solo clasifica intencion. NO ejecuta tools.

Taxonomia cerrada de intents:

```python
class Intent(Enum):
    QUERY_DATA = "query_data"           # SELECT sobre tablas
    AGGREGATE_METRICS = "aggregate"     # GROUP BY, sumas, promedios
    COMPARE_PERIODS = "compare"         # YoY, MoM, WoW
    FORECAST = "forecast"               # Prediccion (requiere addon)
    EXPLAIN_DATA = "explain"            # Solo texto, sin query
    UNKNOWN = "unknown"                 # Fallback explicito
```

El LLM clasifica en uno de estos. Si no encaja, retorna UNKNOWN y pide clarificacion.

Salida:

```json
{
  "intent": "aggregate",
  "confidence": 0.92,
  "needs": ["data", "chart"]
}
```

---

## 10. Tool Registry

Registro central de tools.

Cada tool declara:
- nombre
- version
- schema
- si es determinista
- local o remoto

El core no sabe como se ejecuta.

Implementacion:

```python
@dataclass
class ToolDefinition:
    name: str
    version: str
    input_schema: dict          # JSON Schema
    output_schema: dict         # JSON Schema
    is_deterministic: bool
    execution_mode: Literal["local", "http", "grpc"]
    endpoint: Optional[str]     # Solo si es remoto
    timeout_ms: int = 30000

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}
    
    def register(self, tool: ToolDefinition) -> None:
        key = f"{tool.name}@{tool.version}"
        if key in self._tools:
            raise ValueError(f"Tool {key} already registered")
        self._tools[key] = tool
    
    def get(self, name: str, version: str) -> ToolDefinition:
        key = f"{name}@{version}"
        if key not in self._tools:
            raise KeyError(f"Tool {key} not found")
        return self._tools[key]
    
    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
```

---

## 11. Schema Validator

- Valida inputs
- Valida outputs
- Bloquea ejecuciones invalidas

---

## 12. Tool Executor

Ejecuta tools via:
- funcion local
- HTTP
- gRPC

Maneja timeouts y errores.

El core no se acopla.

---

## 13. Checkpoint Logger (pieza clave)

Cada tool genera un checkpoint inmutable:

```json
{
  "checkpoint_id": "uuid",
  "conversation_id": "c123",
  "tool": "run_table_query@1.1",
  "input": {},
  "output": {},
  "status": "ok",
  "timestamp": "ISO-8601"
}
```

Usos:
- Steps Panel
- Debug
- Auditoria
- Re-ejecucion
- Comparar modelos

Implementacion con storage pluggable:

```python
from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import datetime
from typing import Literal

class CheckpointStorage(ABC):
    @abstractmethod
    def save(self, checkpoint: dict) -> None:
        pass
    
    @abstractmethod
    def query(self, conversation_id: str) -> list[dict]:
        pass

class CheckpointLogger:
    def __init__(self, storage: CheckpointStorage):
        self._storage = storage
    
    def log(
        self,
        conversation_id: str,
        tool: str,
        input_data: dict,
        output_data: dict,
        status: Literal["ok", "error", "timeout"]
    ) -> str:
        checkpoint = {
            "checkpoint_id": str(uuid4()),
            "conversation_id": conversation_id,
            "tool": tool,
            "input": input_data,
            "output": output_data,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._storage.save(checkpoint)
        return checkpoint["checkpoint_id"]
    
    def get_by_conversation(self, conversation_id: str) -> list[dict]:
        return self._storage.query(conversation_id=conversation_id)
```

Storage puede ser:
- JSONFileStorage (dev)
- SQLiteStorage (local)
- PostgresStorage (prod)
- BigQueryStorage (analytics)

---

## 14. Response Composer

Usa LLM.

Recibe:
- checkpoints
- tablas
- reglas de estilo

NO decide datos. NO ejecuta logica. Solo explica.

Prompt template estricto:

```python
RESPONSE_COMPOSER_PROMPT = '''
Eres un asistente de datos. Tu trabajo es explicar resultados, NO inventar.

REGLAS:
1. Solo menciona datos que aparecen en los checkpoints
2. No hagas recomendaciones de negocio
3. No sugieras queries adicionales
4. Si hay error, explica el error sin inventar causas
5. Responde en el idioma del usuario

CHECKPOINTS:
{checkpoints_json}

PREGUNTA ORIGINAL:
{user_question}

RESPUESTA (solo explicacion de los datos):
'''
```

---

## 15. Data Dictionary (critico)

Los LLM no entienden datos sin semantica.

Cada tabla debe tener metadata explicita.

```json
{
  "table": "orders",
  "version": "2.1",
  "deprecated": false,
  "description": "Ordenes realizadas en la plataforma",
  "grain": "1 row = 1 order",
  "primary_key": "order_id",
  "time_column": "order_date",
  "columns": {
    "order_id": "Identificador unico de la orden",
    "customer_id": "Cliente que realizo la orden",
    "order_status": "Estado de la orden",
    "order_total": "Monto total de la orden"
  },
  "metrics": {
    "repeat_customers": {
      "description": "Clientes con mas de una orden",
      "sql": "COUNT(DISTINCT customer_id) FILTER (WHERE order_count > 1)",
      "requires": ["customer_id"],
      "aliases": ["clientes recurrentes", "returning customers", "clientes que regresan"]
    },
    "total_revenue": {
      "description": "Suma de ingresos",
      "sql": "SUM(order_total)",
      "requires": ["order_total"],
      "aliases": ["ventas totales", "ingresos", "revenue"]
    }
  },
  "business_notes": [
    "Solo ordenes delivered cuentan como ventas",
    "Un cliente con mas de una orden es recurrente"
  ],
  "changelog": [
    {"version": "2.1", "date": "2025-12-01", "change": "Added order_source column"},
    {"version": "2.0", "date": "2025-10-15", "change": "Renamed total to order_total"}
  ]
}
```

NO lo inventa el LLM. Se define una vez. Se reutiliza siempre.

El Semantic Resolver hace fuzzy match contra aliases. No inventa metricas.

---

## 16. Semantic Resolver

Tool determinista (o semi-determinista).

Convierte pregunta a intencion de datos usando el Data Dictionary.

```json
{
  "tables": ["orders"],
  "metrics": ["repeat_customers", "total_customers"],
  "time_grain": "month",
  "filters": ["order_status = delivered"]
}
```

El LLM:
- No elige columnas
- No inventa metricas

El Semantic Resolver:
- Busca en Data Dictionary
- Hace fuzzy match contra aliases
- Si no encuentra, retorna error (no inventa)

---

## 17. Data Analyst - flujo completo

```
User
  |
Intent Resolver
  |
Agent Policy
  |
Semantic Resolver (tool)
  |
Data Engine (tool)
  |
(Optional) Forecast Addon
  |
Chart Tool
  |
Response Composer
```

---

## 18. Data Engine

Tool: run_table_query

- Pandas / SQL
- Determinista

Salida:

```json
{
  "table_id": "t_001",
  "columns": ["month", "repeat_customers", "total_customers"],
  "rows": []
}
```

---

## 19. Forecast (Addon)

Tool: compute_forecast

- Vive fuera del core
- Si falla, no rompe nada

---

## 20. Charts (no creativos)

Tool: build_chart

```json
{
  "chart_kind": "line",
  "x": "month",
  "y": ["repeat_customers", "total_customers"]
}
```

- NO recomienda visualizacion
- NO agrega series
- Traduce datos a spec

---

## 21. Addons como microservicios

Ejemplo: forecast_addon

```
addons/forecast/
  tools/
    compute_forecast.py
    schema.json
  adapter.py
  manifest.json
```

manifest.json:

```json
{
  "addon": "forecast",
  "version": "1.0",
  "tools": ["compute_forecast"],
  "requires": ["run_table_query"]
}
```

---

## 22. Por que esta arquitectura no se rompe

- No hay estado compartido implicito
- No hay agentes autonomos
- No hay decisiones creativas sobre datos
- Todo pasa por schemas y checkpoints

---

## 23. Error Handling

Taxonomia de errores:

```python
class VerityError(Exception):
    """Base para todos los errores de Verity"""
    pass

class IntentNotRecognized(VerityError):
    """El Intent Resolver no pudo clasificar"""
    pass

class SemanticMatchFailed(VerityError):
    """No se encontro metrica/tabla en el Data Dictionary"""
    pass

class ToolExecutionFailed(VerityError):
    """La tool fallo durante ejecucion"""
    def __init__(self, tool: str, reason: str):
        self.tool = tool
        self.reason = reason
        super().__init__(f"Tool {tool} failed: {reason}")

class AddonUnavailable(VerityError):
    """El addon no respondio o no esta habilitado"""
    pass
```

Fallbacks:
- IntentNotRecognized: Pedir clarificacion al usuario
- SemanticMatchFailed: Mostrar metricas disponibles
- ToolExecutionFailed: Loggear checkpoint con status error, mostrar mensaje
- AddonUnavailable: Continuar sin addon, avisar al usuario

---

## 24. Testing Strategy

Tres niveles:

### Unit Tests

Cada tool en aislamiento:

```python
def test_run_table_query_returns_valid_schema():
    result = run_table_query({"table": "orders", "columns": ["order_id"]})
    assert "rows" in result
    assert "columns" in result
```

### Integration Tests

Flujo completo con mocks:

```python
def test_full_flow_query_to_response():
    # Mock LLM responses
    # Execute full pipeline
    # Assert checkpoints created
    # Assert response contains expected data
```

### Contract Tests

Validar schemas:

```python
def test_tool_output_matches_schema():
    result = run_table_query({})
    jsonschema.validate(result, RUN_TABLE_QUERY_OUTPUT_SCHEMA)
```

---

## 25. Regla de oro

- El agente no hace cosas
- Las tools hacen TODO
- Los addons solo agregan tools
- El core no cambia
- El LLM explica, no ejecuta

---

## 26. Checklist para implementacion

- [ ] Congelar agentes actuales
- [ ] Eliminar logica ejecutiva del LLM
- [ ] Crear Tool Registry con clase concreta
- [ ] Implementar Checkpoint Logger con storage pluggable
- [ ] Definir Data Dictionary v1 con metrics map
- [ ] Implementar Semantic Resolver con fuzzy match
- [ ] Extraer Forecast como addon
- [ ] Reducir Agent a policy-only con enforcement
- [ ] Limitar LLM a intencion + explicacion
- [ ] Definir Intent enum cerrado
- [ ] Implementar Error taxonomy
- [ ] Crear tests unitarios para cada tool
- [ ] Crear tests de integracion para flujo completo

---

## 27. Conclusion

Si, nos quedamos con el agente, pero:
- Solo como policy
- Nunca como ente autonomo

Esta arquitectura:
- No se rompe
- Escala
- Es mantenible
- Es vendible
- Evita repetir errores de Verity actual y LuminAI

Este documento es la base oficial para el refactor de Verity.
