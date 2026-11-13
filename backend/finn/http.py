"""One polite HTTP client for every source.

- Ordinary browser-like headers, nothing more. If a site refuses us (401/403),
  we accept that: the host is marked blocked for a cool-down period and callers
  fall back to other sources. We never try to defeat bot protection.
- A minimum gap between requests to the same host (see config.MIN_INTERVAL).
- Retries with backoff on 429 / 5xx / connection errors (honours Retry-After).
"""
from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config


class SourceBlocked(RuntimeError):
    """The site refused access (401/403). Use another source."""


class SourceError(RuntimeError):
    """The site answered, but not with what we expected."""


_sessions: dict[str, requests.Session] = {}
_last_hit: dict[str, float] = {}
_blocked_until: dict[str, float] = {}
_lock = threading.Lock()


def _new_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, backoff_factor=1.0, status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",), respect_retry_after_header=True, raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=8))
    s.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/json,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def session(host: str) -> requests.Session:
    with _lock:
        if host not in _sessions:
            _sessions[host] = _new_session()
        return _sessions[host]


def _throttle(host: str) -> None:
    gap = config.MIN_INTERVAL.get(host, config.DEFAULT_INTERVAL)
    with _lock:
        now = time.time()
        slot = max(now, _last_hit.get(host, 0.0) + gap)
        _last_hit[host] = slot
    if slot > now:
        time.sleep(slot - now)


def is_blocked(host: str) -> bool:
    return _blocked_until.get(host, 0.0) > time.time()


def mark_blocked(host: str, seconds: float = config.BLOCK_COOLDOWN) -> None:
    _blocked_until[host] = time.time() + seconds


def reset_blocks() -> None:
    _blocked_until.clear()


def get(url: str, *, params: dict | None = None, headers: dict | None = None,
        timeout: float = 30, stream: bool = False) -> requests.Response:
    """GET with throttle, retries and block handling. Raises SourceBlocked on 401/403."""
    host = urlparse(url).netloc
    if is_blocked(host):
        raise SourceBlocked(f"{host} refused earlier; cooling down")
    _throttle(host)
    r = session(host).get(url, params=params, headers=headers or {}, timeout=timeout, stream=stream)
    if r.status_code in (401, 403):
        mark_blocked(host)
        raise SourceBlocked(f"{host} returned {r.status_code}")
    if r.status_code >= 400:
        raise SourceError(f"{host} returned {r.status_code}")
    return r


def get_text(url: str, **kw) -> str:
    r = get(url, **kw)
    r.encoding = r.encoding or "utf-8"
    return r.text


def get_json(url: str, **kw):
    r = get(url, **kw)
    try:
        return r.json()
    except ValueError as e:
        raise SourceError(f"{urlparse(url).netloc} sent non-JSON ({len(r.content)} bytes)") from e
