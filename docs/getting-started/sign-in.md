# Signing in

tap.az signs in by phone number only. The website sends a 4 digit code by SMS and turns the code into a session cookie. The SDK does the same in two calls, and gives you the cookie so you can keep it and skip the SMS next time.

The catalog calls (categories, properties, regions, contact types) work without a session. Everything about the account's own ads needs one.

## Send the code, check the code

```python
from tapaz_sdk import TapAz

with TapAz() as tap:
    sent = tap.auth.send_code("050 123 45 67")
    if sent.note:
        print(sent.note)
    login = tap.auth.verify("050 123 45 67", input("SMS code: "))
    print("Signed in as", login.user.name)
    saved = login.cookie
```

`send_code` asks the login service tap.az uses to send the SMS. `verify` checks the code, then calls tap.az's `loginUser` with the token the login service returns, which is when tap.az sets the session cookie. Finally it reads the account with that cookie, so you know straight away that the session works.

### Phone numbers

Both calls accept an Azerbaijani mobile number written the usual ways: `050 123 45 67`, `0501234567`, `+994 50 123 45 67`, `994501234567` or `501234567`. It must have nine digits after the country code and start with an operator code (10, 50, 51, 55, 60, 70, 77 or 99). Anything else raises `InvalidRequestError` before a code is requested.

### What `send_code` returns

{py:class}`~tapaz_sdk.CodeSent`:

| Field | Meaning |
| --- | --- |
| `phone` | The number in the local form, such as `0501234567` |
| `code_requests_left` | How many more codes the login service will send now, when it says |
| `retried` | `True` when the request had to be sent again |
| `note` | A sentence to show the user when `retried` is `True`, otherwise `None` |

### What `verify` returns

{py:class}`~tapaz_sdk.Login` has two fields: `user`, a {py:class}`~tapaz_sdk.User`, and `cookie`, the session as a `Cookie` header string. The cookie is left out of `repr()`, so printing the object does not leak it.

| `User` field | Meaning |
| --- | --- |
| `id` | The numeric account id as text, such as `"77"` |
| `global_id` | The GraphQL id |
| `name`, `email`, `phone` | Account details |
| `phone_confirmed` | Whether tap.az has the phone confirmed, when it says |
| `is_shop`, `shop` | Shop accounts and the shop name |
| `banned` | `True` for a banned account |

### When the login service misbehaves

The login service sometimes answers with an error that has nothing to do with the code. The SDK asks again, up to `login_retries` extra times (2 by default). When that happens for `send_code`, the first request may still have reached the phone, so the user can get two SMS messages: `retried` is `True` and `note` says to use the latest code.

If `verify` had to be repeated and the code is then refused, the error is an `InvalidCodeError` whose message says the code may already have been used by the earlier attempt. Ask for a new one.

A timeout while sending or checking a code is never repeated. You get `OutcomeUnknownError`, because there is no way to know whether the SMS went out or the code was used.

### Wrong codes and limits

| Error | When |
| --- | --- |
| `InvalidCodeError` | The code is wrong or expired |
| `RateLimitError` | Too many codes asked for, or too many wrong codes. Wait before trying again |
| `BadRequestError` | The login service refused the phone number |
| `MutationError` | tap.az refused `loginUser` |

## Keep the session

`login.cookie` and `tap.cookie` are the same string. Save it after signing in and pass it to the client next time:

```python
from pathlib import Path

from tapaz_sdk import TapAz

SESSION = Path("tapaz.session")

tap = TapAz(SESSION.read_text().strip() if SESSION.exists() else None)
if not tap.signed_in:
    phone = input("Phone: ")
    tap.auth.send_code(phone)
    login = tap.auth.verify(phone, input("SMS code: "))
    SESSION.write_text(login.cookie)
print(tap.me().name)
```

The cookie can also come from the environment or a config file:

```bash
export TAPAZ_COOKIE="_tapaz_session=abc123"
```

To change the session of an existing client:

```python
tap.use_cookie(saved)
tap.forget_session()
```

`use_cookie` accepts a `Cookie` header value, with or without the `Cookie:` prefix. `forget_session` empties the client's session; it does not sign out on tap.az.

`tap.signed_in` is `True` when the client holds a session. It does not ask tap.az; use `tap.me()` for that.

:::{warning}
The session cookie gives full access to the account while it is valid. Keep it out of version control and logs. The `cookie` setting is a pydantic `SecretStr`, so it does not show up when settings are printed.
:::

## Cloudflare cookies

tap.az sits behind Cloudflare, which sets cookies such as `cf_clearance` and `__cf_bm`. The SDK drops every Cloudflare cookie, whether it comes from a saved string, a `Set-Cookie` header or `use_cookie`, and never sends one. The session it keeps is only the tap.az session.

## Who am I

```python
user = tap.me()
```

`tap.me()` is the same as `tap.auth.me()`. It raises `SessionRequiredError` when the client has no session at all, and `AuthenticationError` when tap.az no longer accepts it.

## When the session expires

```python
from tapaz_sdk import AuthenticationError

try:
    page = tap.ads.list("PUBLISHED")
except AuthenticationError:
    sign_in_again()
```

Calls that need a session raise `SessionRequiredError` before sending anything when the client has none, and `AuthenticationError` when tap.az refuses the one it has.
