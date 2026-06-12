from __future__ import annotations

import ipaddress
import urllib.parse


def parse_http_url(value: str, *, field_name: str) -> urllib.parse.ParseResult:
    if any(char.isspace() for char in value):
        raise ValueError(f"{field_name} must not contain whitespace")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"{field_name} must use http or https")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not include credentials")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} must not include query or fragment values")
    try:
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{field_name} must include a valid host and port") from exc
    if not hostname:
        raise ValueError(f"{field_name} must include a hostname")
    return parsed


def is_loopback_host(hostname: str) -> bool:
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def is_loopback_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return is_loopback_host(parsed.hostname or "")
