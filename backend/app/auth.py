from __future__ import annotations
import os
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_ISSUER = os.getenv("JWT_ISSUER", "mep-bracket-tool")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "mep-bracket-tool-users")

def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    return pwd_context.verify(pw, pw_hash)

def create_access_token(user_id: int, email: str, minutes: int = 60*24) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    if not creds:
        raise HTTPException(status_code=401, detail="Missing token")
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"], audience=JWT_AUDIENCE, issuer=JWT_ISSUER)
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
