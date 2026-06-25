from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import re

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all |previous |above )?instructions",
    r"disregard (your |the )?(system |previous )?prompt",
    r"you are now",
    r"act as (if )?you('re| are) (not |no longer )?an? (ai|assistant|chatbot|language model)",
    r"forget (everything|all|your instructions)",
    r"(new|your real|your true) (instructions|prompt|purpose)",
    r"jailbreak",
    r"DAN mode",
    r"developer mode",
    r"\[system\]|\<system\>",
]

_injection_re = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def detect_prompt_injection(text: str) -> bool:
    """Returns True if text contains prompt injection patterns."""
    return any(pattern.search(text) for pattern in _injection_re)


def sanitize_input(text: str, max_length: int = 4000) -> str:
    if detect_prompt_injection(text):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input contains disallowed content.",
        )
    # Trim to max length
    return text[:max_length].strip()
