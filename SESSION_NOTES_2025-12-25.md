# Verity MVP - Session Notes (Dec 25, 2025)

## Resumen de la Sesión

### Contexto importante (incidente)
- **n8n está caído / la instancia se apagó.**
  - Esto impacta el flujo real de OTP v2 (`POST /api/v2/auth/otp/validate`) cuando **NO** está habilitado el bypass de dev.
  - Durante dev local existe `AUTH_OTP_INSECURE_DEV_BYPASS=true` (solo no-prod) que emite JWT sin validar contra n8n (usar solo para confirmar flujos end-to-end, no para prod).

---

## Lo que se implementó hoy

### 1) Semantics v1.1 (aditivo, sin tocar el core)
Objetivo: ampliar métricas/aliases, agregar desambiguación 1 turno, contexto conversacional leve y ajustar scoring/confidence penalizando supuestos implícitos.

**A) Contexto conversacional leve (TTL in-process)**
- **Nuevo:** `src/verity/core/semantics_context.py`
  - `SemanticsContextStore` con TTL (30 min)
  - Guarda `last_metric`, `last_table`, `last_alias`
  - Guarda `pending_candidates` para desambiguación (1 turno)

**B) conversation_id estable (sin reordenar pipeline)**
- **Actualizado:** `src/verity/core/pipeline.py`
  - `execute(..., conversation_id: str | None = None)` ahora acepta un `conversation_id` externo

**C) Endpoint v2 integra contexto + desambiguación**
- **Actualizado:** `src/verity/api/routes/query_v2.py`
  - `QueryRequest` ahora acepta `conversation_id` opcional
  - Pipeline + checkpoint storage ahora son singletons in-process (no se reinician por request)
  - Inyecta `context["conversation_context"]` hacia `resolve_semantics`
  - Maneja `AmbiguousMetricException` devolviendo una **pregunta corta con opciones** y guardando candidatos
  - Siguiente request acepta respuesta `"1".."5"` o el **nombre canónico exacto** y continúa

**D) Metrics map ampliado (aliases + filtros deterministas por métrica)**
- **Actualizado:** `src/verity/data/dictionary.json`
  - Bump `version: 1.1`
  - Se agregaron aliases más realistas
  - Se agregaron métricas por status con filtros automáticos:
    - `delivered_orders` (filter `order_status = delivered`)
    - `cancelled_orders` (filter `order_status = cancelled`)
    - `pending_orders` (filter `order_status = pending`)

**E) Ajuste de scoring/confidence (penaliza supuestos implícitos)**
- **Actualizado:** `src/verity/tools/resolve_semantics/__init__.py`
  - Soporta `conversation_context` en input
  - Heurística `_looks_like_followup()` para identificar follow-up
  - “Context boost” conservador:
    - +3.0 si coincide con `last_metric`
    - +1.5 si la métrica vive en `last_table`
    - Solo si `base_score >= 70` (no rescata matches débiles)
  - Expone campos de auditoría en el match:
    - `base_match_score`, `context_boost`, `context_boost_reasons`
  - Se afinó el `except` demasiado general en el lookup de tabla a `except KeyError`.

---

## Testing / Calidad

### Tests
- Se hicieron deterministas tests que dependían de env flags (local `.env`):
  - `tests/test_api.py` fuerza `LEGACY_COMPAT_ENABLED=true` para tests que prueban legacy endpoints (/agent/*).
  - `tests/test_auth_otp_jwt.py` fuerza `LEGACY_COMPAT_ENABLED=true` para test legacy `/otp/validate`.
  - `tests/test_auth_v2_otp_validate.py` fuerza `AUTH_OTP_INSECURE_DEV_BYPASS=false` para ejercer el contrato real con n8n mocked.

Resultado:
- `pytest`: **44 passed**.

---

## Estado actual (lo importante para continuar)

### Semantics v1.1
- Cambios principales ya están integrados y pasando tests.
- Falta validar manualmente dos flujos:
  1) **Ambigüedad guiada**: pregunta que dispare `AmbiguousMetricException` → UI/API devuelve opciones → siguiente turno responde “1” y ejecuta.
  2) **Follow-up con contexto**: pregunta resoluble → pregunta corta tipo “¿y ahora?” → verificar que el boost aplica de forma conservadora y que la confidence refleja penalización por supuesto.

### OTP / n8n
- n8n caído: cualquier validación OTP real contra webhook va a fallar.
- Para dev local (solo no-prod) existe bypass:
  - `AUTH_OTP_INSECURE_DEV_BYPASS=true`

---

## Comandos útiles

```powershell
# Backend (modo v2-only; legacy 410)
$env:LEGACY_COMPAT_ENABLED='false'
.\scripts\run.ps1

# Correr tests
F:/Github-Projects/verity-mvp/.venv/Scripts/python.exe -m pytest -q

# Health
$base='http://127.0.0.1:8001'
Invoke-RestMethod -Method Get -Uri ($base + '/api/v2/health') | ConvertTo-Json -Depth 6

# (Solo dev local) habilitar bypass OTP v2 si n8n está abajo
$env:AUTH_OTP_INSECURE_DEV_BYPASS='true'
```

---

## Próximos pasos (Antigravity)

1) **Restaurar n8n** (o apuntar `N8N_BASE_URL` a una instancia viva) y volver a probar el flujo real de OTP.
2) **Validación manual Semantics v1.1** vía `/api/v2/query`:
   - Probar ambigüedad + respuesta “1” con `conversation_id` fijo.
   - Probar follow-up con pregunta corta y confirmar comportamiento de boost/penalización.
3) (Luego) remover/limitar el bypass de dev si ya no se necesita, y confirmar e2e sin bypass.
