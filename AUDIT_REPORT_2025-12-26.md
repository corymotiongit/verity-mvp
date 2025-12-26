# Auditoría de Seguridad y Hardening - Verity MVP

**Fecha**: 2025-12-26
**Auditor**: Sistema Automatizado
**Versión**: stable-tests-v1.1

---

## 1. FUENTES DE DATOS

### 🔴 RIESGO CRÍTICO: Fallback Silencioso a Supabase

**Ubicación**: `src/verity/tools/run_table_query/__init__.py` líneas 116-157

**Problema**:
```python
# Cargar tabla (buscar en uploads/canonical/ o fallback a Supabase)
canonical_path = Path("uploads/canonical")
for file in canonical_path.glob(f"*{table_name}*.csv"):
    ...
if table_file:
    df = pd.read_csv(table_file, encoding="utf-8")
else:
    # Fallback: cargar desde Supabase  <-- SILENCIOSO
```

**Riesgos**:
1. Si el archivo CSV no existe, el sistema cambia a Supabase SIN notificar al usuario
2. Los datos pueden ser diferentes entre CSV y Supabase
3. No hay logging de qué fuente se usó
4. El operador no sabe de dónde vinieron los datos

**Recomendación Inmediata**:
```python
# ANTES de elegir fallback, loguear explícitamente
if table_file:
    logger.info(f"Loading table '{table_name}' from CSV: {table_file}")
    data_source = "csv"
else:
    logger.warning(f"CSV not found for '{table_name}', falling back to Supabase")
    data_source = "supabase"
```

### 🟡 RIESGO MEDIO: Glob Pattern Demasiado Permisivo

**Ubicación**: línea 120

```python
for file in canonical_path.glob(f"*{table_name}*.csv"):
```

**Problema**: Si tengo `orders.csv` y `orders_backup.csv`, puede cargar cualquiera.

---

## 2. LÍMITES Y DEFAULTS PELIGROSOS

### 🔴 CRÍTICO: Límite Default de 20,000 Filas

**Ubicación**: `run_table_query/__init__.py` línea 81

```python
limit = input_data.get("limit", 20000)
```

**Problema**: 
- Schema dice `default: 1000` pero código usa `20000`
- Discrepancia entre contrato y implementación
- 20K filas pueden truncar resultados sin aviso

### 🔴 CRÍTICO: Límite de 50 en Rankings

**Ubicación**: `resolve_semantics/__init__.py` línea 332

```python
limit = min(int(match.group(1)), 50)  # max 50
```

**Problema**: Si el usuario pide "top 100", recibe 50 sin aviso.

### 🟡 MEDIO: Límite Hardcodeado de 8 Candidatos

**Ubicación**: `resolve_semantics/__init__.py` línea 140

```python
extracted = process.extract(
    phrase,
    aliases,
    scorer=fuzz.WRatio,
    limit=8,  # <-- Hardcodeado, no configurable
)
```

### 🟡 MEDIO: Cache TTL Hardcodeado

**Ubicación**: `run_table_query/__init__.py` línea 31

```python
_CACHE_TTL_SECONDS = 120
```

No configurable via env/settings.

### 🟡 MEDIO: Batch Size de Supabase Hardcodeado

**Ubicación**: línea 143

```python
batch_size = 1000
```

---

## 3. CACHE

### ✅ Cache Key Completa

La cache key **SÍ incluye** todos los parámetros relevantes:

```python
cache_key_content = json.dumps({
    "table": table_name,
    "metrics": metrics,
    "filters": filters_spec,
    "group_by": group_by,
    "limit": limit,
    "time_column": time_column,
    "time_grain": time_grain,
    "baseline_period": baseline_period,
    "compare_period": compare_period
}, sort_keys=True)
```

### 🔴 FALTA: `order_by` NO está en Cache Key

**Problema**: Dos queries con mismo contenido pero diferente `order_by` comparten cache.

```python
# FALTA:
"order_by": order_by,  # <-- NO EXISTE EN CACHE KEY
```

### 🟡 FALTA: Invalidación en Cambio de Config

No hay mecanismo para invalidar cache cuando:
- Cambia el archivo CSV
- Cambia la configuración
- Se reinicia la aplicación (cache persiste en memoria)

### 🟡 FALTA: `columns` NO está en Cache Key

Si se pide la misma query con diferentes `columns`, retorna cache incorrecto.

---

## 4. PIPELINE CONTRACTS

### ✅ Inputs/Outputs Explícitos

Los schemas JSON definen contratos claros:
- `resolve_semantics/schema.json`
- `run_table_query/schema.json`

