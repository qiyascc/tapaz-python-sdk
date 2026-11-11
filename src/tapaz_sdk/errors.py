from __future__ import annotations

from typing import Any, Optional, Sequence


class TapAzError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(TapAzError):
    pass


class SessionRequiredError(TapAzError):
    pass


class InvalidRequestError(TapAzError, ValueError):
    def __init__(self, message: str, *, errors: Sequence[Any] = ()) -> None:
        super().__init__(message)
        self.errors = tuple(errors)


class TransportError(TapAzError):
    def __init__(self, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.path = path


class NotSentError(TransportError):
    pass


class OutcomeUnknownError(TransportError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.status_code = status_code


class BlockedError(TransportError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.status_code = status_code


class APIError(TapAzError):
    def __init__(self, message: str, *, status_code: int, body: Any = None, path: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.path = path

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.message}"


class BadRequestError(APIError):
    pass


class AuthenticationError(APIError):
    pass


class NotFoundError(APIError):
    pass


class RateLimitError(APIError):
    def __init__(self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    pass


class GraphQLError(BadRequestError):
    def __init__(self, message: str, *, errors: Sequence[Any] = (), **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.errors = tuple(errors)


class MutationError(GraphQLError):
    @property
    def codes(self) -> frozenset[str]:
        found = set()
        for error in self.errors:
            if isinstance(error, dict):
                code = error.get("code") or (error.get("extensions") or {}).get("code")
                if code:
                    found.add(str(code).upper())
        return frozenset(found)


class BannedError(MutationError):
    pass


class UnconfirmedError(MutationError):
    pass


class InvalidCodeError(BadRequestError):
    pass


def for_status(status: int) -> type[APIError]:
    if status in (401, 403, 419):
        return AuthenticationError
    if status == 404:
        return NotFoundError
    if status == 429:
        return RateLimitError
    if status >= 500:
        return ServerError
    if status >= 400:
        return BadRequestError
    return APIError
