# Verity API v2 - Contracts Reference

> Contratos definitivos para la API v2 del MVP de Verity.

---

## Base URL

```
Production: https://api.verity.app
Local:      http://127.0.0.1:8001
```

---

## Authentication

### POST `/api/v2/auth/otp/validate`

Valida OTP via n8n y emite JWT.

**Request:**
```json
{
  "wa_id": "521234567890",
  "otp": "123456"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:**

| Code | HTTP | Description |
|------|------|-------------|
| `OTP_INVALID` | 401 | Código incorrecto |
| `OTP_EXPIRED` | 401 | Código expirado |
| `OTP_RATE_LIMITED` | 429 | Demasiados intentos |
| `WHATSAPP_PROVIDER_DOWN` | 503 | n8n no disponible |
| `BAD_N8N_RESPONSE` | 502 | Respuesta inválida de n8n |

---

## Query

### POST `/api/v2/query`

Ejecuta query usando el pipeline determinista.

**Request:**
```json
{
  "question": "¿Cuántas órdenes hay?",
  "conversation_id": "optional-uuid",
  "available_tables": ["orders"],
  "context": {
    "conversation_context": {}
  }
}
```

**Response (200):**
```json
{
  "conversation_id": "abc123-uuid",
  "response": "Hay 150 órdenes en total.",
  "intent": "aggregate_metrics",
  "confidence": 0.95,
  "checkpoints": [
    {
      "tool": "semantic_resolution",
      "status": "ok",
      "execution_time_ms": 45.2,
      "output_data": {
        "metrics": [{"name": "total_orders", "definition": "COUNT(*)"}],
        "tables": ["orders"]
      }
    },
    {
      "tool": "run_table_query@1.0",
      "status": "ok",
      "execution_time_ms": 12.5,
      "output_data": {
        "table_id": "xyz",
        "rows": [[150]],
        "columns": ["total_orders"]
      }
    }
  ]
}
```

**Errors:**

| Code | HTTP | Description |
|------|------|-------------|
| `UNRESOLVED_METRIC` | 400 | Métrica no encontrada en diccionario |
| `AMBIGUOUS_METRIC` | 400 | Múltiples métricas coinciden, requiere clarificación |
| `NO_TABLE_MATCH` | 400 | Tabla requerida no disponible |
| `INVALID_FILTER` | 400 | Filtro inválido |
| `TYPE_MISMATCH` | 400 | Tipos incompatibles |
| `EMPTY_RESULT` | 404 | Query sin resultados |

---

## Observability

### GET `/api/v2/metrics`

Métricas de observabilidad del sistema.

**Response (200):**
```json
{
  "uptime_seconds": 3600.5,
  "collected_at": "2025-12-25T19:00:00Z",
  "tools": {
    "resolve_semantics@1.0": {
      "call_count": 150,
      "p50_ms": 45.2,
      "p90_ms": 85.0,
      "p99_ms": 120.5,
      "mean_ms": 52.3,
      "max_ms": 180.0,
      "errors": {
        "UNRESOLVED_METRIC": 3,
        "AMBIGUOUS_METRIC": 1
      }
    },
    "run_table_query@1.0": {
      "call_count": 147,
      "p50_ms": 12.0,
      "p90_ms": 25.0,
      "p99_ms": 45.0,
      "mean_ms": 15.2,
      "max_ms": 80.0,
      "errors": {}
    }
  },
  "global_errors": {
    "RATE_LIMITED": 5
  },
  "otp": {
    "attempts_in_window": 12,
    "unique_wa_ids": 5,
    "success_count": 10,
    "error_counts": {
      "OTP_INVALID": 2
    },
    "window_seconds": 3600
  }
}
```

---

## Health

### GET `/api/v2/health`

Estado del sistema.

**Response (200):**
```json
{
  "status": "healthy",
  "pipeline": "ok",
  "dictionary_version": "1.1",
  "context_store_active": true
}
```

---

## Error Response Format

Todos los errores siguen el mismo formato:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v2/auth/*` | 5 req | 1 min per IP |
| `/api/v2/query` | 30 req | 1 min per IP |

Cuando se excede: `429 Too Many Requests` con header `Retry-After: 60`.

---

## Payload Limits

- **Max body size:** 1 MB (configurable via `MAX_BODY_SIZE_BYTES`)
- Exceder límite: `413 Payload Too Large`

---

## Timeouts

- **Request timeout:** 30s (configurable via `REQUEST_TIMEOUT_SECONDS`)
- **n8n timeout:** 8s (configurable via `N8N_TIMEOUT_SECONDS`)

---

## Semantic Resolution Codes

### Disambiguation Flow

Cuando la métrica es ambigua:

**Request 1:**
```json
{"question": "¿cuántas órdenes?", "conversation_id": "conv-123"}
```

**Response:**
```json
{
  "response": "¿Cuál métrica quieres?\n1. total_orders\n2. delivered_orders\n3. cancelled_orders",
  "awaiting_disambiguation": true
}
```

**Request 2:**
```json
{"question": "1", "conversation_id": "conv-123"}
```

**Response:**
```json
{
  "response": "Hay 150 órdenes totales.",
  "intent": "aggregate_metrics"
}
```

---

## Version Info

- **API Version:** v2
- **Dictionary Version:** 1.1
- **OpenAPI:** `/openapi.json`
