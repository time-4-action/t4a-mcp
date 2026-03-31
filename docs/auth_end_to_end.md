# MCP Authentication — Full End-to-End Details

This document covers the complete authentication flow between the Next.js chat app and the MCP server, from login to tool execution. It covers both sides: the **client (Next.js)** and the **server (Python/FastAPI MCP)**.

---

## Architecture Overview

```
Browser
  └─► Next.js App (auth0 session cookie)
        └─► POST /api/chat
              ├─ auth0.getSession()          → verify user is logged in
              ├─ auth0.getAccessToken()      → get Auth0 JWT for MCP API
              └─ createMCPClient({ SSE })    → connect to MCP server
                    Authorization: Bearer <JWT>
                          │
                          ▼
                   MCP Server (Python)
                    ├─ AuthMiddleware        → extract + validate JWT
                    ├─ verify_token()        → JWKS, RS256, aud, iss, exp
                    ├─ set_user(ctx)         → store claims in ContextVar
                    └─ require_permission()  → per-tool RBAC check
```

---

## Part 1: Client Side (Next.js App)

### 1.1 Auth0 Client Configuration — `lib/auth.ts`

```ts
export const auth0 = new Auth0Client({
  authorizationParameters: {
    scope: "openid profile email offline_access",
    audience: process.env.AUTH0_MCP_AUDIENCE,
  },
});
```

**Key points:**

- `audience` is set to `AUTH0_MCP_AUDIENCE` (e.g., `https://api.time-4-action.com`).
- Setting an audience causes Auth0 to issue an **Access Token** (JWT) instead of an opaque token. Without `audience`, Auth0 issues an opaque token usable only for the `/userinfo` endpoint — not for API calls.
- `offline_access` scope requests a **Refresh Token**, allowing the SDK to silently renew the Access Token without re-prompting the user to log in.
- This configuration applies globally — every login in the app will request this audience.

### 1.2 Getting the Access Token — `app/api/chat/route.ts:346`

```ts
const { token: accessToken } = await auth0.getAccessToken();
```

- `auth0.getAccessToken()` reads the current Auth0 session (from the encrypted session cookie). If the Access Token has expired, the SDK uses the stored Refresh Token to silently obtain a new one from Auth0's `/oauth/token` endpoint.
- Returns the raw JWT string (or `undefined` if no session exists).

### 1.3 Debug Logging of the Token

Before connecting, the code decodes (but does NOT verify) the token payload to log debug info:

```ts
const payload = JSON.parse(Buffer.from(accessToken.split(".")[1], "base64url").toString());
console.log("[MCP] token aud:", payload.aud, "| exp:", new Date((payload.exp ?? 0) * 1000).toISOString());
```

- Splits the JWT on `.`, takes the middle segment (payload), base64url-decodes it, parses JSON.
- Logs the `aud` claim (must match what the MCP server expects) and `exp` (expiry timestamp).
- If the token is opaque (not a JWT), this decode fails — a warning is logged instead:
  ```
  [MCP] token is opaque (not a JWT) — audience was not configured at login time
  ```
  This is a sign that `AUTH0_MCP_AUDIENCE` was missing or empty when the user logged in.

### 1.4 Creating the MCP Client — `app/api/chat/route.ts:357`

```ts
mcpClient = await createMCPClient({
  transport: {
    type: "sse",
    url: process.env.MCP_SERVER_URL,         // e.g. https://mcp.time-4-action.com/mcp
    headers: accessToken
      ? { Authorization: `Bearer ${accessToken}` }
      : undefined,
  },
});
mcpTools = await mcpClient.tools();
```

- Uses **SSE (Server-Sent Events)** transport. The MCP client opens a long-lived HTTP connection to the MCP server.
- The JWT is sent in the `Authorization: Bearer <token>` header on every SSE request.
- If no access token is available, headers are omitted (the MCP server will then return 401).
- `mcpClient.tools()` fetches the list of tools available from the MCP server. Tool definitions (names, descriptions, input schemas) are returned and passed to `streamText`.

### 1.5 Conditional MCP — Graceful Degradation

```ts
if (process.env.MCP_SERVER_URL) {
  try {
    // ... connect + get tools
  } catch (err) {
    console.warn("[chat] MCP unavailable, continuing without tools:", err.message);
    mcpClient = null;
    mcpTools = {};
  }
}
```

- MCP is **optional**. If `MCP_SERVER_URL` is not set, or if the connection fails (network error, 401, etc.), the chat continues without tools.
- This means the app degrades gracefully — users can still chat with Claude, just without company data access.

### 1.6 Passing Tools to Claude

