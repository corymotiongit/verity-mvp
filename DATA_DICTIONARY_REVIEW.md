# Data Dictionary - Estructura y Evaluación Crítica

## 📋 Tu propuesta (evaluada)

### ✅ Aciertos
1. **Separación tables/metrics**: Correcto, metadata vs semántica
2. **expression + aliases**: Mapeo canónico claro
3. **Regla "LLM no inventa métricas"**: CRÍTICO, bien planteado
4. **Filtros automáticos**: Evita repetir lógica de negocio

### ⚠️ Mejoras necesarias

#### 1. Estructura de filtros
**Tu propuesta** (string):
```json
"filters": ["order_status = 'delivered'"]
```

**Problema**: Requiere parsing, vulnerable a SQL injection si se construye dinámicamente.

**Mejorado** (objeto estructurado):
```json
"filters": [
  {"column": "order_status", "operator": "=", "value": "delivered"}
]
```

#### 2. Metadata faltante en métricas
**Agregado**:
- `data_type`: integer | number | string (para validación)
- `requires`: Lista explícita de columnas necesarias
- `format`: number | currency | percent | date (para UI)
- `business_notes`: Contexto de negocio (opcional)

#### 3. Metadata faltante en columnas
**Tu propuesta**:
```json
"columns": {
  "order_id": "string"
}
```

**Mejorado**:
```json
"columns": {
  "order_id": {
    "type": "string",
    "description": "Identificador único de la orden"
  }
}
```

#### 4. Versioning
**Agregado en raíz**:
```json
{
  "version": "1.0",
  "updated_at": "2025-12-20T00:00:00Z",
  "changelog": [...]
}
```

#### 5. Clarificación de "deriva columnas desde expression"
**Ambiguo**: ¿Cómo parseas "count_distinct(customer_id) where..."?

**Solución**: Campo `requires` explícito.
```json
"repeat_customers": {
  "expression": "COUNT(DISTINCT customer_id) FILTER (WHERE order_count > 1)",
  "requires": ["customer_id", "order_status"]  ← resolve_semantics retorna esto
}
```

`run_table_query` recibe `requires` directamente, NO parsea expression.

---

## 🏗️ Flujo corregido

### resolve_semantics@1.0
**Input**: "cuántos clientes recurrentes tenemos?"

**Proceso**:
1. Fuzzy match "clientes recurrentes" → alias match → `repeat_customers`
2. Cargar métrica desde Data Dictionary
3. Extraer `requires`, `filters`, `expression`

**Output**:
```json
{
  "metrics": [
    {
      "name": "repeat_customers",
      "alias_matched": "clientes recurrentes",
      "definition": "COUNT(DISTINCT customer_id) FILTER (WHERE order_count > 1)",
      "requires": ["customer_id", "order_status"],
      "filters": [
        {"column": "order_status", "operator": "=", "value": "delivered"}
      ],
      "format": "number"
    }
  ],
  "confidence": 0.95
}
```

### run_table_query@1.0
**Input** (derivado de resolve_semantics):
```json
{
  "table": "orders",
  "columns": ["customer_id", "order_status"],  ← Viene de requires
  "metrics": [
    {
      "name": "repeat_customers",
      "sql": "COUNT(DISTINCT customer_id) FILTER (WHERE order_count > 1)"
    }
  ],
  "filters": [
    {"column": "order_status", "operator": "=", "value": "delivered"}
  ]
}
```

**Output**:
```json
{
  "table_id": "t_001",
  "columns": ["repeat_customers"],
  "rows": [[142]],
  "row_count": 1,
  "execution_time_ms": 23.5
}
```

---

## 📊 Checkpoints corregidos

**Tu propuesta**:
- semantic_resolution
- metric_resolution
- query_execution
- chart_build

**Corrección**: Deben ser nombres de tools reales (con versión):

```json
{
  "checkpoint_id": "cp_001",
  "conversation_id": "conv_123",
  "tool": "resolve_semantics@1.0",
  "input": {"question": "cuántos clientes recurrentes?"},
  "output": {"metrics": [...], "confidence": 0.95},
  "status": "ok",
  "timestamp": "2025-12-20T10:30:00Z"
}
```

```json
{
  "checkpoint_id": "cp_002",
  "conversation_id": "conv_123",
  "tool": "run_table_query@1.0",
  "input": {"table": "orders", "metrics": [...]},
  "output": {"table_id": "t_001", "rows": [[142]]},
  "status": "ok",
  "timestamp": "2025-12-20T10:30:01Z"
}
```

```json
{
  "checkpoint_id": "cp_003",
  "conversation_id": "conv_123",
  "tool": "build_chart@2.0",
  "input": {"table_id": "t_001", "chart_kind": "bar"},
  "output": {"chart_spec": {...}, "chart_id": "chart_001"},
  "status": "ok",
  "timestamp": "2025-12-20T10:30:02Z"
}
```

---

## ✅ Veredicto final

**Tu propuesta es sólida en concepto, con mejoras críticas en implementación:**

1. ✅ **Separación tables/metrics**: Excelente
2. ✅ **Aliases + expression**: Correcto
3. ✅ **Reglas duras anti-LLM**: CRÍTICO y bien pensado
4. ⚠️ **Filtros estructurados**: Necesario (objeto, no string)
5. ⚠️ **`requires` explícito**: Evita parsing de expression
6. ⚠️ **Versioning + changelog**: Mantenibilidad
7. ⚠️ **format + data_type**: Para validación y UI
8. ⚠️ **Checkpoints = tool names**: No nombres genéricos

**Implementado en**:
- [`src/verity/data/dictionary.json`](src/verity/data/dictionary.json)
- [`src/verity/data/dictionary.py`](src/verity/data/dictionary.py)

**Próximo paso recomendado**:
Implementar `fuzzy_match_metric()` con rapidfuzz/fuzzywuzzy para matching robusto.
