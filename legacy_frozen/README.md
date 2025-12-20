# legacy_frozen/

**DEPRECATED - NO USAR EN NUEVA ARQUITECTURA**

Este directorio contiene agentes y prompts congelados de la arquitectura anterior.

**IMPORTANTE**: Este código está FUERA de `src/` intencionalmente. Python no puede importarlo.
Esto previene uso accidental de código legacy en la nueva arquitectura.

## Agentes movidos aquí

### `code_generator_agent.py` (antes `data/agent.py`)
- **Por qué está deprecated**: LLM genera código Python/Pandas ejecutable
- **Violación**: LLM ejecutando lógica de datos
- **Reemplazo**: `tools/resolve_semantics` + `tools/run_table_query` (deterministas)

### `chart_agent.py` (antes `data/charts.py`)
- **Por qué está deprecated**: LLM elige tipo de visualización
- **Violación**: LLM tomando decisiones creativas sobre representación
- **Reemplazo**: `tools/build_chart` (mapeo determinista tabla → chart_spec)

### `forecast_agent.py` (antes `forecast/agent.py`)
- **Por qué está deprecated**: Vive en el core, debería ser addon
- **Violación**: Feature opcional acoplada al core
- **Reemplazo**: `addons/forecast/` (microservicio opcional)

### `doc_qa_agent.py` (antes `agent/doc_qa.py`)
- **Por qué está deprecated**: Puede tener lógica autónoma
- **Violación**: Mezcla retrieval con decisiones
- **Reemplazo**: Tool puro de retrieval con evidencia explícita

## Prompts prohibidos

- `CODE_GENERATOR_SYSTEM_PROMPT`: Da autonomía al LLM sobre datos
- `CHART_SYSTEM_PROMPT`: LLM decide visualizaciones

## Regla de oro

**NUNCA** usar `exec()` / `eval()` de output del LLM.

## Fecha de congelación

2025-12-20

## Referencia

Ver [ARCHITECTURE_REVIEW.md](../../../../../ARCHITECTURE_REVIEW.md) para nueva arquitectura.
