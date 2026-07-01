import secrets

from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def require_api_key(
    request: Request,
    key: str = Security(_api_key_header),
) -> str:
    # SRP: authentication lives in one place — no route handler carries this logic
    # DIP: reads expected key from app.state (injected at startup), not from a concrete Settings import
    expected = request.app.state.api_key
    if not secrets.compare_digest(key, expected):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
    return key
