"""Authentication helpers for OfferGo."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone


USERNAME_MIN_LENGTH = 4
USERNAME_MAX_LENGTH = 20
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 14
AUTH_COOKIE_NAME = "offergo_sid"

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_password_policy() -> dict[str, int | str]:
    return {
        "usernameMinLength": USERNAME_MIN_LENGTH,
        "usernameMaxLength": USERNAME_MAX_LENGTH,
        "passwordMinLength": PASSWORD_MIN_LENGTH,
        "passwordMaxLength": PASSWORD_MAX_LENGTH,
        "passwordCompositionRule": "密码至少包含大写字母、小写字母、数字、符号中的任意两类",
    }


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> str:
    value = username.strip()
    if len(value) < USERNAME_MIN_LENGTH or len(value) > USERNAME_MAX_LENGTH:
        raise ValueError(f"用户名长度需为 {USERNAME_MIN_LENGTH}-{USERNAME_MAX_LENGTH} 位")
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError("用户名仅支持字母、数字和下划线")
    return value


def validate_password(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"密码长度需为 {PASSWORD_MIN_LENGTH}-{PASSWORD_MAX_LENGTH} 位")

    groups = 0
    groups += int(any(char.islower() for char in password))
    groups += int(any(char.isupper() for char in password))
    groups += int(any(char.isdigit() for char in password))
    groups += int(any(not char.isalnum() for char in password))

    if groups < 2:
        raise ValueError("密码至少包含大写字母、小写字母、数字、符号中的任意两类")
    return password


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
    return _b64encode(derived), _b64encode(salt)


def verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    salt = _b64decode(password_salt)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000)
    return hmac.compare_digest(_b64encode(derived), password_hash)


def new_user_id() -> str:
    return uuid.uuid4().hex


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def session_expires_at() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE_SECONDS)).isoformat()


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(raw: str) -> bytes:
    return base64.b64decode(raw.encode("ascii"))
