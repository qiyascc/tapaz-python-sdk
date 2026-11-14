# Advanced use

## Any GraphQL operation

`tap.graphql` sends any GraphQL document with the same session, headers and error handling as the built in calls:

```python
data = tap.graphql(
    "query CurrentUser { currentUser { id name email } }",
    operation="CurrentUser",
    safe=True,
)
print(data["currentUser"])
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `query` | | The GraphQL document |
| `variables` | `None` | A mapping of variables |
| `operation` | `None` | Sent as `operationName` |
| `safe` | `False` | `True` for queries that can be repeated; they are then retried like reads |
| `auth` | `True` | Send the session cookie. With `True` and no session, `SessionRequiredError` |

It returns the `data` of the answer as a dict. GraphQL errors raise `GraphQLError`, authorisation errors `AuthenticationError`.

## Global ids and numeric ids

tap.az's GraphQL API uses global ids, base64 strings such as `Z2lkOi8vdGFwL0FkLzUwMDE`, while the website and this SDK use the short numeric ids. Two helpers convert between them:

```python
from tapaz_sdk import gid, legacy_id

gid("Ad", 5001)
legacy_id("Z2lkOi8vdGFwL0FkLzUwMDE")
```

`gid(kind, value)` turns a numeric id into a global id of that kind (`Ad`, `Category`, `Region`, `User`, ...). A value that is not all digits is returned unchanged, so it is safe to call on an id that is already global. `legacy_id(value)` goes the other way and returns numeric ids unchanged.

These are only needed with `tap.graphql`; the rest of the SDK takes and returns numeric ids.

## The client object

`repr(tap)` shows whether a session is set, never the cookie: `TapAz(signed_in=True)`.

`tap.settings` is the loaded {py:class}`~tapaz_sdk.Settings`. Create a new client to change settings; the HTTP client is built when the client is created.

`CLOUDFLARE_COOKIES` is the set of cookie names the SDK always drops. Names that start with `cf_chl` are dropped too.

## Your own httpx client

```python
import logging

import httpx

from tapaz_sdk import TapAz

log = logging.getLogger("tapaz")


def show(response: httpx.Response) -> None:
    log.info("%s %s -> %s", response.request.method, response.request.url.host, response.status_code)


tap = TapAz(saved_cookie, http_client=httpx.Client(timeout=30, event_hooks={"response": [show]}))
```

Every call to tap.az is a POST to one GraphQL address, so log the operation name from the body if you need to tell calls apart. Never log headers: they hold the session cookie.

## Several accounts and threads

One client holds one session. For several accounts create one client each. A sync client can be shared between threads for reads; do not sign in on it while other threads use it.

## Pointing at a test server

`site_url`, `graphql_url`, `photos_url` and `auth_url` can all point at a local mock:

```python
tap = TapAz(
    graphql_url="http://localhost:8080/graphql",
    photos_url="http://localhost:8080",
    auth_url="http://localhost:8080",
    site_url="http://localhost:8080",
    return_to="http://localhost:8080/",
)
```

Plain http is allowed for `localhost`.
