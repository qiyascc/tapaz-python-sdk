# Configuration

`TapAz()` works with no configuration at all. When you want to change something, there are three places to do it. Settings are loaded with [goodconf](https://github.com/lincolnloop/goodconf) on top of pydantic.

## Where settings come from

From the highest priority to the lowest:

1. **Arguments in code**, such as `TapAz(timeout=10)`.
2. **Environment variables** starting with `TAPAZ_`, such as `TAPAZ_TIMEOUT=10`.
3. **A config file**, such as `tapaz.toml`.
4. **The defaults** in the table below.

## In code

```python
from tapaz_sdk import TapAz

tap = TapAz(saved_cookie, timeout=10, default_region="420", user_agent="my-shop/1.0 tapaz-python-sdk/{version}")
```

The first positional argument is the session cookie. Any setting can follow as a keyword.

To share settings between clients, build them once:

```python
from tapaz_sdk import TapAz, load_settings

settings = load_settings("/etc/my-shop/tapaz.toml")
tap = TapAz(settings=settings)
slow = TapAz(settings=settings, timeout=60)
```

`load_settings(config_file=None, **overrides)` reads the environment and the file and applies the overrides. `None` overrides are ignored.

## Environment variables

The setting name in capitals with a `TAPAZ_` prefix:

```bash
export TAPAZ_COOKIE="_tapaz_session=abc123"
export TAPAZ_TIMEOUT=20
export TAPAZ_DEFAULT_REGION=420
```

Windows CMD:

```bat
set TAPAZ_COOKIE=_tapaz_session=abc123
set TAPAZ_TIMEOUT=20
```

Nested settings use a double underscore: `TAPAZ_ENDPOINTS__PHOTO_UPLOAD=/pond`.

## Config file

With no `config_file` argument the client looks in the working directory for `tapaz.toml`, `tapaz.yaml`, `tapaz.yml` or `tapaz.json`, in that order. Point it elsewhere with `TAPAZ_CONFIG=/path/to/file` or `config_file=`.

::::{tab-set}

:::{tab-item} TOML
```toml
timeout = 30
max_retries = 2
login_retries = 2
default_region = "420"
delete_reason = "6"

[endpoints]
photo_upload = "/pond"
```
:::

:::{tab-item} YAML
```yaml
timeout: 30
max_retries: 2
login_retries: 2
default_region: "420"
delete_reason: "6"
endpoints:
  photo_upload: /pond
```
:::

:::{tab-item} JSON
```json
{
  "timeout": 30,
  "max_retries": 2,
  "login_retries": 2,
  "default_region": "420",
  "delete_reason": "6",
  "endpoints": {"photo_upload": "/pond"}
}
```
:::

::::

YAML needs the `yaml` extra, TOML on Python 3.10 the `toml` extra. The repository has an example: [examples/tapaz.toml](https://github.com/qiyascc/tapaz-python-sdk/blob/main/examples/tapaz.toml).

## All settings

| Setting | Environment variable | Default | What it does |
| --- | --- | --- | --- |
| `cookie` | `TAPAZ_COOKIE` | empty | Session cookie of a signed in account, as a `Cookie` header |
| `site_url` | `TAPAZ_SITE_URL` | `https://tap.az` | Address of tap.az, used for links, `Origin` and `Referer` |
| `graphql_url` | `TAPAZ_GRAPHQL_URL` | `https://tap.az/graphql` | Address of the GraphQL API |
| `photos_url` | `TAPAZ_PHOTOS_URL` | `https://photos.tap.az` | Address of the photo service |
| `auth_url` | `TAPAZ_AUTH_URL` | `https://api.digit-u.id` | Address of the login service that sends and checks SMS codes |
| `return_to` | `TAPAZ_RETURN_TO` | `https://tap.az/` | Address the login service signs the user into |
| `endpoints` | `TAPAZ_ENDPOINTS__<NAME>` | see below | Path of every call that is not GraphQL |
| `language` | `TAPAZ_LANGUAGE` | `az` | Language of messages from the login and photo services |
| `source` | `TAPAZ_SOURCE` | `DESKTOP` | Source sent with ad mutations |
| `default_region` | `TAPAZ_DEFAULT_REGION` | `420` | Region of new ads when none is given. 420 is Baku |
| `delete_reason` | `TAPAZ_DELETE_REASON` | `6` | Delete reason preferred when an ad is deleted without one |
| `timeout` | `TAPAZ_TIMEOUT` | `30` | Seconds to wait for an answer |
| `connect_timeout` | `TAPAZ_CONNECT_TIMEOUT` | `10` | Seconds to wait for a connection |
| `max_retries` | `TAPAZ_MAX_RETRIES` | `2` | Extra attempts for calls that are safe to repeat, 0 to 10 |
| `login_retries` | `TAPAZ_LOGIN_RETRIES` | `2` | Extra attempts when the login service answers without a known error, 0 to 10 |
| `backoff_base` | `TAPAZ_BACKOFF_BASE` | `0.6` | First wait between retries, in seconds |
| `backoff_cap` | `TAPAZ_BACKOFF_CAP` | `8` | Longest wait between retries, in seconds |
| `user_agent` | `TAPAZ_USER_AGENT` | `tapaz-python-sdk/{version}` | User-Agent header. `{version}` becomes the SDK version |
| `allow_insecure_http` | `TAPAZ_ALLOW_INSECURE_HTTP` | `false` | Allow plain http addresses outside localhost, for a private test server only |

Values are checked when the settings load: a negative timeout or an address without `http://` or `https://` fails at once.

## Endpoints

| Name | Default | Service |
| --- | --- | --- |
| `photo_upload` | `/pond` | `photos_url` |
| `photo_rotate` | `/pond/rotate` | `photos_url` |
| `send_code` | `/auth` | `auth_url` |
| `verify_code` | `/auth/verify` | `auth_url` |

GraphQL calls all go to `graphql_url`.

## The User-Agent

The SDK identifies itself as `tapaz-python-sdk/<version>` and does not pretend to be a browser. Put your product's name in front if you run one on top of it:

```python
tap = TapAz(user_agent="my-shop/1.0 (+https://example.az) tapaz-python-sdk/{version}")
```

## Plain http

Every address must be https because the session cookie travels with the requests. `localhost`, `127.0.0.1` and `::1` may use plain http for local test servers. Other plain http addresses raise `ConfigurationError` when the client is created, unless `allow_insecure_http=True`.

## Your own httpx client

For proxies, custom certificates or logging, pass an `httpx.Client` (or `httpx.AsyncClient` for `AsyncTapAz`) as `http_client=`:

```python
import httpx

from tapaz_sdk import TapAz

tap = TapAz(saved_cookie, http_client=httpx.Client(proxy="http://proxy.internal:3128", timeout=30))
```

`proxy=` needs httpx 0.26 or newer; older versions call it `proxies=`. A client you pass in is not closed by `tap.close()`. The SDK clears the httpx cookie jar after every answer and keeps the session in its own store.
