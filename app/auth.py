"""Password hashing and JWT issue/verify."""
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# bcrypt truncates silently past 72 bytes and newer versions raise instead.
# Schemas reject longer passwords up front so this is never hit at runtime.
BCRYPT_MAX_BYTES = 72

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(plain: str) -> str:
    """bcrypt with a per-password salt. Deliberately slow, which is the point."""
    return bcrypt.hashpw(plain.encode()[:BCRYPT_MAX_BYTES], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:BCRYPT_MAX_BYTES], hashed.encode())
    except ValueError:
        # Stored hash is malformed. Fail closed rather than raising a 500.
        return False


def create_access_token(user_id: int) -> str:
    s = get_settings()
    expires = datetime.now(UTC) + timedelta(minutes=s.access_token_expire_minutes)
    # "sub" must be a string per the JWT spec; python-jose will not complain but
    # other verifiers will.
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the bearer token to a User, or 401.

    Every protected route depends on this, which is what stops one user from
    reading another user's entries.
    """
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise CREDENTIALS_ERROR
    except JWTError:
        raise CREDENTIALS_ERROR from None

    user = db.get(User, int(user_id))
    if user is None:
        # The token is valid but the account is gone.
        raise CREDENTIALS_ERROR
    return user
