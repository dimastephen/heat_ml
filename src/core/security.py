from datetime import timedelta,datetime
from typing import Dict, Any, Optional
from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from src.config import settings


def create_token(data: Dict[str, Any], expires_delta: timedelta, scope: str) -> str:
    expires = datetime.now() + expires_delta
    to_encode = data.copy()
    to_encode.update({
        "exp": expires,
        "iat": datetime.now(),
        "scope": scope,
    })
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGO_SECRET_KEY)

    return encoded_jwt


def verify_token(token: str, expected_scope: str) ->Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token,settings.JWT_SECRET_KEY,settings.JWT_ALGO_SECRET_KEY)
        if payload.get("scope")!=expected_scope:
            return None
        return payload
    except jwt.JWTError:
        return None


def create_access_token(data: Dict[str, Any]) -> str:
    expires_delta = timedelta(minutes=settings.JWT_ACCESS_TIME_MINS)
    return create_token(data=data, expires_delta=expires_delta, scope="access")


def create_refresh_token(data: Dict[str, Any]) -> str:
    expires_delta = timedelta(days=settings.JWT_REFRESH_TIME_DAYS)
    return create_token(data, expires_delta, "refresh")


# Хэш и валидация пароля
ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(hashed_password: str, password: str) -> bool:
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False
