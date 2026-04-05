from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import app.config as settings

api_key_scheme = APIKeyHeader(name="x-api-key", auto_error=False)


async def require_api_key(key: str = Security(api_key_scheme)):
    if not key or key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing x-api-key header",
        )
    return key
