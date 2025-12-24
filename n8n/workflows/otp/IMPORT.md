# Importar workflows OTP (n8n)

Estos workflows implementan OTP con Redis y el contrato esperado por FastAPI (Verity).

## Archivos
- `Shadowcat-OTP-Request.json`
- `Shadowcat-OTP-Validate.json`

## Import en n8n (UI)
1. Abre tu instancia de n8n.
2. Ve a **Workflows** → **Import from File**.
3. Importa ambos JSON.
4. En cada workflow:
   - Revisa el nodo **Redis** y selecciona/configura tus credenciales de Redis.
   - Guarda el workflow.

## Endpoints (webhooks)
- Request: `POST /webhook/shadowcat-otp-request`
- Validate: `POST /webhook/shadowcat-otp-validate`

En n8n, el nodo Webhook debe quedar con `responseMode = responseNode` (ya viene así).

## Contrato esperado por FastAPI
### Validate (n8n → FastAPI)
FastAPI llama a n8n con:
```json
{ "wa_id": "...", "otp": "..." }
```

Respuestas:
- Success:
```json
{ "ok": true, "wa_id": "...", "phone_number": "+52..." }
```
- Error:
```json
{ "ok": false, "error_code": "OTP_INVALID" }
```
`error_code` permitido: `OTP_INVALID | OTP_EXPIRED | OTP_RATE_LIMITED`.

## Requisitos
- Redis accesible desde n8n.
- FastAPI configurado con:
  - `N8N_BASE_URL` (host de n8n)
  - `N8N_OTP_REQUEST_PATH=/webhook/shadowcat-otp-request`
  - `N8N_OTP_VALIDATE_PATH=/webhook/shadowcat-otp-validate`

## Pruebas rápidas (curl)
### Request
```bash
curl -s -X POST "https://<tu-n8n>/webhook/shadowcat-otp-request" \
  -H "Content-Type: application/json" \
  -d '{"wa_id":"wa-123","phone_number":"+521234"}'
```

### Validate
```bash
curl -s -X POST "https://<tu-n8n>/webhook/shadowcat-otp-validate" \
  -H "Content-Type: application/json" \
  -d '{"wa_id":"wa-123","otp":"123456"}'
```

> Nota: el envío real por WhatsApp depende del proveedor/nodo que uses (WhatsApp Cloud API / Twilio / etc.).
