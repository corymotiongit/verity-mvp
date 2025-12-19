# Verity MVP - Session Notes (Dec 17, 2025)

## Resumen de la Sesión

### Lo que se implementó:

#### 1. **ValueResolver (100% Data-Driven)**
- **Archivo:** `src/verity/modules/data/value_resolver.py`
- Resolución de valores sin hardcodes
- Orden: Learned aliases → Exact → Substring → Fuzzy
- Thresholds: 
  - `>= 0.90`: Auto-pick
  - `0.60 - 0.90`: Confirmation
  - `>= 0.40`: Suggestions
- `OrgAliasMemory`: Aprende de confirmaciones por organización

#### 2. **Table Rendering (Backend)**
- **Archivo:** `src/verity/modules/data/schemas.py`
  - `TablePreview`: `{columns: [...], rows: [[...]], total_rows: int}`
- **Archivo:** `src/verity/modules/data/sandbox.py`
  - `_format_result()`: Serializa DataFrame/Series a formato estructurado
- **Archivo:** `src/verity/modules/data/engine.py`
  - `_format_success_response()`: Genera `table_preview` + `table_markdown`
- **Archivo:** `src/verity/modules/agent/service.py`
  - Incluye `table_markdown` en prompt de síntesis

#### 3. **Persistencia de Documentos (JSON)**
- **Archivo:** `src/verity/modules/documents/service.py`
  - `documents_db.json`: Guarda metadatos de documentos
  - `org_stores_db.json`: Guarda stores por organización
  - Se cargan al iniciar el módulo
  - Se guardan en cada ingest/delete

#### 4. **Filtrado por Category/Project en Intent Router**
- **Archivo:** `src/verity/modules/agent/service.py`
  - `_classify_intent()` ahora acepta `category` y `project`
  - Pre-filtra documentos antes de enviar a Gemini
  - Frontend envía `document_category` y `document_project` en context

---

## Bugs Pendientes (Para Mañana)

### 🔴 BUG CRÍTICO: Valores con Comillas en CSV
- **Problema:** Los valores del CSV tienen comillas simples: `'Tlapehuala'` en lugar de `Tlapehuala`
- **Ubicación:** `src/verity/modules/data/sandbox.py` → `load_dataframe()`
- **Fix implementado pero no activo:** Se agregó limpieza de comillas, pero el cache tiene valores viejos
- **Solución:** Reiniciar servidor y/o limpiar cache

### 🟡 Cache del DataEngine no se invalida
- El cache persiste entre recargas del servidor
- Necesita invalidarse cuando se sube un nuevo documento
- **Método agregado:** `DataEngineCache.clear_all()`
- **Falta:** Endpoint admin o trigger automático

### 🟡 Etiquetas persisten en frontend
- Las categorías/proyectos se muestran en filtros aunque los documentos se borraron
- Posiblemente cache del navegador o state de React
- **Solución:** Gestionar etiquetas a nivel de org, no solo por documento

---

## Features Para Mañana

### 1. Sistema de Etiquetas por Organización
- Endpoint para CRUD de tags/categories
- Asignar documentos a etiquetas existentes
- UI para crear/eliminar etiquetas

### 2. Cache Admin
- Endpoint `POST /admin/cache/clear`
- O auto-invalidar en upload/delete

### 3. Testing E2E
- Subir archivo limpio (sin comillas)
- Verificar flujo completo: upload → query → respuesta correcta

---

## Archivos Modificados Hoy

```
src/verity/modules/data/
├── __init__.py          # Exports ValueResolver
├── value_resolver.py    # NUEVO - 100% data-driven
├── entity_resolver.py   # OBSOLETO (no eliminar aún)
├── schemas.py           # TablePreview, updated DataEngineResponse
├── sandbox.py           # Structured table format, quote cleaning
├── engine.py            # Table formatting, cache.clear_all()

src/verity/modules/documents/
├── service.py           # JSON persistence

src/verity/modules/agent/
├── service.py           # Category/project filtering in intent
```

---

## Comandos Útiles

```powershell
# Limpiar uploads
Remove-Item uploads\* -Force

# Ver documentos guardados
Get-Content uploads\documents_db.json

# Test de query
.venv\Scripts\python -c "
import requests
r = requests.post('http://localhost:8000/agent/chat', json={'message': 'cuantos contratos tiene Tlapehuala?'})
print(r.json()['message']['content'])
"

# Test directo del DataEngine
.venv\Scripts\python -c "
import asyncio
from verity.modules.data.engine import DataEngine
async def test():
    engine = DataEngine()
    response = await engine.query(
        user_query='cuantos contratos tiene Tlapehuala?',
        dataset_id='test',
        file_path='<uuid>_contratos.csv'
    )
    print(response.answer)
asyncio.run(test())
"
```

---

## Estado Actual

| Component | Status |
|-----------|--------|
| ValueResolver | ✅ Implementado |
| Table Rendering | ✅ Implementado |
| Document Persistence | ✅ Implementado |
| Intent Filter by Category | ✅ Implementado |
| Quote Cleaning | ⚠️ Código listo, cache stale |
| Tag Management | ❌ Pendiente |
| Cache Admin | ❌ Pendiente |

---

## Próximo Paso Recomendado

1. **Reiniciar servidor backend** (kill uvicorn, start fresh)
2. **Limpiar uploads/** 
3. **Subir archivo CSV limpio** (sin comillas en valores)
4. **Probar query** "cuantos contratos tiene Tlapehuala?"
5. Si funciona, implementar Tag Management
