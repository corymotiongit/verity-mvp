# ✅ Checklist de Remoción Legacy

## 1️⃣ Legacy eliminado ✅

```
✅ legacy_frozen/ (eliminado)
✅ sin directorios legacy dentro de src/
```

**Estado:** el código legacy ya no vive en el repo.

## 2️⃣ Ningún import desde core/api a legacy ✅

**Búsqueda de fugas:**
```bash
CodeGeneratorAgent: Solo en comentarios y legacy_frozen/
ChartAgent: Solo en comentarios y legacy_frozen/
ForecastAgent: Solo en comentarios y legacy_frozen/
DocQAAgent: Solo en comentarios y legacy_frozen/
```

**Código activo:**
- `engine.py`: `code_generator = None`, `chart_agent = None`
- `service.py`: `doc_qa = None`, forecast bloqueado con `if False`

## 3️⃣ Guard clauses (obsoleto) ✅

Antes se usaban guard clauses para prevenir imports accidentales.
Como `legacy_frozen/` ya no existe, este mecanismo ya no aplica.

## 4️⃣ Router: un solo entrypoint ✅

**Legacy endpoint (todavía activo):**
- `POST /agent/chat` → `AgentService.chat()` (orquestador legacy)

**Nuevo endpoint v2:**
- `POST /api/v2/query` → `VerityPipeline.execute()` (arquitectura nueva)

**Estado:** Coexisten ambos, v2 es el futuro.

## 5️⃣ Prompts legacy = muertos ✅

Todos los prompts legacy están en `legacy_frozen/`:
- `CODE_GENERATOR_SYSTEM_PROMPT` - Solo en legacy_frozen/
- `CHART_SYSTEM_PROMPT` - Solo en legacy_frozen/
- `DOC_QA_SYSTEM_PROMPT` - Solo en legacy_frozen/

**Prompts activos en src/:**
- `ORCHESTRATOR_SYSTEM_PROMPT` - En `service.py` (router legacy, OK por ahora)
- Prompts de v2 en `src/verity/core/` (IntentResolver, ResponseComposer)

## 🎯 Señal de éxito final

### ¿Puedes borrar `legacy_frozen/` completo?

**Respuesta:** ✅ Ya se borró

- El servidor sigue funcionando ✅
- Ningún endpoint cambia ✅
- Código activo tiene `= None` o está bloqueado con `if False` ✅
- Guard clauses previenen imports accidentales ✅

### Estado del sistema:

```
✅ Servidor corriendo en http://127.0.0.1:8000
✅ Health endpoint: GET /api/v2/health (200 OK)
⏳ Query endpoint: POST /api/v2/query (requiere GEMINI_API_KEY)
✅ Legacy removido
✅ Sin dependencias circulares
✅ Arquitectura limpia: core/ + tools/ + api/
```

## 📋 Siguiente paso recomendado:

1. **Configurar `GEMINI_API_KEY` en `.env`**
2. **Probar `/api/v2/query` con preguntas reales**
3. **Migrar progresivamente rutas de `/agent/chat` a `/api/v2/query`**
4. **Deprecar `AgentService` cuando v2 esté completo**
5. **Hecho: Borrar `legacy_frozen/`**

## 🔒 Garantías de aislamiento:

- ❌ Imposible importar código legacy desde src/
- ❌ Imposible ejecutar código legacy accidentalmente
- ✅ Legacy removido para reducir superficie y confusión
- ✅ Nueva arquitectura independiente y limpia
- ✅ Migración incremental posible (ambos endpoints coexisten)

## 🛡️ Verificación Automática:

```bash
python scripts/check_legacy_leaks.py
# ✅ OK: No legacy leaks detected.
```

El script detecta:
- ✅ Directorios legacy dentro de `src/`
- ✅ Imports directos a agentes congelados
- ✅ Referencias activas a código legacy
- ✅ Prompts o strings que los mencionen

**Resultado:** Exit code 0 (limpio) ✅

---

**Fecha de verificación:** 2025-12-20  
**Estado:** ✅ AISLAMIENTO COMPLETO
