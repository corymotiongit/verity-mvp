# Verity MVP - Session Notes (Dec 18, 2025)

## Resumen de la Sesión

### Lo que se implementó:

#### 1. **Quote Cleaning Fix**
- **Problema:** Valores en CSV tenían comillas embebidas (`'Tlapehuala'`)
- **Root cause:** Profiler cargaba datos sin limpiar comillas
- **Fix:** Agregada limpieza de comillas en `profiler._load_dataframe()`

#### 2. **Punctuation Normalization**
- **Archivo:** `src/verity/modules/data/value_index.py`
- `_normalize()` ahora quita puntuación (ej: `Tlapehuala?` → `tlapehuala`)
- Permite que queries con `?` matcheen correctamente

#### 3. **File Normalizer Pipeline (NUEVO)**
- **Archivo:** `src/verity/modules/data/normalizer.py`
- Pipeline completo: **Raw → Canonical → Audit**

```
uploads/
├── raw/          ← Archivo original (preservado)
├── canonical/    ← Archivo normalizado (UTF-8, limpio)
└── audit/        ← Log de transformaciones (JSON)
```

**Detección automática:**
- Encoding (UTF-8, latin-1, UTF-16, etc.)
- Separator (`,` `;` `\t` `|`)
- Quote char (`"` o `'`)
- Escape char (`\` si aplica)

**Transformaciones:**
- `encoding`: Conversión a UTF-8
- `separator_normalize`: Estandarizar a `,`
- `quotechar_normalize`: Estandarizar a `"`
- `header_clean`: Limpiar nombres de columnas
- `quote_strip`: Quitar comillas de valores
- `remove_empty_rows`: Eliminar filas vacías
- `standardize_nulls`: Normalizar valores null
- `skip_bad_lines`: Saltar líneas problemáticas (con log)

**Audit log ejemplo:**
```json
{
  "doc_id": "abc123",
  "raw_file": "raw/abc123_contratos.csv",
  "canonical_file": "canonical/abc123_contratos.csv",
  "rows_before": 850,
  "rows_after": 847,
  "transforms_applied": [
    {"rule": "encoding", "details": {"from": "latin-1", "to": "utf-8"}},
    {"rule": "quotechar_normalize", "details": {"from": "'", "to": "\""}}
  ],
  "sample_issues": [...]
}
```

#### 4. **Integration con Documents Service**
- `ingest_document()` usa FileNormalizer para CSV/Excel
- Guarda normalization info en document metadata
- Profiler y Sandbox prefieren canonical files automáticamente

---

## Archivos Modificados/Creados

```
src/verity/modules/data/
├── normalizer.py      # NUEVO - Pipeline de normalización
├── __init__.py        # Export de FileNormalizer
├── profiler.py        # Usa canonical files, fallback a raw
├── sandbox.py         # Usa canonical files, skip cleaning si canonical
├── value_index.py     # _normalize() quita puntuación

src/verity/modules/documents/
├── service.py         # Integra FileNormalizer en ingest
```

---

## Estado Actual

| Component | Status |
|-----------|--------|
| Quote Cleaning | ✅ Implementado |
| ValueResolver | ✅ Implementado |
| Table Rendering | ✅ Implementado |
| Document Persistence | ✅ Implementado |
| Intent Filter by Category | ✅ Implementado |
| **File Normalizer** | ✅ **NUEVO** |
| **Routing Fix (Source of Truth)** | ✅ **NUEVO** |
| **Hardening Evidence (row_ids)** | ✅ **NUEVO** |
| **Tag Management** | ✅ **NUEVO** |
| **Chat Scope (Persistent)** | ✅ **NUEVO** |
| **Cache Admin API** | ✅ **NUEVO** |

---

## Routing & Source of Truth Fixes

### Problema Original
Query tabular respondía con datos del documento equivocado porque:
- DataEngine buscaba en `uploads/` (mezclaba archivos)
- File Search indexaba CSVs (DocQA podía contestar preguntas tabulares)
- Sin logging para diagnosticar routing

### Fixes Implementados

#### 1. **CSV/Excel NO va a File Search**
```python
# documents/service.py
if not is_tabular:
    upload_to_file_search_store(...)  # Solo PDF/texto
else:
    logger.info("[FILE_SEARCH] SKIPPED tabular file")
```

#### 2. **DataEngine usa canonical path**
```python
# agent/service.py  
canonical_path = normalizer.get_canonical_path(str(doc.id))
if canonical_path.exists():
    file_path = canonical_path
    logger.info(f"[DATA_QUERY] CANONICAL_PATH={canonical_path}")
```

#### 3. **Logging detallado por request**
```
[ROUTING] route_selected=data_query, target_file_id=abc123, reasoning=...
[DATA_QUERY] file_id=abc123, display_name=productos.csv
[DATA_QUERY] CANONICAL_PATH=uploads/canonical/abc123_productos.csv
[DATA_QUERY] Result: answer_type=scalar, code_executed=True
```

#### 4. **Evidence en Source**
```python
source = Source(
    title=f"Data Engine: {doc.display_name}",
    snippet=f"File: {file_path}\nCode:\n{executed_code}..."
)
```

---

## Tests Ejecutados

1. **test_normalizer.py** - Pipeline de normalización ✅
2. **test_e2e_normalize.py** - Upload → Normalize → Query ✅  
3. **test_routing.py** - Routing correcto y source of truth ✅
4. **test_evidence.py** - Evidence estructurado en sources ✅

---

## Contrato Unificado de Sources (Audit-Ready)

### Para Tabular (type="data")
```json
{
  "type": "data",
  "file": "productos.csv",
  "canonical_file_id": "abc123-uuid",
  "data_evidence": {
    "operation": "lookup",
    "filter_applied": "PRODUCTO = 'Laptop Dell'",
    "columns_used": ["PRODUCTO", "PRECIO"],
    "row_ids": [2, 3, 4],
    "sample_rows": [{"PRODUCTO": "Laptop Dell", "PRECIO": 25000}]
  }
}
```

### Para DocQA (type="doc")
```json
{
  "type": "doc",
  "file": "contrato.pdf",
  "doc_evidence": {
    "page": 5,
    "section": "Cláusula 3",
    "excerpt": "El proveedor deberá..."
  }
}
```

### Force Document (context.document_id)
Si se pasa `context.document_id`, se bypasea el classify_intent y se fuerza `data_query`:
```json
{
  "message": "Cuál es el precio?",
  "context": {
    "document_id": "abc123-uuid"
  }
}
```

---

## Próximos Pasos

1. **row_ids exactos** - Implementar tracking de líneas en sandbox
2. **Tag Management** - CRUD de etiquetas por organización  
3. **Cache Admin** - Endpoint para limpiar cache
4. **Frontend** - Mostrar evidence estructurado en UI

## Chat Context & Scope Persistence

Se implementó una arquitectura robusta de contexto por conversación para soportar "Buscando en...":

1.  **ChatScope (Schema)**: Define filtros (`project`, `tags`, `collection`) y metadatos de scope.
2.  **ScopeResolver (Service)**: Traduce `ChatScope` -> `doc_ids` reales. Maneja lógica de "Empty Scope" y expansión de Collections.
3.  **Persistencia**: Scope guardado en `uploads/chat_contexts.json` por `conversation_id`.
4.  **Endpoints**:
    *   `GET/PUT /agent/chat/{id}/scope`: Gestionar scope desde UI.
    *   `POST /agent/chat/{id}/scope/resolve`: Previsualizar scope (count/summary).
5.  **Agent Integration**:
    *   El agente lee el scope persistido automáticamente.
    *   Filtra documentos candidatos para clasificación de intención.
    *   Devuelve `scope_info` en cada respuesta para el banner de UI.

6.  **Diagnostics & Suggestions**:
    *   Si el scope está vacío, el sistema diagnostica la causa (`empty_reason`):
        *   "Proyecto vacío" -> Sugiere **Upload**.
        *   "Filtros sin match" -> Sugiere **Clear Filters**.
    *   Estructura `ScopeSuggestion` enviada al Frontend para CTAs inteligentes.
