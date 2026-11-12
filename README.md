# tapaz-python-sdk

[![PyPI](https://img.shields.io/pypi/v/tapaz-python-sdk?color=3775A9&logo=pypi&logoColor=white)](https://pypi.org/project/tapaz-python-sdk/)
[![Python](https://img.shields.io/badge/python-3.10%20to%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![tap.az](https://img.shields.io/badge/site-tap.az%20GraphQL-FF6A00)](https://tap.az)
[![Typed](https://img.shields.io/badge/typing-mypy-2A6DB2)](https://mypy-lang.org)
[![Async](https://img.shields.io/badge/sync%20%2B%20async-httpx-5A45FF)](https://www.python-httpx.org)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/qiyascc/tapaz-python-sdk/blob/main/LICENSE)

Typed Python client for tap.az. SMS code login, the category catalog with every property, ads, photos and the account's own ad list. Sync and async, with retry rules built so an ad is never posted twice.

Unofficial. It talks to the same GraphQL API, photo service and login service as the tap.az website, as one signed in account.

```bash
pip install tapaz-python-sdk
```

## Sign in with an SMS code

```python
from tapaz_sdk import TapAz

with TapAz() as tap:
    tap.auth.send_code("050 123 45 67")
    login = tap.auth.verify("050 123 45 67", "1234")
    login.user.name
    saved = login.cookie
```

tap.az signs in by phone only. `send_code` asks the login service for a 4 digit SMS code, `verify` turns the code into a tap.az session. Keep `login.cookie` and pass it next time, so the user does not need a new SMS:

```python
tap = TapAz(saved)
tap.me().phone
```

The session is a plain `Cookie` header (`tap.cookie`, `tap.use_cookie(...)`). Cloudflare cookies such as `cf_clearance` and `__cf_bm` are dropped on the way in and on the way out, and the client never keeps them between calls.

## Post an apartment

```python
category = tap.catalog.category(635)
for prop in category.properties:
    print(prop.id, prop.name, prop.kind.value, prop.required, [(o.id, o.name) for o in prop.options])

photo = tap.photos.upload("flat-1.jpg")
ad = tap.ads.create(
    635,
    "3 room flat in Yasamal, renovated, close to the metro.",
    properties={"740": "3722", "737": 85, "812": "Elmler Akademiyasi metro", "900": True},
    price=150000,
    photo_ids=[photo.id],
)
ad.id, ad.status, ad.url
```

`properties` maps property ids to values: an option id for a collection, a number for a range, `True` or `False` for a boolean, text for a string. Before anything is sent the client loads the category and checks every value the way the tap.az form does: required properties, option ids, ranges, properties that only apply after another option is chosen (`depends_on`, `catalog.property_options(...)`), and the category rules for price, photos and title. Every problem is listed in `InvalidRequestError.errors`. `tap.ads.validate(...)` runs the same check and returns the property set without posting.

The contact phone and email come from the account unless you pass `phones`, `email` and `name`. `contact_type="ONLY_MESSAGES"` hides the phone number. New ads go to `region_id` 420 (Baku) unless you pass another region from `tap.catalog.regions()`.

tap.az covers every kind of ad, so the same calls work for any leaf category: find it in `tap.catalog.categories()` (`walk()` goes through the tree).

## Manage ads

```python
from tapaz_sdk import AdTab

page = tap.ads.list(AdTab.PUBLISHED, first=20)
everything = tap.ads.all(AdTab.REJECTED)
tap.ads.get(5001).reject_reason
tap.ads.update(5001, 635, "New text", properties={"740": "3722", "737": 85, "812": "Yasamal"}, price=140000)
tap.ads.prolong(5001)
tap.ads.delete(5001)
```

`list` pages with a cursor (`page.next_cursor`), `all` follows it. `delete` reads the delete reasons tap.az offers for the ad and picks reason 6 (the `delete_reason` setting), or the first one that needs no description, unless you pass `reason_id` from `tap.ads.delete_reasons(...)`. An update sends the text, price, photos, contact type and the boolean properties; the other properties are checked but only set when the ad is created.

## Photos

```python
photo = tap.photos.upload("flat.jpg")
photo = tap.photos.upload(open("flat.png", "rb"))
photo = tap.photos.upload(raw_bytes, "flat.jpg")
turned = tap.photos.rotate(photo.id, 90)
```

Upload before creating the ad and pass the ids in `photo_ids`. A rotation returns a new id.

## Safety

| Situation | What the client does |
| --- | --- |
| Connection refused, nothing sent | Retries, then `NotSentError` |
| Timeout, cut connection, 5xx or a broken answer on `createAd`, `updateAd`, `destroyAd`, `prolongAds` or `loginUser` | No retry, `OutcomeUnknownError`. Look at `ads.list()` before trying again |
| Same failure on a read or a photo upload | Retries with backoff, then `TransportError`. A repeated upload can only leave an unused photo |
| Login service answers without a known error (any status) | Asks again up to `login_retries` times, as the service is known to fail now and then |
| A send that needed a retry | `CodeSent.retried` and a note: more than one SMS may arrive, use the latest code |
| A code refused after a retry | `InvalidCodeError` says the code may already be used |
| Timeout while sending or checking a code | No retry, `OutcomeUnknownError` |
| Too many codes or wrong codes | `RateLimitError` |
| Cloudflare challenge page | `BlockedError`. The client does not solve challenges, use no proxies and sends its own User-Agent |
| Bad property, price, phone or id | `InvalidRequestError` before anything is sent |
| Session cookie | Sent to tap.az and its photo service only, never to the login service |
| Plain http address | `ConfigurationError`, except localhost or `allow_insecure_http` |

## Endpoints

| Namespace | Methods |
| --- | --- |
| `auth` | `send_code` `verify` `me` |
| `catalog` | `categories` `category` `property_options` `regions` `contact_types` |
| `ads` | `create` `validate` `update` `delete` `delete_reasons` `prolong` `get` `list` `all` |
| `photos` | `upload` `rotate` |
| client | `me` `graphql` `cookie` `use_cookie` `forget_session` `signed_in` |

`AsyncTapAz` has the same methods, awaited. `tap.graphql(query, variables, operation=..., safe=True)` sends any other operation with the same session and error handling.

## Errors

`TapAzError` is the base. HTTP answers raise `APIError` subclasses: `BadRequestError` (400), `AuthenticationError` (401, 403, 419 and GraphQL authorization errors), `NotFoundError`, `RateLimitError` (429), `ServerError` (5xx). GraphQL errors raise `GraphQLError` with `.errors`. Refused mutations raise `MutationError` with `.errors` and `.codes`, or `BannedError` and `UnconfirmedError` for a banned account or an unconfirmed phone or email. A wrong SMS code raises `InvalidCodeError`. Calls that need a session raise `SessionRequiredError` when there is none.

## Config

Pass values in code, or set `TAPAZ_COOKIE`, `TAPAZ_TIMEOUT`, `TAPAZ_MAX_RETRIES`, `TAPAZ_LOGIN_RETRIES`, `TAPAZ_DEFAULT_REGION`, `TAPAZ_USER_AGENT`, or put them in `tapaz.toml` ([example](https://github.com/qiyascc/tapaz-python-sdk/blob/main/examples/tapaz.toml)). Every address is a setting (`TAPAZ_GRAPHQL_URL`, `TAPAZ_PHOTOS_URL`, `TAPAZ_AUTH_URL`) and so is every path (`TAPAZ_ENDPOINTS__PHOTO_UPLOAD=...`). Messages live in `messages.yaml` and can be replaced with `messages.use(...)`. More in [examples](https://github.com/qiyascc/tapaz-python-sdk/tree/main/examples).

## Develop

```bash
pip install -e ".[dev]" && pytest && ruff check . && mypy src
```

## Links

- Source code: [github.com/qiyascc/tapaz-python-sdk](https://github.com/qiyascc/tapaz-python-sdk)
- PyPI: [pypi.org/project/tapaz-python-sdk](https://pypi.org/project/tapaz-python-sdk/)
- Project page: [theqiyas.cc/projects/tapaz-sdk](https://theqiyas.cc/projects/tapaz-sdk/)
- Author: [Qiyas Sadıqov](https://theqiyas.cc), more projects at [theqiyas.cc](https://theqiyas.cc)

## License

MIT
