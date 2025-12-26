# Verity Auth & Data Runbook

> Guía operativa para autenticación OTP y gestión de datos.

---

## 1. Arquitectura OTP

```
┌─────────────┐    POST /otp/validate    ┌──────────┐
│   Frontend  │ ───────────────────────▶ │ FastAPI  │
└─────────────┘                          └────┬─────┘
                                              │
                    POST /webhook/otp-validate│
                                              ▼
┌─────────────┐    Validate + Consume    ┌──────────┐
│    Redis    │ ◀──────────────────────  │   n8n    │
│  (OTP TTL)  │                          └──────────┘
└─────────────┘
```

**Flujo:**
1. Usuario solicita OTP via WhatsApp
2. n8n genera OTP, guarda en Redis (TTL 5 min), envía via WhatsApp
3. Usuario ingresa OTP en frontend
4. Frontend → FastAPI → n8n valida contra Redis
5. FastAPI emite JWT + upsert identity en Supabase

---

## 2. Troubleshooting

### n8n caído / no responde

**Síntoma:**
```json
{"error": {"code": "WHATSAPP_PROVIDER_DOWN", "message": "..."}}
```

**Diagnóstico:**
```powershell
# Verificar n8n
curl https://shadowcat.cloud/webhook/health

# Logs de FastAPI
grep "provider_down" /var/log/verity/api.log
```

**Workaround (solo dev):**
```powershell
$env:AUTH_OTP_INSECURE_DEV_BYPASS='true'
# ⚠️ NUNCA en producción
```

**Solución:**
1. Verificar instancia n8n (VM, container)
2. Revisar SSL/certificados
3. Verificar `N8N_BASE_URL` en `.env`

---

### Redis timeout / OTP expirado

**Síntoma:**
```json
{"error": {"code": "OTP_EXPIRED", "message": "El código expiró."}}
```

**Diagnóstico:**
```bash
# Verificar TTL de OTP
redis-cli -u $REDIS_URL TTL "otp:521234567890"
```

**Solución:**
- Si TTL = -2: OTP ya consumido o nunca existió
- Si TTL = -1: Sin expiración (bug)
- Solicitar nuevo OTP

---

### Rate limited (OTP)

**Síntoma:**
```json
{"error": {"code": "OTP_RATE_LIMITED", "message": "Demasiados intentos."}}
```

**Diagnóstico:**
```bash
# Ver intentos en Redis
redis-cli -u $REDIS_URL GET "otp_attempts:521234567890"
```

**Solución:**
- Esperar window (5 min default)
- Admin puede limpiar: `DEL otp_attempts:521234567890`

---

### JWT expirado

**Síntoma:**
```json
{"error": {"code": "UNAUTHORIZED", "message": "Token expired"}}
```

**Solución:**
- Frontend debe re-autenticar via OTP
- Default TTL: 15 min (`AUTH_ACCESS_TOKEN_TTL_SECONDS`)

---

## 3. Data Pipeline Issues

### Métrica no resuelta

**Síntoma:**
```json
{"error": {"code": "UNRESOLVED_METRIC"}}
```

**Diagnóstico:**
1. Revisar `data/dictionary.json`
2. Verificar aliases de la métrica
3. Revisar logs de `resolve_semantics`

**Solución:**
- Agregar alias al diccionario
- Regenerar cache de métricas

---

### Query sin resultados

**Síntoma:**
```json
{"error": {"code": "EMPTY_RESULT"}}
```

**Diagnóstico:**
```sql
-- Verificar datos en tabla
SELECT COUNT(*) FROM orders WHERE <filtros>;
```

**Solución:**
- Ajustar filtros
- Verificar datos source

---

## 4. Recovery Procedures

### Regenerar JWT Secret

```powershell
# 1. Generar nuevo secret
$secret = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Max 256 }) -as [byte[]])

# 2. Actualizar Secret Manager
gcloud secrets versions add verity-jwt-secret --data-file=-

# 3. Restart API
kubectl rollout restart deployment/verity-api
```

**⚠️ Todos los tokens existentes serán inválidos.**

---

### Flush Redis (emergencia)

```bash
# Solo OTPs (no sesiones)
redis-cli -u $REDIS_URL KEYS "otp:*" | xargs redis-cli -u $REDIS_URL DEL

# Todo (nuclear)
redis-cli -u $REDIS_URL FLUSHDB
```

---

### Reset Rate Limits

```powershell
# In-process (dev)
# Restart del servidor limpia el store

# Redis (prod)
redis-cli -u $REDIS_URL KEYS "rate:*" | xargs redis-cli -u $REDIS_URL DEL
```

---

## 5. Environment Variables

### Auth

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_JWT_SECRET` | demo-secret | Secret para firmar tokens |
| `AUTH_JWT_ALGORITHM` | HS256 | Algoritmo de firma |
| `AUTH_ACCESS_TOKEN_TTL_SECONDS` | 900 | TTL de access tokens |
| `AUTH_INSECURE_DEV_BYPASS` | false | Bypass Redis session validation |
| `AUTH_OTP_INSECURE_DEV_BYPASS` | false | Bypass OTP validation |

### n8n

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_BASE_URL` | https://shadowcat.cloud | Base URL de n8n |
| `N8N_OTP_VALIDATE_PATH` | /webhook/shadowcat-otp-validate | Path del webhook |
| `N8N_TIMEOUT_SECONDS` | 8.0 | Timeout HTTP |

### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | true | Habilitar rate limiting |
| `RATE_LIMIT_AUTH_PER_MIN` | 5 | Requests auth/min/IP |
| `RATE_LIMIT_QUERY_PER_MIN` | 30 | Requests query/min/IP |

---

## 6. Monitoring

### Métricas clave

```powershell
# Obtener métricas
Invoke-RestMethod -Uri 'http://127.0.0.1:8001/api/v2/metrics' | ConvertTo-Json -Depth 4
```

**Alertas sugeridas:**
- `otp.error_counts.OTP_INVALID > 10/min` → Posible ataque
- `global_errors.RATE_LIMITED > 50/min` → Revisar límites
- `tools.*.p99_ms > 500` → Degradación de performance

---

## 7. Contactos

| Rol | Contacto |
|-----|----------|
| Backend | [Nombre] |
| Infra/n8n | [Nombre] |
| Frontend | [Nombre] |
