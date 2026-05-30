from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Mapping


MAX_TTL_SECONDS = 3600


class CredentialBrokerError(ValueError):
    pass


@dataclass(frozen=True)
class CredentialLease:
    lease_id: str
    secret_name: str
    scopes: tuple[str, ...]
    client_id: str
    issued_at: datetime
    expires_at: datetime
    token: str = field(repr=False)
    revoked: bool = False

    def is_expired(self, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(timezone.utc)
        return current >= self.expires_at

    def audit_record(self, *, now: datetime | None = None) -> dict[str, object]:
        return {
            "lease_id": self.lease_id,
            "secret_name": self.secret_name,
            "scopes": list(self.scopes),
            "client_id": self.client_id,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ttl_seconds_remaining": max(
                0,
                int((self.expires_at - (now or datetime.now(timezone.utc))).total_seconds()),
            ),
            "revoked": self.revoked,
            "token": "[redacted]",
        }


class CredentialBroker:
    def __init__(self, *, environ: Mapping[str, str] | None = None) -> None:
        self.environ = environ if environ is not None else os.environ
        self._leases: dict[str, CredentialLease] = {}

    def issue_env_lease(
        self,
        *,
        secret_name: str,
        env_var: str,
        scopes: tuple[str, ...],
        client_id: str,
        ttl_seconds: int = 900,
        now: datetime | None = None,
    ) -> CredentialLease:
        clean_secret_name = _require_label(secret_name, "secret name")
        clean_env_var = _require_env_name(env_var)
        clean_client_id = _require_label(client_id, "client id")
        clean_scopes = _validate_scopes(scopes)
        clean_ttl = _validate_ttl(ttl_seconds)
        token = self.environ.get(clean_env_var, "").strip()
        if not token:
            raise CredentialBrokerError(f"Environment variable {clean_env_var} is not set")
        if len(token) < 8:
            raise CredentialBrokerError(f"Environment variable {clean_env_var} is too short")

        issued_at = now or datetime.now(timezone.utc)
        lease = CredentialLease(
            lease_id=secrets.token_urlsafe(18),
            secret_name=clean_secret_name,
            scopes=clean_scopes,
            client_id=clean_client_id,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=clean_ttl),
            token=token,
        )
        self._leases[lease.lease_id] = lease
        return lease

    def revoke(self, lease_id: str) -> CredentialLease:
        lease = self._leases.get(lease_id)
        if lease is None:
            raise CredentialBrokerError(f"Unknown lease id: {lease_id}")
        revoked = CredentialLease(
            lease_id=lease.lease_id,
            secret_name=lease.secret_name,
            scopes=lease.scopes,
            client_id=lease.client_id,
            issued_at=lease.issued_at,
            expires_at=lease.expires_at,
            token=lease.token,
            revoked=True,
        )
        self._leases[lease_id] = revoked
        return revoked


def _validate_ttl(value: int) -> int:
    ttl = int(value)
    if ttl < 1 or ttl > MAX_TTL_SECONDS:
        raise CredentialBrokerError(f"TTL must be between 1 and {MAX_TTL_SECONDS} seconds")
    return ttl


def _validate_scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    clean = tuple(_require_label(scope, "scope") for scope in scopes if scope.strip())
    if not clean:
        raise CredentialBrokerError("At least one scope is required")
    return clean


def _require_label(value: str, label: str) -> str:
    text = value.strip()
    if not text:
        raise CredentialBrokerError(f"{label} is required")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:._/-")
    if any(char not in allowed for char in text):
        raise CredentialBrokerError(f"{label} contains unsupported characters")
    return text


def _require_env_name(value: str) -> str:
    text = value.strip()
    if not text:
        raise CredentialBrokerError("environment variable name is required")
    if not text.replace("_", "").isalnum() or text[0].isdigit():
        raise CredentialBrokerError("environment variable name is invalid")
    return text
