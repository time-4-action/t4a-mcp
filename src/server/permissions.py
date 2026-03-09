"""Tool-level RBAC: permission map, context variable, and guard helper."""

import contextvars

_user_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar("user_ctx", default=None)

TOOL_PERMISSIONS: dict[str, list[str]] = {
    "identify_product":     ["read:products"],
    "get_product_price":    ["read:products"],
    "get_product_stock":    ["read:products"],
    "get_product_url":      ["read:products"],
    "get_product_variants": ["read:products"],
}


def has_permission(user_permissions: list[str], required: list[str]) -> bool:
    if "admin:all" in user_permissions:
        return True
    return all(p in user_permissions for p in required)


def set_user(user: dict) -> None:
    _user_ctx.set(user)


def require_permission(tool_name: str) -> None:
    """Raise PermissionError if the current user lacks the required permissions."""
    user = _user_ctx.get()
    if user is None:
        raise PermissionError("Unauthorized: no authenticated user in context")
    required = TOOL_PERMISSIONS.get(tool_name, [])
    if not has_permission(user["permissions"], required):
        raise PermissionError(
            f"Forbidden: tool '{tool_name}' requires permissions: {', '.join(required)}"
        )
