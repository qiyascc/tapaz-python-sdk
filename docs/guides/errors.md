# Errors

Every exception inherits from {py:class}`~tapaz_sdk.TapAzError`.

## The hierarchy

```text
TapAzError
├── ConfigurationError        settings that cannot work
├── SessionRequiredError      the call needs a session and the client has none
├── InvalidRequestError       a bad argument or ad, found before sending (also a ValueError)
├── TransportError            no usable answer came back
│   ├── NotSentError          the connection failed, nothing was sent
│   ├── OutcomeUnknownError   a write may or may not have gone through
│   └── BlockedError          a Cloudflare challenge page
└── APIError                  tap.az or a tap.az service answered with an error
    ├── AuthenticationError   401, 403, 419 or a GraphQL authorisation error
    ├── NotFoundError         404, or an ad that does not exist
    ├── RateLimitError        429 after the retries, or too many SMS codes
    ├── ServerError           5xx after the retries
    └── BadRequestError       400 and other 4xx
        ├── InvalidCodeError  the SMS code was not accepted
        └── GraphQLError      tap.az refused a GraphQL request
            └── MutationError tap.az refused a change
                ├── BannedError       the account is banned
                └── UnconfirmedError  the phone or email is not confirmed
```

## Attributes

Every exception has `message`.

| Exception | Extra attributes |
| --- | --- |
| `InvalidRequestError` | `errors`: a tuple of `{"field", "error"}` dicts, filled when an ad fails the checks |
| `TransportError` and below | `path`: the host that was called |
| `OutcomeUnknownError`, `BlockedError` | `status_code` when there was an answer |
| `APIError` and below | `status_code`, `body`, `path` |
| `RateLimitError` | `retry_after`, which stays `None` in this version: waiting is handled by the retries |
| `GraphQLError` | `errors`: the GraphQL errors |
| `MutationError` | `codes`: a frozenset of the error codes in upper case |

`str()` of an `APIError` starts with the status code in brackets.

## Which one to catch

| You want to | Catch |
| --- | --- |
| Show form errors | `InvalidRequestError` (read `errors`), `MutationError` |
| Ask the user to sign in | `SessionRequiredError`, `AuthenticationError` |
| Ask for a new SMS code | `InvalidCodeError` |
| Try again later | `RateLimitError`, `ServerError`, `NotSentError`, `TransportError` |
| Check the account before retrying | `OutcomeUnknownError` |
| Stop and alert someone | `BlockedError`, `BannedError`, `ConfigurationError` |

```python
from tapaz_sdk import (
    AuthenticationError,
    BannedError,
    BlockedError,
    InvalidRequestError,
    MutationError,
    OutcomeUnknownError,
    SessionRequiredError,
    TapAzError,
    UnconfirmedError,
)

try:
    ad = tap.ads.create(category_id, body, properties=values, price=price, photo_ids=ids)
except InvalidRequestError as exc:
    show_form_errors(exc.errors)
except UnconfirmedError:
    ask_to_confirm_phone()
except BannedError:
    alert_admin("tap.az account is banned")
except MutationError as exc:
    show_form_errors([{"field": ".".join(map(str, e.get("path") or [])), "error": e.get("message")} for e in exc.errors])
except (SessionRequiredError, AuthenticationError):
    sign_in_again()
except OutcomeUnknownError:
    check_pending_ads_first()
except BlockedError:
    alert_admin("tap.az shows a Cloudflare challenge to this server")
except TapAzError as exc:
    retry_later(exc)
```

Order matters: catch the subclasses before `MutationError`, and `MutationError` before `TapAzError`.

## Notes

- `BlockedError` is a `TransportError` here, because the answer did not come from tap.az's API at all.
- A GraphQL error on reading a single ad becomes `NotFoundError` with the message "Ad … was not found".
- `NotFoundError` is also raised by a mutation whose error code is `NOT_FOUND_ERROR`.
- Every message comes from `messages.yaml`; see [Messages](messages.md).