### 🟡 DEPENDENCIA IMPLÍCITA: Pipeline asume orden de etapas

**Ubicación**: `pipeline.py` líneas 248-310

```python
elif tool_name == "run_table_query@1.0":
    if not previous_output:
        raise ValueError("run_table_query requires previous resolve_semantics output")
```

No hay validación de que `previous_output` tenga la estructura esperada.

### 🟡 DEPENDENCIA IMPLÍCITA: `result_metadata` opcional

El campo `result_metadata` se propaga pero es opcional. Si falta, el ResponseComposer asume comportamiento por defecto.

---

## 5. TESTS

### 🔴 Tests que Pasan por Accidente

**1. `test_compare_periods_v2`** - SKIP injustificado técnicamente
- El test está bien diseñado
- El skip es por problema de arquitectura (app factory)
- Debería haber issue/ticket asociado

**2. Tests de Rate Limiting** - Estado inconsistente
- `test_rate_limit_auth_endpoint`: Puede pasar o fallar según orden de ejecución
- El rate limit store es global y no se limpia entre tests

### 🟡 Cobertura Faltante

**Rutas NO cubiertas**:
1. Fallback a Supabase (solo CSV en tests)
2. Cache hit (el fixture limpia cache)
3. Paginación de Supabase (líneas 141-152)
4. Validación de NaN en columnas temporales
5. Operadores `LIKE` e `IN` en filtros complejos

### 🟡 Mocks Incompletos

**`test_auth_otp_jwt`**: Acepta 502 como éxito
```python
assert authed.status_code in (200, 502), f"Auth should pass, got {authed.status_code}"
```
Esto enmascara errores reales del endpoint.

---

## 6. OBSERVABILIDAD

### 🔴 NO SE LOGUEA: Data Source Real Usado

El sistema no loguea si usó CSV o Supabase.

### 🔴 NO SE LOGUEA: Número Real de Filas Cargadas

Antes del `limit`, no hay log de cuántas filas había originalmente.

### 🔴 NO SE LOGUEA: Operación Ejecutada

No hay log de `operation=rank`, `operation=aggregate`, etc.

### ✅ SÍ SE LOGUEA:
- Request/response con request_id
- Excepciones con código y mensaje
- Latencia por tool (en métricas)
- Errores de Gemini

---

## LISTA DE DEFAULTS PELIGROSOS

| Default | Ubicación | Valor | Riesgo |
|---------|-----------|-------|--------|
| `limit` | run_table_query | 20000 | Truncación silenciosa |
| `limit` (rankings) | resolve_semantics | 10 (max 50) | Truncación silenciosa |
| `available_tables` | query_v2.py | `["orders"]` | Tabla incorrecta |
| `_CACHE_TTL_SECONDS` | run_table_query | 120 | No configurable |
| `batch_size` (Supabase) | run_table_query | 1000 | No configurable |
| `threshold` (fuzzy) | resolve_semantics | 85 | Hardcodeado |
| `ambiguity_margin` | resolve_semantics | 3 | Hardcodeado |

---

## CHECKLIST DE INVARIANTES DEL SISTEMA

### Invariantes que NUNCA Deben Romperse:

1. **[ ]** Cada query retornada debe incluir `data_source` en metadata
2. **[✅]** Nunca ejecutar query sin primero resolver semántica (validado en pipeline)
3. **[✅]** Nunca retornar datos sin `table_id` para trazabilidad
4. **[ ]** Nunca truncar resultados sin notificar `rows_truncated: true`
5. **[✅]** Nunca aceptar métrica con score < 85 (threshold)
6. **[✅]** Nunca aceptar operadores no soportados en filtros (whitelist explícita)
7. **[ ]** Nunca usar cache sin incluir TODOS los parámetros en la key
8. **[✅]** Nunca ejecutar query si tabla no está en `available_tables`
9. **[✅]** Nunca retornar datos con NaN sin excepción tipada
10. **[ ]** Nunca cambiar de data source sin log explícito

---

## ACCIONES INMEDIATAS (HARDENING)

### Prioridad 1 (Crítica):
1. Agregar `order_by` y `columns` a cache key
2. Loguear data_source (CSV vs Supabase) en cada query
3. Alinear `limit` default entre schema (1000) y código (20000)

### Prioridad 2 (Alta):
4. Agregar `rows_before_limit` al output para detectar truncación
5. Loguear `original_row_count` antes de aplicar limit
6. Notificar al usuario cuando se aplica max 50 en rankings

### Prioridad 3 (Media):
7. Hacer configurable `_CACHE_TTL_SECONDS` via env
8. Agregar tests para fallback a Supabase
9. Agregar tests para cache hit scenarios
