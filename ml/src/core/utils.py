"""Shared helper utilities for CardioSense."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def new_document_id(prefix: str) -> str:
    """Return a human-readable unique document id."""
    return f"{prefix}_{uuid4().hex}"


def stable_document_id(prefix: str, *parts: Any) -> str:
    """Return a deterministic document id derived from stable input parts."""
    encoded = "::".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return f"{prefix}_{digest[:32]}"


def canonical_json_hash(payload: Any) -> str:
    """Create a deterministic SHA-256 hash for structured payloads."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def pseudonymous_subject_hash(external_subject_id: Any, salt: str) -> str:
    """Hash a subject identifier into a stable pseudonymous key."""
    raw_value = f"{salt}:{external_subject_id}"
    return hashlib.sha256(raw_value.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str | None:
    """Return a SHA-256 digest for a file when present."""
    if not path.exists():
        return None

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
