"""Stdlib authenticated encryption, blind indexes, and synthetic-text guards.

No extra packages are required. Demo defaults are for synthetic local use only;
set ARIA_SECRET_KEY and ARIA_BLIND_SALT in any shared environment.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from typing import Any, Optional

SYN_PREFIX = "SYN:"
_SYNTHETIC_ALIASES = ("SYN:", "SYNTHETIC:")

_DEMO_SECRET = "aria-synthetic-master-key-32bytes!"
_DEMO_SALT = "aria-salt-2026!"


def master_key() -> bytes:
    return os.environ.get("ARIA_SECRET_KEY", _DEMO_SECRET).encode("utf-8")


def audit_key() -> bytes:
    return hashlib.sha256(master_key() + b"|audit-hmac-v1").digest()


def phone_hash(phone: str, salt: Optional[str] = None) -> str:
    """Salted blind index so phone numbers are not stored or queried in the clear."""
    normalized = re.sub(r"[\s\-+()]", "", str(phone))
    active_salt = salt or os.environ.get("ARIA_BLIND_SALT", _DEMO_SALT)
    return hashlib.sha256(f"{active_salt}:{normalized}".encode("utf-8")).hexdigest()


def derive_idempotency_key(*parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str).encode("utf-8")
    return "idm-" + hashlib.sha256(payload).hexdigest()[:32]


def ensure_synthetic_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    value = str(text).strip()
    if value in ("", "[PURGED]", "[REDACTED]"):
        return value
    for alias in _SYNTHETIC_ALIASES:
        if value.startswith(alias):
            rest = value[len(alias) :].lstrip()
            return f"{SYN_PREFIX}{rest}" if rest else SYN_PREFIX
    return f"{SYN_PREFIX}{value}"


def validate_synthetic_text(text: Optional[str], *, required: bool = True) -> None:
    if text is None:
        if required:
            raise ValueError("Synthetic text is required")
        return
    value = str(text)
    if not required and value == "":
        return
    if value in ("[PURGED]", "[REDACTED]"):
        return
    if not value.startswith(SYN_PREFIX):
        raise ValueError(f"Free-text fields must start with '{SYN_PREFIX}'")
    body = value[len(SYN_PREFIX) :]
    if "@" in body:
        raise ValueError("Email addresses are not allowed in synthetic text")
    if re.search(r"\b\d{10,}\b", body):
        raise ValueError("Phone-like digit runs are not allowed in synthetic text")


def redact_pii_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    redacted = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[EMAIL_REDACTED]", text)
    redacted = re.sub(r"(\+?\d{1,3}[\s-]?)?\(?\d{3,5}\)?[\s.-]?\d{3,5}[\s.-]?\d{4}\b", "[PHONE_REDACTED]", redacted)
    redacted = re.sub(r"\b\d{10}\b", "[PHONE_REDACTED]", redacted)
    redacted = re.sub(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[ID_REDACTED]", redacted)
    redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]", redacted)
    return redacted


_REDACT_KEY_FRAGMENTS = (
    "phone",
    "name",
    "ssn",
    "aadhaar",
    "email",
    "dob",
    "note_text",
    "summary",
    "complaint",
    "sbar",
    "rationale",
)


def sanitize_details(obj: Any) -> Any:
    """Keep operational metadata; strip obvious PII before audit write."""
    if isinstance(obj, str):
        return redact_pii_text(obj)
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _REDACT_KEY_FRAGMENTS):
                out[key] = "[REDACTED]"
            else:
                out[key] = sanitize_details(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [sanitize_details(item) for item in obj]
    return obj


def _seal(key: bytes, text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    nonce = secrets.token_bytes(16)
    data = str(text).encode("utf-8")
    derived = hashlib.sha256(key).digest()
    stream = bytearray()
    counter = 0
    while len(stream) < len(data):
        stream.extend(hmac.new(derived, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    cipher = bytes(byte ^ mask for byte, mask in zip(data, stream[: len(data)]))
    tag = hmac.new(derived, b"aria:" + nonce + cipher, hashlib.sha256).digest()[:16]
    return base64.b64encode(nonce + tag + cipher).decode("utf-8")


def _open(key: bytes, cipher_b64: Optional[str]) -> Optional[str]:
    if not cipher_b64 or cipher_b64 in ("[PURGED]", "[REDACTED]"):
        return cipher_b64
    try:
        raw = base64.b64decode(cipher_b64)
        if len(raw) < 32:
            return "[INVALID]"
        nonce, tag, cipher = raw[:16], raw[16:32], raw[32:]
        derived = hashlib.sha256(key).digest()
        expected = hmac.new(derived, b"aria:" + nonce + cipher, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(tag, expected):
            return "[INVALID]"
        stream = bytearray()
        counter = 0
        while len(stream) < len(cipher):
            stream.extend(hmac.new(derived, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
            counter += 1
        plaintext = bytes(byte ^ mask for byte, mask in zip(cipher, stream[: len(cipher)]))
        return plaintext.decode("utf-8")
    except (ValueError, TypeError, UnicodeDecodeError):
        return "[ERROR]"


def enc_master(text: Optional[str]) -> Optional[str]:
    return _seal(master_key(), text)


def dec_master(ciphertext: Optional[str]) -> Optional[str]:
    return _open(master_key(), ciphertext)


def enc_with_key(key: bytes, text: Optional[str]) -> Optional[str]:
    return _seal(key, text)


def dec_with_key(key: bytes, ciphertext: Optional[str]) -> Optional[str]:
    return _open(key, ciphertext)
