"""Server-side credential encryption helpers."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from agent_forge.config import settings


def _credential_key() -> bytes:
    raw_key = settings.credential_encryption_key or settings.jwt_secret_key or "agentforge-dev-credential-key"
    key_bytes = raw_key.encode("utf-8")
    try:
        Fernet(key_bytes)
        return key_bytes
    except Exception:
        digest = hashlib.sha256(key_bytes).digest()
        return base64.urlsafe_b64encode(digest)


def encrypt_secret(secret: str) -> str:
    if not secret:
        raise ValueError("Secret must not be empty")
    return Fernet(_credential_key()).encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_secret: str) -> str:
    try:
        return Fernet(_credential_key()).decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Credential cannot be decrypted") from exc
