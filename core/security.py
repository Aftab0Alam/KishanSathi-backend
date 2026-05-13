from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.config import settings
from loguru import logger

security_scheme = HTTPBearer(auto_error=False)  # auto_error=False allows optional auth


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    """Decode JWT token, return None if invalid."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug(f"JWT decode failed: {e}")
        return None


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
) -> dict:
    """Require authenticated user. Raises 401 if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return {"user_id": user_id, "role": payload.get("role", "farmer"), "email": payload.get("email")}


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
) -> Optional[dict]:
    """Return user if authenticated, or None if not. Does NOT raise 401."""
    if not credentials:
        return None
    payload = _decode_token(credentials.credentials)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return {"user_id": user_id, "role": payload.get("role", "farmer"), "email": payload.get("email")}
