"""JWT validation against Auth0 JWKS endpoint."""

import json
import os
import urllib.request
from functools import lru_cache

from fastapi import HTTPException
from jose import JWTError, jwt


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    domain = os.getenv("AUTH0_DOMAIN", "")
    url = f"https://{domain}/.well-known/jwks.json"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def verify_token(authorization: str | None) -> dict:
    """Validate a Bearer JWT and return {sub, email, permissions}."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[7:]

    try:
        header = jwt.get_unverified_header(token)
        jwks = _get_jwks()
        key = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
        if not key:
            raise HTTPException(status_code=401, detail="Unable to find matching signing key")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=os.getenv("AUTH0_MCP_AUDIENCE"),
            issuer=f"https://{os.getenv('AUTH0_DOMAIN')}/",
        )

        return {
            "sub": payload.get("sub", ""),
            "email": payload.get("email", ""),
            "permissions": payload.get("permissions", []),
        }
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
