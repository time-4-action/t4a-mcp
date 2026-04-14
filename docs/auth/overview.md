# MCP Auth0 Authentication — How It Works

This document explains the full Auth0 JWT authentication flow used in this MCP server, step by step.

---

## Overview

Every request to `/mcp/*` must include a valid Auth0-issued JWT. The server validates this token, extracts the user's identity and permissions, and enforces tool-level RBAC (role-based access control) before any MCP tool executes.

---

## Step-by-Step Flow

### 1. Client sends a request with a Bearer token

```
GET /mcp/...
Authorization: Bearer <JWT>
```

### 2. `AuthMiddleware` intercepts the request (`src/server/app.py:17`)

`AuthMiddleware` is a raw ASGI middleware that runs before any FastAPI route or MCP handler. It checks every request whose path starts with `/mcp`.

```python
if scope["type"] == "http" and scope["path"].startswith("/mcp"):
    headers = dict(scope.get("headers", []))
    auth = headers.get(b"authorization", b"").decode()
    user = verify_token(auth)
    set_user(user)
```

If `verify_token` raises, middleware returns a JSON `401` immediately — the MCP handler never runs.

### 3. `verify_token` validates the JWT (`src/server/auth.py:20`)

#### a. Header check
The token must be present and start with `Bearer `. The raw JWT is extracted.

#### b. Fetch the JWKS (JSON Web Key Set)
```python
url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
```
Auth0 publishes its public RSA signing keys at this URL. The result is cached in-process with `@lru_cache(maxsize=1)` — fetched once, reused forever (until the process restarts).

#### c. Match the signing key by `kid`
JWTs carry a `kid` (Key ID) in their header. The code finds the matching key from the JWKS:
```python
header = jwt.get_unverified_header(token)
key = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
```
If no key matches → `401 Unable to find matching signing key`.

#### d. Decode and verify the JWT
```python
payload = jwt.decode(
    token,
    key,
    algorithms=["RS256"],
    audience=AUTH0_MCP_AUDIENCE,
    issuer=f"https://{AUTH0_DOMAIN}/",
)
```
The `jose` library verifies:
- **Signature** — using the matched RSA public key (RS256). Proves Auth0 signed it.
- **Algorithm** — must be `RS256`. Prevents algorithm confusion attacks.
- **Audience (`aud`)** — must match `AUTH0_MCP_AUDIENCE`. Ensures the token was issued *for this API*.
- **Issuer (`iss`)** — must match `https://{AUTH0_DOMAIN}/`. Ensures the token came from *your* Auth0 tenant.
- **Expiry (`exp`)** — checked automatically. Expired tokens are rejected.

#### e. Extract user claims
```python
return {
    "sub":         payload.get("sub", ""),         # user ID
    "email":       payload.get("email", ""),        # user email
    "permissions": payload.get("permissions", []),  # Auth0 RBAC permissions
}
```

### 4. User is stored in async context (`src/server/permissions.py:35`)

```python
_user_ctx: ContextVar[dict | None] = ContextVar("user_ctx", default=None)

def set_user(user: dict) -> None:
    _user_ctx.set(user)
```

`contextvars.ContextVar` is async-safe — each concurrent request gets its own copy of the user. No shared mutable state.

### 5. Tool-level permission check (`src/server/permissions.py:39`)

Each MCP tool calls `require_permission(tool_name)` before doing any work. It reads the user from context and checks their permissions against `TOOL_PERMISSIONS`:

```python
TOOL_PERMISSIONS = {
    "identify_product":    ["products:read"],
    "get_product_stock":   ["warehouse:read"],
    "search_documents":    ["documents:read"],
    "get_partner":         ["partners:read"],
    # ...
}
```

`has_permission` checks:
- If user has `admin:all` → allow everything.
- Otherwise → user must have **all** required permissions for that tool.

If the check fails → `PermissionError("Forbidden: tool '...' requires permissions: ...")`.

---

## Environment Variables Required

| Variable             | Purpose                                         |
|----------------------|-------------------------------------------------|
| `AUTH0_DOMAIN`       | Your Auth0 tenant domain, e.g. `dev-xxx.auth0.com` |
| `AUTH0_MCP_AUDIENCE` | API identifier configured in Auth0              |

---

## Security Properties

| Property | How it's enforced |
|---|---|
| Token authenticity | RSA signature verified against Auth0's public JWKS |
| Token freshness | `exp` claim checked by `jose.jwt.decode` |
| Right audience | `aud` claim must equal `AUTH0_MCP_AUDIENCE` |
| Right issuer | `iss` claim must equal `https://{AUTH0_DOMAIN}/` |
| Algorithm pinning | Only `RS256` accepted — prevents HS256 confusion |
| Per-tool RBAC | `permissions` claim checked on every tool call |
| Context isolation | `ContextVar` keeps user data per async task |
| Key caching | JWKS fetched once via `lru_cache` — no per-request network call |

---

## What Auth0 Actually Issues

Auth0 issues a JWT structured like:

```
Header:  { "alg": "RS256", "kid": "<key-id>", "typ": "JWT" }
Payload: {
  "iss": "https://dev-xxx.auth0.com/",
  "sub": "auth0|user123",
  "aud": ["your-api-audience"],
  "exp": 1712345678,
  "email": "user@example.com",
  "permissions": ["products:read", "warehouse:read"]
}
Signature: <RSA-SHA256 signature using Auth0's private key>
```

The server never trusts the payload without verifying the signature. Auth0 holds the private key; the server only needs the public JWKS endpoint.
