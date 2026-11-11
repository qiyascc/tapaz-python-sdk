from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Generator, Mapping, Optional, TypeVar
from urllib.parse import urlsplit

import httpx

from .config import Settings, load_settings
from .errors import (
    APIError,
    AuthenticationError,
    BadRequestError,
    BlockedError,
    GraphQLError,
    InvalidCodeError,
    NotFoundError,
    NotSentError,
    OutcomeUnknownError,
    RateLimitError,
    ServerError,
    SessionRequiredError,
    TransportError,
    for_status,
)
from .messages import text
from .session import cookie_header, parse_cookie, set_cookies

T = TypeVar("T")

NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.UnsupportedProtocol)
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
SITE_ERRORS = frozenset({"code_requests", "failed_attempts", "phone", "code"})
AUTH_CODES = frozenset({"unauthorized", "unauthenticated", "forbidden", "unauthorized_error", "authentication_error"})
AUTH_HINTS = ("unauthorized", "not authorized", "unauthenticated", "sign in", "log in", "login required",
              "daxil olun", "giriş")

GRAPHQL = "graphql"
PHOTOS = "photos"
LOGIN = "login"


@dataclass
class Op:
    kind: str
    parse: Callable[[Any], Any] = lambda body: body
    query: str = ""
    operation: str = ""
    variables: Optional[dict[str, Any]] = None
    endpoint: str = ""
    params: Optional[dict[str, Any]] = None
    json: Optional[dict[str, Any]] = None
    files: Optional[list[Any]] = None
    safe: bool = False
    auth: bool = False
    capture: bool = False
    missing: Optional[str] = None
    unknown: str = "error.unknown_outcome"
    attempts: int = field(default=0, compare=False)


@dataclass(frozen=True)
class Pause:
    seconds: float


Step = Any
Flow = Generator[Step, Any, T]


class Outcome:
    def __init__(self, value: Any = None, error: Optional[Exception] = None, wait: Optional[float] = None) -> None:
        self.value = value
        self.error = error
        self.wait = wait


def cloudflare_blocked(response: httpx.Response) -> bool:
    if response.headers.get("cf-mitigated", "").lower() == "challenge":
        return True
    if response.status_code in (403, 503) and "cloudflare" in response.headers.get("server", "").lower():
        return "text/html" in response.headers.get("content-type", "")
    return False