```ts
const result = streamText({
  model: anthropic(modelId),
  system: systemPrompt,
  messages,
  stopWhen: stepCountIs(5),
  ...(Object.keys(mcpTools).length > 0 && { tools: mcpTools }),
  ...
});
```

- Tools are only passed to `streamText` if any were successfully fetched from the MCP server.
- `stopWhen: stepCountIs(5)` limits the model to 5 tool-call rounds (agentic steps) per request.

### 1.7 Closing the MCP Connection

```ts
onFinish: async () => {
  await mcpClient?.close();
  // ... save to MongoDB, update memory, usage tracking
}
```

- The MCP client is closed in the `onFinish` callback, after the full streaming response completes.
- Also closed in the `catch` block if `streamText` itself throws.

---

## Part 2: Server Side (Python MCP Server)

### 2.1 Authentication Middleware — `src/server/app.py`

```python
class AuthMiddleware:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            user = verify_token(auth)   # raises on failure → returns 401
            set_user(user)
        await self.app(scope, receive, send)
```

- Raw ASGI middleware — runs before FastAPI and before the MCP handler.
- Only activates for paths starting with `/mcp`.
- If `verify_token` raises any exception → immediately returns a `401 JSON` response. The MCP handler never executes.
- On success, stores the validated user claims in an async context variable via `set_user()`.

### 2.2 Token Validation — `src/server/auth.py`

#### Step 1: Header extraction
```python
if not auth_header or not auth_header.startswith("Bearer "):
    raise ValueError("Missing or malformed Authorization header")
token = auth_header[len("Bearer "):]
```

#### Step 2: Fetch JWKS (Auth0 public keys)
```python
@lru_cache(maxsize=1)
def get_jwks():
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    return requests.get(url).json()
```

- Auth0 publishes its RSA public keys at this well-known URL.
- `@lru_cache(maxsize=1)` ensures the JWKS is fetched **once per process start**, then reused for all subsequent requests. No per-request network call to Auth0.
- The JWKS response contains one or more keys, each with a `kid` (Key ID).

#### Step 3: Match signing key by `kid`
```python
header = jwt.get_unverified_header(token)
key = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
if not key:
    raise ValueError("Unable to find matching signing key")
```

- JWTs carry a `kid` in their header identifying which key was used to sign them.
- Auth0 rotates keys periodically; matching by `kid` ensures the right key is used even if multiple are present.
- If no matching key exists → `401`.

#### Step 4: Decode and verify the JWT
```python
payload = jwt.decode(
    token,
    key,
    algorithms=["RS256"],
    audience=AUTH0_MCP_AUDIENCE,
    issuer=f"https://{AUTH0_DOMAIN}/",
)
```

The `jose` library verifies all of the following in one call:

| Check | Claim | What it proves |
|---|---|---|
| **Signature** | (header + payload) | Auth0 signed this token with its private RSA key |
| **Algorithm** | `alg: RS256` | Prevents algorithm confusion (no HS256 with a guessable secret) |
| **Audience** | `aud` | Token was issued specifically for this API (`AUTH0_MCP_AUDIENCE`) |
| **Issuer** | `iss` | Token came from your Auth0 tenant (not some other Auth0 tenant) |
| **Expiry** | `exp` | Token is not expired |

If any check fails → exception → `401`.

#### Step 5: Extract user claims
```python
return {
    "sub":         payload.get("sub", ""),         # Auth0 user ID  e.g. "auth0|abc123"
    "email":       payload.get("email", ""),        # user email
    "permissions": payload.get("permissions", []),  # RBAC permissions list
}
```

### 2.3 Async Context Storage — `src/server/permissions.py`

```python
_user_ctx: ContextVar[dict | None] = ContextVar("user_ctx", default=None)

def set_user(user: dict) -> None:
    _user_ctx.set(user)

def get_user() -> dict | None:
    return _user_ctx.get()
```

- `ContextVar` is Python's async-safe per-task storage (similar to thread-local but for coroutines).
- Each concurrent request gets its own isolated copy of the user. No risk of one request's user leaking into another.

### 2.4 Per-Tool RBAC — `src/server/permissions.py`

```python
TOOL_PERMISSIONS = {
    "identify_product":    ["products:read"],
    "get_product_stock":   ["warehouse:read"],
    "search_documents":    ["documents:read"],
    "get_partner":         ["partners:read"],
    # ...
}

def require_permission(tool_name: str) -> None:
    user = get_user()
    perms = user.get("permissions", [])
    if "admin:all" in perms:
        return   # admin bypasses all checks
    required = TOOL_PERMISSIONS.get(tool_name, [])
    missing = [p for p in required if p not in perms]
    if missing:
        raise PermissionError(f"Forbidden: tool '{tool_name}' requires permissions: {missing}")
```

