import os
import time
from typing import Any, Dict

import requests
from fastapi import HTTPException, Request, status
from jose import jwt

_JWKS_CACHE: Dict[str, Any] = {"keys": None, "expires_at": 0.0}


def _auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "0") == "1"


def _jwt_settings() -> tuple[str | None, str | None, str | None]:
    pool_id = os.getenv("COGNITO_USER_POOL_ID")
    client_id = os.getenv("COGNITO_CLIENT_ID")
    region = os.getenv("COGNITO_REGION") or os.getenv("AWS_REGION")
    return pool_id, client_id, region


def _jwks_url(pool_id: str, region: str) -> str:
    return f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json"


def _get_jwks(pool_id: str, region: str) -> Dict[str, Any]:
    now = time.time()
    if _JWKS_CACHE["keys"] and _JWKS_CACHE["expires_at"] > now:
        return _JWKS_CACHE["keys"]

    try:
        response = requests.get(_jwks_url(pool_id, region), timeout=6)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Unable to load auth keys.") from exc

    jwks = response.json()
    _JWKS_CACHE["keys"] = jwks
    _JWKS_CACHE["expires_at"] = now + 3600
    return jwks


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if not auth_header:
        return None
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def _fallback_user_id(request: Request) -> str:
    return request.headers.get("x-user-id", "demo-user")


def require_user(request: Request) -> Dict[str, Any]:
    pool_id, client_id, region = _jwt_settings()
    token = _extract_bearer_token(request)

    if not pool_id or not region:
        if _auth_required():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth not configured.")
        user_id = _fallback_user_id(request)
        request.state.user_id = user_id
        return {"sub": user_id, "auth_source": "disabled"}

    if not token:
        if _auth_required():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")
        user_id = _fallback_user_id(request)
        request.state.user_id = user_id
        return {"sub": user_id, "auth_source": "anonymous"}

    jwks = _get_jwks(pool_id, region)
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    key = next((entry for entry in jwks.get("keys", []) if entry.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token.")

    issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
    options = {"verify_aud": bool(client_id)}
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=client_id if client_id else None,
            issuer=issuer,
            options=options,
        )
    except Exception as exc:  # jose raises multiple error types
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token.") from exc

    user_id = claims.get("sub") or claims.get("username") or _fallback_user_id(request)
    request.state.user_id = user_id
    return claims