def _number(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _detail(errors: list[Any]) -> str:
    parts = []
    for error in errors:
        if isinstance(error, Mapping):
            where = ".".join(str(x) for x in error.get("path") or [])
            parts.append(f"{where}: {error.get('message')}" if where else str(error.get("message")))
    return "; ".join(parts) or "unknown error"


def _is_auth(errors: list[Any]) -> bool:
    words = " ".join(str(e.get("message", "")) for e in errors if isinstance(e, Mapping)).lower()
    codes = {str((e.get("extensions") or {}).get("code", "")).lower() for e in errors if isinstance(e, Mapping)}
    return bool(codes & AUTH_CODES) or any(hint in words for hint in AUTH_HINTS)


def _paren(message: str) -> str:
    return f"({message})" if message else ""


class Engine:
    def __init__(
        self,
        cookie: Optional[str] = None,
        *,
        settings: Optional[Settings] = None,
        config_file: Optional[str] = None,
        **overrides: Any,
    ) -> None:
        if settings is None:
            settings = load_settings(config_file, **overrides)
        elif overrides:
            current = settings.model_dump()
            current["cookie"] = settings.cookie.get_secret_value()
            settings = load_settings(None, **{**current, **{k: v for k, v in overrides.items() if v is not None}})
        self.settings = settings
        settings.check_transport()
        self._jar: dict[str, str] = parse_cookie(cookie if cookie is not None else settings.cookie.get_secret_value())

    def __repr__(self) -> str:
        return f"{type(self).__name__}(signed_in={self.signed_in})"

    @property
    def cookie(self) -> str:
        return cookie_header(self._jar)

    @property
    def signed_in(self) -> bool:
        return bool(self._jar)

    def use_cookie(self, cookie: Optional[str]) -> None:
        self._jar = parse_cookie(cookie)

    def forget_session(self) -> None:
        self._jar = {}

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(self.settings.timeout, connect=self.settings.connect_timeout)

    def _url(self, op: Op) -> str:
        s = self.settings
        if op.kind == GRAPHQL:
            return s.graphql_url
        base = s.photos_url if op.kind == PHOTOS else s.auth_url
        return base + getattr(s.endpoints, op.endpoint)

    def _host(self, op: Op) -> str:
        return urlsplit(self._url(op)).hostname or self._url(op)

    def _request_args(self, op: Op) -> dict[str, Any]:
        s = self.settings
        headers = {"Accept": "application/json", "User-Agent": s.resolved_user_agent()}
        args: dict[str, Any] = {"headers": headers}
        if op.kind == LOGIN:
            headers["Accept-Language"] = s.language
            args["json"] = op.json or {}
            return args
        headers["Origin"] = s.site_url
        headers["Referer"] = s.site_url + ("/elanlar/new" if op.kind == PHOTOS else "/")
        if op.auth:
            if not self._jar:
                raise SessionRequiredError(text("error.no_session"))
            headers["Cookie"] = self.cookie
        if op.kind == PHOTOS:
            args["params"] = op.params or {}
            if op.files is not None:
                args["files"] = op.files
            return args
        body: dict[str, Any] = {"query": op.query, "variables": op.variables or {}}
        if op.operation:
            body["operationName"] = op.operation
        args["json"] = body
        return args

    def _backoff(self, attempt: int) -> float:
        base = self.settings.backoff_base
        return min(self.settings.backoff_cap, base * (2**attempt)) + random.uniform(0, base / 2)

    def _forget_client_cookies(self) -> None:
        jar = getattr(self, "_http", None)
        if jar is not None:
            jar.cookies.clear()

    def _capture(self, op: Op, response: httpx.Response) -> None:
        if op.kind == LOGIN:
            return
        found = set_cookies(response.headers.get_list("set-cookie"))
        for name, value in found.items():
            if op.capture or name in self._jar:
                if value:
                    self._jar[name] = value
                else:
                    self._jar.pop(name, None)

    def _on_exception(self, op: Op, exc: Exception, attempt: int) -> Outcome:
        host = self._host(op)
        can_retry = attempt < self.settings.max_retries
        if isinstance(exc, NOT_SENT):
            if can_retry:
                return Outcome(wait=self._backoff(attempt))
            return Outcome(error=NotSentError(text("error.connect", host=host, error=exc), path=host))
        if op.safe:
            if can_retry:
                return Outcome(wait=self._backoff(attempt))
            return Outcome(error=TransportError(text("error.timeout", host=host, error=exc), path=host))
        return Outcome(error=OutcomeUnknownError(text(op.unknown, reason=type(exc).__name__), path=host))

    def _on_login(self, op: Op, response: httpx.Response, attempt: int) -> Outcome:
        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = None
        data = body if isinstance(body, Mapping) else None
        if status < 400 and data is not None:
            return Outcome(value=op.parse(data))
        kind = str(data.get("error") or "") if data is not None else ""
        if kind in SITE_ERRORS and data is not None:
            message = _paren(str(data.get("message") or ""))
            args: dict[str, Any] = {"status_code": status, "body": data, "path": self._host(op)}
            sending = op.endpoint == "send_code"
            if kind in ("code_requests", "failed_attempts"):
                key = "error.code_requests" if sending or kind == "code_requests" else "error.code_attempts"
                return Outcome(error=RateLimitError(text(key, message=message).strip(), **args))
            if kind == "phone":
                return Outcome(error=BadRequestError(text("error.phone_refused", message=message).strip(), **args))
            key = "error.code_reused" if attempt > 0 else "error.code_refused"
            return Outcome(error=InvalidCodeError(text(key, message=message).strip(), **args))
        if attempt < self.settings.login_retries:
            return Outcome(wait=self._backoff(attempt))
        return Outcome(error=ServerError(text("error.login_service", attempts=attempt + 1, last=f"HTTP {status}"),
                                         status_code=status, body=data, path=self._host(op)))

    def _on_response(self, op: Op, response: httpx.Response, attempt: int) -> Outcome:
        host = self._host(op)
        status = response.status_code
        if cloudflare_blocked(response):
            return Outcome(error=BlockedError(text("error.blocked", host=host), status_code=status, path=host))
        self._capture(op, response)
        if op.kind == LOGIN:
            return self._on_login(op, response, attempt)
        can_retry = attempt < self.settings.max_retries
        if status == 429 and can_retry:
            hint = _number(response.headers.get("retry-after"))
            return Outcome(wait=min(self.settings.backoff_cap, hint) if hint is not None else self._backoff(attempt))
        if status in (401, 419):
            return Outcome(error=AuthenticationError(text("error.session"), status_code=status, path=host))
        if status in RETRY_STATUSES and status != 429:
            if op.safe and can_retry:
                return Outcome(wait=self._backoff(attempt))
            if not op.safe:
                return Outcome(error=OutcomeUnknownError(text(op.unknown, reason=f"HTTP {status}"),
                                                         status_code=status, path=host))
        if status == 413:
            return Outcome(error=BadRequestError(text("error.photo_size"), status_code=status, path=host))
        try:
            body = response.json()
        except ValueError:
            snippet = response.text[:200]
            if status < 400 and not op.safe:
                return Outcome(error=OutcomeUnknownError(text("error.body", host=host, body=snippet),
                                                         status_code=status, path=host))
            return Outcome(error=for_status(status)(text("error.body", host=host, body=snippet), status_code=status,
                                                    body=snippet, path=host))
        if status >= 400:
            message = body.get("message") or body.get("error") if isinstance(body, Mapping) else None
            kind = for_status(status)
            return Outcome(error=kind(str(message or text("error.status", host=host, status=status)),
                                      status_code=status, body=body, path=host))
        if not isinstance(body, Mapping):
            return Outcome(error=APIError(text("error.refused"), status_code=status, body=body, path=host))
        if op.kind == GRAPHQL:
            errors = [e for e in body.get("errors") or [] if isinstance(e, Mapping)]
            if errors:
                if _is_auth(errors):
                    return Outcome(error=AuthenticationError(text("error.session"), status_code=status, body=body,
                                                             path=host))
                if op.missing:
                    return Outcome(error=NotFoundError(op.missing, status_code=status, body=body, path=host))
                return Outcome(error=GraphQLError(text("error.graphql", details=_detail(errors)), errors=errors,
                                                  status_code=status, body=body, path=host))
            data = body.get("data")
            return Outcome(value=op.parse(data if isinstance(data, Mapping) else {}))
        return Outcome(value=op.parse(body))


class SyncEngine(Engine):
    def __init__(self, *args: Any, http_client: Optional[httpx.Client] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(timeout=self._timeout())

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)

    def _run(self, op: Op) -> Any:
        url = self._url(op)
        attempt = 0
        while True:
            args = self._request_args(op)
            op.attempts = attempt + 1
            try:
                response = self._http.request("POST", url, **args)
            except httpx.HTTPError as exc:
                outcome = self._on_exception(op, exc, attempt)
            else:
                self._forget_client_cookies()
                outcome = self._on_response(op, response, attempt)
            if outcome.wait is not None:
                self._sleep(outcome.wait)
                attempt += 1
                continue
            if outcome.error is not None:
                raise outcome.error
            return outcome.value

    def _flow(self, flow: Flow[T]) -> T:
        reply: Any = None
        while True:
            try:
                step = flow.send(reply)
            except StopIteration as done:
                result: T = done.value
                return result
            if isinstance(step, Pause):
                self._sleep(step.seconds)
                reply = None
            else:
                reply = self._run(step)


class AsyncEngine(Engine):
    def __init__(self, *args: Any, http_client: Optional[httpx.AsyncClient] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=self._timeout())

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self: T) -> T:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            await asyncio.sleep(seconds)

    async def _run(self, op: Op) -> Any:
        url = self._url(op)
        attempt = 0
        while True:
            args = self._request_args(op)
            op.attempts = attempt + 1
            try:
                response = await self._http.request("POST", url, **args)
            except httpx.HTTPError as exc:
                outcome = self._on_exception(op, exc, attempt)
            else:
                self._forget_client_cookies()
                outcome = self._on_response(op, response, attempt)
            if outcome.wait is not None:
                await self._sleep(outcome.wait)
                attempt += 1
                continue
            if outcome.error is not None:
                raise outcome.error
            return outcome.value

    async def _flow(self, flow: Flow[T]) -> T:
        reply: Any = None
        while True:
            try:
                step = flow.send(reply)
            except StopIteration as done:
                result: T = done.value
                return result
            if isinstance(step, Pause):
                await self._sleep(step.seconds)
                reply = None
            else:
                reply = await self._run(step)
