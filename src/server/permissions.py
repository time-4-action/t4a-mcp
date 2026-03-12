"""Tool-level RBAC: permission map, context variable, and guard helper."""

import contextvars
import functools

_user_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar("user_ctx", default=None)

TOOL_PERMISSIONS: dict[str, list[str]] = {
    # Products
    "identify_product":                    ["products:read"],
    "get_product_price":                   ["products:read"],
    "get_product_stock":                   ["warehouse:read"],
    "get_product_url":                     ["products:read"],
    "get_product_variants":                ["products:read"],
    # Documents
    "search_documents":                    ["documents:read"],
    "get_document":                        ["documents:read"],
    # Partners
    "get_partner":                         ["partners:read"],
    # Delivery
    "get_delivery_service_pricelists":     ["delivery:pricelists:read"],
    # Warehouse
    "get_warehouse_list":                  ["warehouse:read"],
    "get_warehouse_stock":                 ["warehouse:read"],
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


def with_permission_check(fn):
    """Decorator that catches PermissionError and returns a structured error dict.

    Wraps a tool function so that permission failures produce a clear, readable
    response for the LLM instead of a raw exception/error.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except PermissionError as e:
            msg = str(e)
            # Extract required permissions from the error message for a helpful hint
            if "requires permissions:" in msg:
                _, perms_part = msg.split("requires permissions:", 1)
                required_perms = perms_part.strip()
            else:
                required_perms = None
            response = {
                "error": "permission_denied",
                "message": msg,
            }
            if required_perms:
                response["required_permissions"] = required_perms
                response["hint"] = (
                    f"Your account is missing the '{required_perms}' permission. "
                    "Ask your administrator to grant you access in Auth0."
                )
            return response
    return wrapper
