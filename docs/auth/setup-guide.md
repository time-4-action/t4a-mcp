# MCP Server — Auth0 Authentication & Role-Based Access Control

This guide covers what needs to be implemented on the **MCP server** side.

---

## Overview

The MCP server needs to:
1. Validate a JWT (Auth0 access token) on every request
2. Extract the user's roles from the token
3. Guard individual tools based on required roles

---

## 1. Auth0 API Setup (Dashboard)

Before writing code, register the MCP server as an **Auth0 API**:

1. Go to **Auth0 Dashboard → Applications → APIs → Create API**
2. Set an identifier (audience), e.g. `https://mcp.your-company.com`
3. Enable **RBAC** on this API:
   - Settings tab → Enable RBAC → ON
   - Enable "Add Permissions in the Access Token" → ON
4. Add permissions (scopes) that map to tool groups, e.g.:
   - `read:products`
   - `read:orders`
   - `write:orders`
   - `read:customers`
   - `admin:all`
5. Go to **User Management → Roles**, create roles and assign the permissions above:
   - `sales` → `read:products`, `read:orders`, `read:customers`
   - `manager` → all of the above + `write:orders`
   - `admin` → `admin:all` + everything
6. Assign roles to users in **User Management → Users → [user] → Roles**

---

## 2. JWT Validation Middleware

Install dependencies (Node.js example):

```bash
npm install jose
# or
npm install jsonwebtoken jwks-rsa
```

### Using `jose` (recommended, edge-compatible):

```typescript
import { createRemoteJWKSet, jwtVerify } from "jose";

const JWKS = createRemoteJWKSet(
  new URL(`https://${process.env.AUTH0_DOMAIN}/.well-known/jwks.json`)
);

export async function verifyToken(authHeader: string | undefined): Promise<{
  sub: string;
  email: string;
  permissions: string[];
}> {
  if (!authHeader?.startsWith("Bearer ")) {
    throw new Error("Missing or invalid Authorization header");
  }

  const token = authHeader.slice(7);

  const { payload } = await jwtVerify(token, JWKS, {
    issuer: `https://${process.env.AUTH0_DOMAIN}/`,
    audience: process.env.AUTH0_MCP_AUDIENCE, // e.g. https://mcp.your-company.com
  });

  return {
    sub: payload.sub as string,
    email: (payload.email ?? "") as string,
    permissions: (payload.permissions as string[]) ?? [],
  };
}
```

### Env vars needed on the MCP server:

```env
AUTH0_DOMAIN=your-tenant.eu.auth0.com
AUTH0_MCP_AUDIENCE=https://mcp.your-company.com
```

---

## 3. Applying Auth on Each Request

In the MCP server's request handler, validate the token before processing any tool call:

```typescript
// In your SSE / HTTP handler:
app.post("/sse", async (req, res) => {
  let userContext: { sub: string; email: string; permissions: string[] };

  try {
    userContext = await verifyToken(req.headers.authorization);
  } catch (err) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  // Pass userContext into your MCP tool handlers
  handleMCPRequest(req, res, userContext);
});
```

---

## 4. Role-Based Tool Guards

Define a permission requirement per tool, then enforce it inside each tool handler:

```typescript
// permissions.ts
export const TOOL_PERMISSIONS: Record<string, string[]> = {
  get_product:        ["read:products"],
  list_products:      ["read:products"],
  get_order:          ["read:orders"],
  list_orders:        ["read:orders"],
  update_order:       ["write:orders"],
  get_customer:       ["read:customers"],
  admin_reset_cache:  ["admin:all"],
};

// Helper
export function hasPermission(userPermissions: string[], required: string[]): boolean {
  if (userPermissions.includes("admin:all")) return true; // admin bypasses everything
  return required.every((p) => userPermissions.includes(p));
}
```

In each tool handler:

```typescript
async function handleToolCall(toolName: string, args: unknown, user: UserContext) {
  const required = TOOL_PERMISSIONS[toolName] ?? [];

  if (!hasPermission(user.permissions, required)) {
    throw new MCPError({
      code: -32001,
      message: `Forbidden: tool '${toolName}' requires permissions: ${required.join(", ")}`,
    });
  }

  // ... actual tool logic
}
```

---

## 5. Returning Filtered Tool Listings (Optional but Recommended)

Instead of exposing all tools to every user and erroring at call time, you can filter the tools list at connection time based on the user's permissions:

```typescript
function getToolsForUser(permissions: string[]): Tool[] {
  return ALL_TOOLS.filter((tool) => {
    const required = TOOL_PERMISSIONS[tool.name] ?? [];
    return hasPermission(permissions, required);
  });
}

// In your MCP list_tools handler:
server.setRequestHandler(ListToolsRequestSchema, async (req, { user }) => {
  return { tools: getToolsForUser(user.permissions) };
});
```

This means Claude only sees tools the user is allowed to call — cleaner and more secure.

---

## 6. Summary of Changes on MCP Server

| What | Where |
|---|---|
| Install `jose` | `package.json` |
| Add `AUTH0_DOMAIN` + `AUTH0_MCP_AUDIENCE` env vars | `.env` on MCP server |
| `verifyToken()` middleware | `src/auth.ts` |
| `TOOL_PERMISSIONS` map + `hasPermission()` | `src/permissions.ts` |
| Call `verifyToken` in every request handler | SSE/HTTP handler |
| Guard each tool call with `hasPermission` | Each tool handler |
| Optionally filter `list_tools` response | `list_tools` handler |
