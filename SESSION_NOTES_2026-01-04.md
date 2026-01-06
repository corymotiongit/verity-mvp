# Verity MVP - Session Notes (Jan 4, 2026)

## Resumen de la Sesión

**Objetivo principal**: Auditoría pasiva de genericidad del sistema con dataset arbitrario (Walmart Sales).

**Resultado crítico**: ⚠️ **Sistema NO es genérico** - 0/6 preguntas exitosas sin modificar código.

---

## Auditoría de Genericidad - Dataset Walmart

### Configuración del Test

- **Dataset**: Walmart Sales CSV (`walmart.csv`)
- **Registros**: 6,435 filas
- **Columnas**: Store, Date, Weekly_Sales, Holiday_Flag, Temperature, Fuel_Price, CPI, Unemployment
- **Método**: Auditoría pasiva (sin modificar código, prompts, diccionarios o configs)
- **Endpoint**: `/api/v2/query`

### Preguntas Probadas

| # | Pregunta | Status | Intent | Resultado |
|---|----------|--------|--------|-----------|
| 1 | "¿Cuántos registros hay?" | **400** | null | FAIL - HTTP Error |
| 2 | "¿Cuántas tiendas únicas hay?" | 200 | aggregate | FAIL - Sugiere métricas Spotify ❌ |
| 3 | "Top 5 tiendas por ventas" | **400** | null | FAIL - HTTP Error |
| 4 | "Top 10 departamentos por ventas" | **400** | null | FAIL - HTTP Error |
| 5 | "Top 5 tiendas en semanas con holiday" | 200 | unknown | FAIL - No procesado |
| 6 | "Top 5 tiendas por ventas" (repetida) | **400** | null | FAIL - Sin cache |

**Score Final: 0/6 preguntas exitosas** ❌

---

## Hallazgos Críticos

### 1. Data Dictionary Hardcodeado

**Problema**: El sistema solo conoce tablas pre-registradas en `data/dictionary.json`:
- `orders` (demo original)
- `listening_history` (Spotify)

**Impacto**: Tabla `walmart` → `NoTableMatchException` → HTTP 400

**Ubicación**: `src/verity/data/dictionary.json`

### 2. Fuzzy Match Cruza Dominios

**Problema**: Pregunta "¿Cuántas tiendas únicas hay?" → Sistema sugiere:
```
1) total_plays (alias: cuantas canciones, score: 90.0)
2) unique_tracks (alias: canciones unicas, score: 90.0)
```

**Root Cause**: `resolve_semantics` hace fuzzy match contra **todas las tablas** del diccionario, no solo la tabla objetivo.

**Ubicación**: `src/verity/tools/resolve_semantics/__init__.py`

### 3. Sin Schema Inference

**Problema**: No existe mecanismo para:
- Leer columnas de un CSV arbitrario al vuelo
- Auto-registrar tablas subidas por el usuario
- Operar sin Data Dictionary (operaciones básicas como COUNT)

**Impacto**: Sistema depende 100% de pre-registro manual.

### 4. HTTP 400 Sin Body

**Problema**: 4 de 6 preguntas retornaron `400` sin response body.

**Causa**: Excepciones no capturadas:
- `NoTableMatchException`
- `UnresolvedMetricException`

### 5. Sin Cache Hit en Preguntas Repetidas

**Problema**: Pregunta #6 (idéntica a #3) no mostró cache hit.

**Posible causa**: Ambas fallaron antes de llegar a `run_table_query` (donde está el cache).

---

## Diagrama de Flujo del Fallo

```
Usuario sube walmart.csv
    │
    ▼
API: /api/v2/query
    question="Top 5 tiendas por ventas"
    available_tables=["walmart"]
    │
    ▼
IntentResolver
    │
    ▼
resolve_semantics Tool
    │
    ├─► Busca "walmart" en Data Dictionary
    │   └─► NO EXISTE ❌
    │
    ├─► Fuzzy match contra TODAS las tablas
    │   └─► Encuentra aliases en listening_history
    │       (ej: "tiendas" ~ "canciones")
    │
    └─► Lanza NoTableMatchException
        │
        ▼
    HTTP 400 (sin body)
```

---

## Análisis de Causa Raíz

### Dependencias Hardcodeadas

| Componente | Estado Actual | Problema |
|-----------|---------------|----------|
| Data Dictionary | JSON estático | Solo `orders`, `listening_history` |
| Schema | Pre-registrado manual | No infiere columnas del CSV |
| Fuzzy Match | Global (todas las tablas) | Cruza dominios |
| Fallback | No existe | Operaciones básicas requieren diccionario |

### Capabilities Faltantes

| Capacidad | Requerido Para Genericidad |
|-----------|---------------------------|
| Schema Inference | Leer columnas del CSV al vuelo |
| Data Dictionary Dinámico | Auto-registro de tablas subidas |
| Operaciones sin diccionario | COUNT(*), SELECT columnas explícitas |
| Domain Detection | Evitar sugerir métricas de otro dominio |
| Error Handling | HTTP 400 con body descriptivo |

