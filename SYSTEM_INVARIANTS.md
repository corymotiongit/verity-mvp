# Verity - System Invariants

> **Documento vivo**: Declara explícitamente qué nunca debe pasar,
> qué debe fallar de forma ruidosa, y qué siempre debe loguearse.
>
> Este documento previene regresiones invisibles.

**Última actualización**: 2025-12-26  
**Versión**: 1.0

---

## 1. Invariantes de Datos

### NUNCA debe pasar:

| ID | Invariante | Enforcement |
|----|-----------|-------------|
| D1 | Cambiar de data source sin log explícito | `logger.info("[run_table_query] Loading from {source}")` |
| D2 | Retornar datos sin `data_source` en output | Schema require: `data_source` |
| D3 | Truncar resultados sin `rows_truncated: true` | Output siempre incluye flag |
| D4 | Retornar datos con NaN sin excepción | `TypeMismatchException` obligatorio |
| D5 | Cargar tabla que no está en `available_tables` | `NoTableMatchException` obligatorio |

### SIEMPRE debe loguearse:

```python
# Al cargar datos:
logger.info(f"[run_table_query] Loading table '{table}' from {data_source}: {path}")
logger.info(f"[run_table_query] Loaded {len(df)} rows from {data_source}")

# Al truncar:
logger.warning(f"[run_table_query] Results truncated: {before} -> {after} rows (limit={limit})")

# Al capear ranking:
logger.warning(f"[resolve_semantics] Ranking limit capped: requested {requested}, using {actual}")
```

---

## 2. Invariantes de Cache

### NUNCA debe pasar:

| ID | Invariante | Enforcement |
|----|-----------|-------------|
| C1 | Cache key sin `order_by` | Incluido en `cache_key_content` |
| C2 | Cache key sin `columns` | Incluido en `cache_key_content` |
| C3 | Cache key sin `limit` | Incluido en `cache_key_content` |
| C4 | Retornar cache hit sin `cache_hit: true` | Output siempre incluye flag |

### Cache Key DEBE incluir:

```python
cache_key_content = json.dumps({
    "table": table_name,
    "columns": columns,       # ✅ Obligatorio
    "metrics": metrics,
    "filters": filters_spec,
    "group_by": group_by,
    "order_by": order_by,     # ✅ Obligatorio
    "limit": limit,           # ✅ Obligatorio
    "time_column": time_column,
    "time_grain": time_grain,
    "baseline_period": baseline_period,
    "compare_period": compare_period
}, sort_keys=True)
```

---

## 3. Invariantes de Pipeline

### NUNCA debe pasar:

| ID | Invariante | Enforcement |
|----|-----------|-------------|
| P1 | Ejecutar `run_table_query` sin `resolve_semantics` previo | `ValueError` en pipeline |
| P2 | Retornar datos sin `table_id` | Schema require |
| P3 | Aceptar métrica con score < 85 | `UnresolvedMetricException` |
| P4 | Aceptar operadores no soportados | Whitelist en `allowed_ops` |

### Orden de ejecución SIEMPRE:

```
1. IntentResolver.resolve(question)
2. resolve_semantics (si intent requiere datos)
3. run_table_query (si semantics OK)
4. build_chart (si intent incluye chart)
5. ResponseComposer.compose()
```

---

## 4. Invariantes de Contratos

### NUNCA debe pasar:

| ID | Invariante | Valor Correcto |
|----|-----------|----------------|
| K1 | `limit` default diferente entre schema y código | `1000` en ambos |
| K2 | Ranking limit > 50 sin `limit_capped: true` | Flag obligatorio |
| K3 | Output sin `execution_time_ms` | Siempre incluido |

### Defaults autorizados:

| Parámetro | Default | Max | Configurable |
|-----------|---------|-----|--------------|
| `limit` (query) | 1000 | 50000 | Sí (input) |
| `limit` (ranking) | 10 | 50 | No (hardcoded) |
| `cache_ttl` | 120s | - | No (TODO) |
| `fuzzy_threshold` | 85 | - | No (hardcoded) |

---

## 5. Invariantes de Observabilidad

### SIEMPRE debe loguearse:

| Evento | Nivel | Formato |
|--------|-------|---------|
| Request recibido | INFO | `[{request_id}] {method} {path}` |
| Response enviado | INFO | `[{request_id}] {method} {path} -> {status}` |
| Data source usado | INFO | `[run_table_query] Loading from {source}` |
| Filas cargadas | INFO | `Loaded {n} rows from {source}` |
| Truncación | WARN | `Results truncated: {before} -> {after}` |
| Ranking capeado | WARN | `Ranking limit capped: {requested} -> {actual}` |
| Excepción tipada | WARN | `VerityException: {code} - {message}` |
| Excepción no tipada | ERROR | Full traceback |

### Métricas obligatorias:

- `tool_latency_ms` por tool
- `tool_error_count` por tool + código
- `cache_hit_count`
- `cache_miss_count`

---

## 6. Checklist de Validación

Antes de cada release, verificar:

- [ ] Todos los tests pasan (no skips injustificados)
- [ ] `data_source` presente en todos los outputs de query
- [ ] Cache key incluye todos los parámetros
- [ ] `limit` alineado entre schema y código
- [ ] Logging de truncación activo
- [ ] No hay fallbacks silenciosos

---

## 7. Cómo agregar nuevos invariantes

1. Documentar en este archivo
2. Agregar test que valide el invariante
3. Agregar enforcement en código (excepción o assertion)
4. Agregar logging si aplica
5. Actualizar versión del documento

---

## Historial de Cambios

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2025-12-26 | Creación inicial post-auditoría |
