# AUDITORÍA PASIVA - VERITY MVP
## Test de Genericidad con Dataset Arbitrario

**Fecha:** 2025-12-31  
**Auditor:** Modo pasivo (sin modificaciones de código)  
**Dataset:** Walmart Sales CSV (`C:\Users\ofgarcia\Downloads\walmart.csv`)  
**Columnas CSV:** Store, Date, Weekly_Sales, Holiday_Flag, Temperature, Fuel_Price, CPI, Unemployment  
**Registros:** 6,435

---

## OBJETIVO

Validar si el sistema Verity MVP puede procesar un CSV arbitrario **sin tocar código, prompts, diccionarios, aliases, configs ni tests**.

Operaciones a probar:
1. COUNT - Conteo de registros
2. UNIQUE - Valores únicos
3. TOP N - Rankings

---

## CONFIGURACIÓN DEL TEST

```python
available_tables = ["walmart"]  # Tabla NO registrada en Data Dictionary
```

Preguntas ejecutadas vía API `/api/v2/query`:
1. "¿Cuántos registros hay?"
2. "¿Cuántas tiendas únicas hay?"
3. "Top 5 tiendas por ventas"
4. "Top 10 departamentos por ventas"
5. "Top 5 tiendas en semanas con holiday"
6. "Top 5 tiendas por ventas" (repetida - test de cache)

---

## RESULTADOS

| # | Pregunta | Status | Intent | Confidence | Resultado | Cache Hit | Human Intervention |
|---|----------|--------|--------|------------|-----------|-----------|---------------------|
| 1 | "¿Cuántos registros hay?" | **400** | null | null | FAIL - HTTP Error | No | No |
| 2 | "¿Cuántas tiendas únicas hay?" | 200 | aggregate | 0.2 | FAIL - Desambiguación incorrecta | No | **Sí** |
| 3 | "Top 5 tiendas por ventas" | **400** | null | null | FAIL - HTTP Error | No | No |
| 4 | "Top 10 departamentos por ventas" | **400** | null | null | FAIL - HTTP Error | No | No |
| 5 | "Top 5 tiendas en semanas con holiday" | 200 | unknown | 0.2 | FAIL - No procesado | No | No |
| 6 | "Top 5 tiendas por ventas" (repetida) | **400** | null | null | FAIL - Sin cache | No | No |

### Score Final: **0/6 preguntas exitosas**

---

## HALLAZGOS DETALLADOS

### 1. Pregunta 2 - Desambiguación Incorrecta

El sistema respondió pidiendo desambiguación, pero **sugirió métricas del dominio equivocado**:

```
¿A cuál métrica te refieres? Responde con el número (1-5) o el nombre exacto:
1) total_plays (alias: cuantas canciones, score: 90.0)
2) unique_tracks (alias: canciones unicas, score: 90.0)
```

**Problema:** El fuzzy matcher encontró matches parciales contra aliases de `listening_history` (Spotify), no del dataset Walmart.

### 2. HTTP 400 en 4 de 6 preguntas

Las preguntas 1, 3, 4 y 6 retornaron HTTP 400 sin response body. Esto indica excepciones no manejadas, probablemente:
- `NoTableMatchException` - tabla `walmart` no existe en Data Dictionary
- `UnresolvedMetricException` - métricas no encontradas

### 3. Intent Unknown

La pregunta 5 fue clasificada como `intent: unknown` con `confidence: 0.2`, indicando que el IntentResolver no pudo mapear la pregunta a una operación conocida.

### 4. Sin Cache Hit

La pregunta repetida (#6 = #3) no mostró cache hit, aunque ambas fallaron con el mismo error.

---

## ANÁLISIS DE CAUSA RAÍZ

### Dependencias Hardcodeadas Identificadas

1. **Data Dictionary Estático**
   - Ubicación: `src/verity/data/dictionary.json`
   - Solo contiene: `orders`, `listening_history`
   - No tiene `walmart`

2. **resolve_semantics Tool**
   - Hace fuzzy match contra aliases del Data Dictionary
   - No tiene fallback para tablas no registradas
   - `_detect_ranking_generic()` busca columnas en el schema del diccionario, no del CSV

3. **Sin Schema Inference**
   - No hay mecanismo para inferir columnas desde un CSV arbitrario
   - El sistema asume que todas las tablas están pre-registradas

---

## DIAGRAMA DE FLUJO DEL FALLO

```
Usuario sube walmart.csv
    │
    ▼
API recibe question + available_tables=["walmart"]
    │
    ▼
IntentResolver clasifica intent
    │
    ▼
resolve_semantics Tool ejecuta
    │
    ├─► Busca "walmart" en Data Dictionary → NO EXISTE
    │
    ├─► Fuzzy match encuentra aliases similares en OTRAS tablas
    │   (ej: "tiendas" ~ "canciones" en listening_history)
    │
    └─► Lanza NoTableMatchException o AmbiguousMetricException
        │
        ▼
    HTTP 400 o Desambiguación incorrecta
```

---

## CONCLUSIÓN

### El sistema Verity MVP **NO ES GENÉRICO**.

Para soportar datasets arbitrarios sin modificar código, se requeriría:

| Capacidad Faltante | Estado Actual | Requerido |
|--------------------|---------------|-----------|
| Schema Inference | No existe | Leer columnas del CSV al vuelo |
| Data Dictionary Dinámico | Estático JSON | Auto-registro de tablas subidas |
| Fallback sin diccionario | N/A | Operaciones básicas (COUNT, etc.) sin pre-registro |
| Detección de dominio | No existe | Evitar sugerir métricas de otro dominio |

---

## ARCHIVOS RELACIONADOS

- **Script de auditoría:** `scripts/audit_walmart.py`
- **Resultados JSON:** `audit_results.json`
- **Data Dictionary:** `src/verity/data/dictionary.json`
- **resolve_semantics:** `src/verity/tools/resolve_semantics/__init__.py`

---

## RECOMENDACIÓN

Antes de considerar el sistema "genérico", implementar al menos:

1. **Schema inference** desde CSV/Parquet al momento del upload
2. **Auto-registro temporal** en Data Dictionary para tablas ad-hoc
3. **Operaciones básicas sin diccionario** (COUNT(*), GROUP BY columna explícita)

---

*Auditoría realizada en modo pasivo. No se modificó código del sistema.*