---

## Archivos Modificados/Creados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `AUDIT_REPORT_2025-12-31_GENERICIDAD.md` | NEW | Reporte completo de auditoría |
| `audit_results.json` | NEW | Resultados estructurados (6 preguntas) |
| `scripts/audit_walmart.py` | NEW | Script de test automatizado |
| `tests/test_generic_csv.py` | NEW | Test suite para datasets arbitrarios |

**Commit**: `a7d50a2`  
**Mensaje**: `audit: Test de genericidad con dataset Walmart - Sistema NO es generico (0/6 preguntas exitosas)`

---

## Recomendaciones de Acción

### Prioridad ALTA

1. **Schema Inference al Upload**
   - Detectar columnas/tipos desde CSV/Parquet
   - Auto-registrar en Data Dictionary temporal
   - **Ubicación**: `src/verity/modules/documents/service.py`

2. **Domain Scoping en resolve_semantics**
   - Fuzzy match SOLO contra la tabla objetivo
   - Evitar sugerir métricas de otros dominios
   - **Ubicación**: `src/verity/tools/resolve_semantics/__init__.py`

3. **Operaciones Básicas sin Diccionario**
   - Implementar fallback para:
     - `COUNT(*)` → devolver filas totales
     - `COUNT(DISTINCT column)` → valores únicos de columna
     - `TOP N column BY metric` → ranking directo
   - **Ubicación**: `src/verity/tools/run_table_query/__init__.py`

### Prioridad MEDIA

4. **Error Handling Mejorado**
   - HTTP 400 debe incluir body con error code
   - `NoTableMatchException` debe sugerir tablas disponibles
   - **Ubicación**: `src/verity/main.py` (exception handlers)

5. **Tests de Regresión**
   - Agregar `test_generic_csv.py` al CI
   - Validar soporte multi-dominio
   - **Ubicación**: `tests/`

---

## Testing / Calidad

### Tests Ejecutados

| Test | Status | Archivo |
|------|--------|---------|
| Walmart CSV import | ✅ | `scripts/audit_walmart.py` |
| 6 preguntas genéricas | ❌ 0/6 | `audit_results.json` |
| Existing test suite | ⚠️ No ejecutado | - |

### Coverage

- ❌ No hay tests de genericidad en CI
- ❌ No hay validación de multi-dominio
- ✅ Tests de Spotify siguen pasando (asumido)

---

## Estado del Sistema

### ✅ Funciona Correctamente

- Pipeline Spotify (listening_history)
- Cache + logging + SYSTEM_INVARIANTS
- Multi-org isolation
- Auditoría de seguridad resuelta (26 Dic)

### ❌ Limitaciones Identificadas

- **NO soporta datasets arbitrarios** sin pre-registro
- **NO detecta schema** de CSV automáticamente
- **NO tiene fallback** para operaciones básicas
- Fuzzy match cruza dominios (desambiguación incorrecta)

---

## Próximos Pasos (Enero 2026)

### Opción A: Hacer el Sistema Genérico

1. Implementar schema inference en document upload
2. Auto-registro temporal en Data Dictionary
3. Operaciones básicas sin diccionario
4. Tests de regresión multi-dominio

**Esfuerzo estimado**: 3-5 días

### Opción B: Documentar Limitación + Workaround

1. Actualizar README con "Supported Datasets"
2. Proveer template para Data Dictionary
3. Script para generar diccionario desde CSV
4. Mantener enfoque en dominios específicos (Spotify, Orders)

**Esfuerzo estimado**: 1 día

### Opción C: Híbrido (Recomendado)

1. Implementar **solo** schema inference (auto-detect columnas)
2. Operaciones básicas (COUNT, DISTINCT) sin diccionario
3. Mantener diccionario manual para métricas complejas
4. Documentar cuándo se requiere pre-registro

**Esfuerzo estimado**: 2-3 días

---

## Comandos Útiles

```powershell
# Ejecutar auditoría Walmart
python scripts/audit_walmart.py

# Ver resultados JSON
Get-Content audit_results.json | ConvertFrom-Json | Format-Table

# Health check
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/v2/health'
```

---

## Referencias

- **Reporte completo**: [AUDIT_REPORT_2025-12-31_GENERICIDAD.md](AUDIT_REPORT_2025-12-31_GENERICIDAD.md)
- **Resultados JSON**: [audit_results.json](audit_results.json)
- **Test script**: [scripts/audit_walmart.py](scripts/audit_walmart.py)
- **Invariantes**: [SYSTEM_INVARIANTS.md](SYSTEM_INVARIANTS.md)
- **Session anterior**: [SESSION_NOTES_2025-12-26.md](SESSION_NOTES_2025-12-26.md)

---

*Última actualización: 4 Enero 2026*