- Every MCP tool calls `require_permission(tool_name)` as its first line before doing any work.
- Permissions come from the `permissions` claim inside the validated JWT — set in Auth0's RBAC configuration per user/role.
- `admin:all` is a wildcard that grants access to all tools.
- If permissions are insufficient → `PermissionError` → MCP returns an error response to Claude, which relays it to the user.

---

## Part 3: The JWT Itself

Auth0 issues a JWT with this structure:

```
Header:
{
  "alg": "RS256",
  "kid": "<key-id matching a key in JWKS>",
  "typ": "JWT"
}

Payload:
{
  "iss": "https://time-4-action.eu.auth0.com/",
  "sub": "auth0|<user-id>",
  "aud": ["https://api.time-4-action.com"],
  "iat": 1712345000,
  "exp": 1712348600,          // typically 1 hour after iat
  "email": "user@example.com",
  "permissions": ["products:read", "warehouse:read", "documents:read"]
}

Signature:
  RSASHA256(base64url(header) + "." + base64url(payload), Auth0_private_key)
```

- Auth0 holds the **private key** and never exposes it.
- The MCP server only needs the **public key** (fetched from JWKS) to verify the signature.
- The token is self-contained — the server does not need to call Auth0 on every request.

---

## Part 4: Environment Variables

### Client (Next.js `.env.local`)

| Variable | Value | Purpose |
|---|---|---|
| `AUTH0_ISSUER_BASE_URL` | `https://time-4-action.eu.auth0.com` | Auth0 tenant URL |
| `AUTH0_CLIENT_ID` | `UIeD1C92wPF...` | OAuth2 app client ID |
| `AUTH0_CLIENT_SECRET` | `o63lSVSu_...` | OAuth2 app client secret (server-side only) |
| `AUTH0_SECRET` | 64-char hex | Encrypts the session cookie |
| `AUTH0_BASE_URL` | `http://localhost:3000` | App base URL (for callback redirect) |
| `AUTH0_MCP_AUDIENCE` | `https://api.time-4-action.com` | API audience for the Access Token |
| `MCP_SERVER_URL` | `https://mcp.time-4-action.com/mcp` | MCP SSE endpoint |

### Server (Python MCP `.env`)

| Variable | Purpose |
|---|---|
| `AUTH0_DOMAIN` | Auth0 tenant domain (for JWKS URL + issuer check) |
| `AUTH0_MCP_AUDIENCE` | Must match `aud` claim in the token |

---

## Part 5: Security Properties Summary

| Property | Mechanism |
|---|---|
| **User identity** | JWT `sub` claim (Auth0 user ID), verified by RSA signature |
| **Token authenticity** | RSA signature verified against Auth0's public JWKS — unforgeable without Auth0's private key |
| **Token freshness** | `exp` claim checked on every request — stale tokens rejected |
| **Audience binding** | `aud` must equal `AUTH0_MCP_AUDIENCE` — prevents token reuse across APIs |
| **Issuer binding** | `iss` must equal your Auth0 tenant — prevents cross-tenant token use |
| **Algorithm pinning** | Only `RS256` accepted — prevents HS256 confusion attacks where attacker signs with the public key |
| **Per-tool RBAC** | `permissions` claim checked on every tool call — users can only call tools their role grants |
| **Admin override** | `admin:all` permission bypasses per-tool checks |
| **Context isolation** | `ContextVar` keeps user data per async task — no cross-request leakage |
| **JWKS caching** | `lru_cache` — one network call per process, not per request |
| **Graceful degradation** | If MCP is down or auth fails, chat continues without tools — user is not blocked |
| **Session cookie encryption** | `AUTH0_SECRET` encrypts the Next.js session cookie — access tokens never exposed to the browser |

---

## Part 6: Common Failure Modes

| Symptom | Likely Cause | Fix |
|---|---|---|
| `[MCP] token is opaque` in logs | `AUTH0_MCP_AUDIENCE` was not set when user logged in | Set env var, then the user must log out and back in |
| MCP 401 despite valid session | Token `aud` does not match what MCP server expects | Ensure `AUTH0_MCP_AUDIENCE` is identical on both client and server |
| Token is expired | `offline_access` scope missing → no refresh token | Add `offline_access` to `authorizationParameters.scope` in `lib/auth.ts` |
| Tool returns "Forbidden" | User's Auth0 role is missing the required permission | Add permission in Auth0 dashboard → Roles → assign to user |
| MCP unavailable, chat still works | MCP server down or unreachable | Expected behavior — graceful degradation is by design |
| `kid` not found in JWKS | Auth0 rotated keys; old key cached | Restart MCP server process to clear `lru_cache` |
