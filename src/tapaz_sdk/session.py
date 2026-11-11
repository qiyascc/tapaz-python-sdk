from __future__ import annotations

import base64
from typing import Iterable, Mapping, Optional

CLOUDFLARE_COOKIES = frozenset({"cf_clearance", "__cf_bm", "__cflb", "_cfuvid", "cf_chl_rc_m"})


def is_cloudflare(name: str) -> bool:
    lowered = name.strip().lower()
    return lowered in CLOUDFLARE_COOKIES or lowered.startswith("cf_chl")


def parse_cookie(header: Optional[str]) -> dict[str, str]:
    jar: dict[str, str] = {}
    raw = (header or "").strip()
    if raw.lower().startswith("cookie:"):
        raw = raw[7:]
    for part in raw.split(";"):
        name, sep, value = part.strip().partition("=")
        if sep and name.strip() and value.strip() and not is_cloudflare(name):
            jar[name.strip()] = value.strip()
    return jar


def set_cookies(lines: Iterable[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in lines:
        name, sep, value = line.split(";", 1)[0].strip().partition("=")
        if sep and name.strip() and not is_cloudflare(name):
            found[name.strip()] = value.strip()
    return found


def cookie_header(jar: Mapping[str, str]) -> str:
    return "; ".join(f"{name}={value}" for name, value in jar.items() if value and not is_cloudflare(name))


def gid(kind: str, value: object) -> str:
    raw = str(value).strip()
    if not raw.isdigit():
        return raw
    return base64.b64encode(f"gid://tap/{kind}/{raw}".encode()).decode().rstrip("=")


def legacy_id(value: object) -> Optional[str]:
    if value is None:
        return None
    raw = str(value)
    if raw.isdigit():
        return raw
    try:
        decoded = base64.b64decode(raw + "=" * (-len(raw) % 4)).decode()
    except ValueError:
        return raw
    return decoded.rsplit("/", 1)[-1] if decoded.startswith("gid://") else raw
