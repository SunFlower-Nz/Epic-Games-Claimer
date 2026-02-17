# Epic Games Claimer - HTTP / Browser Flow Documentation

## Overview

This document describes the authentication and claim flow used by the Epic Games Claimer.

> **Nota (v3.0.0):** A partir da v3.0.0, o **claim** (resgate) de jogos é feito via **navegador**
> (Chrome CDP ou Playwright), não mais por chamada HTTP direta ao order API. A API de orders
> retorna erros 403/captcha quando chamada diretamente. As seções de autenticação e consulta
> de jogos continuam funcionando via HTTP.

## Authentication Flow

### Device Authorization (Referência Histórica)

> **Nota:** O client_id/secret do Epic Games Launcher (EGL) atualmente retorna `400 Bad Request`
> na maioria dos cenários. A autenticação principal agora é via cookies do Chrome (EPIC_EG1)
> extraídos por CDP. Esta seção é mantida como referência técnica.

```
┌─────────────┐     1. Device Auth Request      ┌──────────────────┐
│             │ ──────────────────────────────► │                  │
│   Script    │                                  │  Epic OAuth API  │
│             │ ◄────────────────────────────── │                  │
└─────────────┘     2. device_code + user_code  └──────────────────┘
       │
       │ 3. Open browser with verification URL
       ▼
┌─────────────┐
│   Browser   │  User logs in and authorizes
└─────────────┘
       │
       │ 4. User completes authorization
       ▼
┌─────────────┐     5. Poll with device_code    ┌──────────────────┐
│             │ ──────────────────────────────► │                  │
│   Script    │                                  │  Epic OAuth API  │
│             │ ◄────────────────────────────── │                  │
└─────────────┘     6. access_token + refresh   └──────────────────┘
```

### Endpoints

#### 1. Start Device Authorization

```http
POST https://account-public-service-prod.ol.epicgames.com/account/api/oauth/deviceAuthorization
Authorization: Basic {base64(client_id:client_secret)}
Content-Type: application/x-www-form-urlencoded

prompt=login
```

**Response:**
```json
{
  "device_code": "...",
  "user_code": "A1B2C3",
  "verification_uri": "https://www.epicgames.com/activate",
  "verification_uri_complete": "https://www.epicgames.com/activate?userCode=A1B2C3",
  "expires_in": 600,
  "interval": 5
}
```

#### 2. Poll for Token

```http
POST https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token
Authorization: Basic {base64(client_id:client_secret)}
Content-Type: application/x-www-form-urlencoded

grant_type=device_code&device_code={device_code}
```

**Response (pending):**
```json
{
  "errorCode": "errors.com.epicgames.account.oauth.authorization_pending",
  "message": "Authorization pending..."
}
```

**Response (success):**
```json
{
  "access_token": "eg1~...",
  "expires_in": 7200,
  "expires_at": "2025-01-15T12:00:00.000Z",
  "refresh_token": "...",
  "refresh_expires": 28800,
  "refresh_expires_at": "2025-01-15T18:00:00.000Z",
  "account_id": "...",
  "client_id": "...",
  "displayName": "YourUsername"
}
```

#### 3. Refresh Token

```http
POST https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token
Authorization: Basic {base64(client_id:client_secret)}
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token={refresh_token}
```

---

## Catalog / Free Games

### Get Free Games (GraphQL)

```http
POST https://store.epicgames.com/graphql
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "query": "query searchStoreQuery(...) { ... }",
  "variables": {
    "category": "games/edition/base|bundles/games|editors|software/edition/base",
    "country": "BR",
    "locale": "pt-BR",
    "freeGame": true,
    "count": 40,
    "start": 0
  }
}
```

### Check Ownership (Entitlements)

```http
GET https://entitlement-public-service-prod08.ol.epicgames.com/entitlement/api/account/{account_id}/entitlements?count=5000
Authorization: Bearer {access_token}
```

---

## Claiming Games (via Browser)

> **v3.0.0:** O resgate agora é feito via navegador (Chrome CDP ou Playwright).
> O script navega até a página da loja, clica em "Get" / "Place Order", lida com
> age gate (jogos 18+), e verifica o entitlement após a compra.

### Fluxo do Browser

```
1. Abrir https://store.epicgames.com/pt-BR/p/{slug}
2. Verificar se já possui o jogo (botão "In Library")
3. Clicar "Get" → "Place Order"
4. Aguardar confirmação ("Thank you" / "Obrigado")
5. Verificar entitlement via API (namespace match)
```

### Order API (Referência Histórica)

> **Nota:** Esta API retorna 403/captcha quando chamada diretamente sem contexto
> de browser. Mantida como referência técnica.

```http
POST https://order-processor-prod.ol.epicgames.com/api/v1/user/{account_id}/orders
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "offerId": "{offer_id}",
  "namespace": "{namespace}",
  "country": "BR",
  "locale": "pt-BR",
  "useDefault": true,
  "lineOffers": [
    {
      "offerId": "{offer_id}",
      "quantity": 1,
      "namespace": "{namespace}"
    }
  ]
}
```

**Response Codes:**
- `200` - Successfully claimed
- `409` - Already owned
- `401` - Unauthorized (token expired)
- `400` - Bad request (invalid offer)

---

## Session Management

### Session File Format

The session is stored in `data/session.json`:

```json
{
  "access_token": "eg1~...",
  "refresh_token": "...",
  "account_id": "abc123...",
  "display_name": "YourUsername",
  "expires_at": "2025-01-15T12:00:00+00:00",
  "refresh_expires_at": "2025-01-15T18:00:00+00:00",
  "cookies": {}
}
```

### Token Lifecycle

1. **Access Token**: Valid for ~2 hours
2. **Refresh Token**: Valid for ~8 hours
3. **Auto-refresh**: Script automatically refreshes before expiration
4. **Re-authorization**: If refresh token expires, user must authorize again

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EPIC_CLIENT_ID` | Launcher ID | OAuth client ID |
| `EPIC_CLIENT_SECRET` | Launcher secret | OAuth client secret |
| `SESSION_FILE` | `data/session.json` | Session storage path |
| `DATA_DIR` | `data` | Data directory |
| `LOG_BASE_DIR` | `logs` | Logs directory |
| `USE_EXTERNAL_FREEBIES` | `false` | Use external API |
| `TIMEOUT` | `30` | Request timeout (seconds) |
| `EPIC_EG1` | - | Fallback token from browser |

---

## Security Notes

1. **Never commit** `.env` or `session.json` to git
2. **Session tokens** are equivalent to being logged in
3. **Device auth** is secure - no password stored locally
4. **Refresh tokens** allow persistent access without re-login
