# Safety and retries

When a request fails halfway, a read can simply be repeated. A write cannot: an ad that tap.az created but never confirmed must not be posted again. The SDK treats each kind of call differently.

## The kinds of calls

| Kind | Calls | On a timeout, a dropped connection or a 5xx |
| --- | --- | --- |
| Reads | every `catalog` call, `auth.me`, `ads.get`, `ads.list`, `ads.all`, `ads.delete_reasons`, and the reads inside `create`, `update`, `validate` and `delete` | Retried with backoff, then `TransportError` or `ServerError` |
| Photos | `photos.upload`, `photos.rotate` | Retried with backoff. A repeated upload can only leave an unused photo |
| Ad changes | `ads.create`, `ads.update`, `ads.delete`, `ads.prolong`, the `loginUser` step of `auth.verify`, `graphql(...)` | Never retried. `OutcomeUnknownError` |
| SMS login | `auth.send_code`, the code check in `auth.verify` | Answers without a known error are asked again up to `login_retries`; a timeout is not retried |

## Every situation

| Situation | What the client does |
| --- | --- |
| Connection refused, nothing sent | Retries, then `NotSentError` |
| Timeout, cut connection, 5xx or a broken answer on `createAd`, `updateAd`, `destroyAd`, `prolongAds` or `loginUser` | No retry, `OutcomeUnknownError`. Look at `ads.list()` before trying again |
| Same failure on a read or a photo upload | Retries with backoff, then `TransportError` |
| 429 on a tap.az call | Waits for `Retry-After` (at most `backoff_cap`) and tries again, then `RateLimitError` |
| Login service answers without a known error (any status) | Asks again up to `login_retries` times, as the service is known to fail now and then |
| A send that needed a retry | `CodeSent.retried` and a `note`: more than one SMS may arrive, use the latest code |
| A code refused after a retry | `InvalidCodeError` says the code may already be used |
| Timeout while sending or checking a code | No retry, `OutcomeUnknownError` |
| Too many codes or wrong codes | `RateLimitError` |
| Cloudflare challenge page | `BlockedError`. The client does not solve challenges, uses no proxies and sends its own User-Agent |
| Bad property, price, phone or id | `InvalidRequestError` before anything is sent |
| A call that needs a session, with none | `SessionRequiredError` before anything is sent |
| Session cookie | Sent to tap.az and its photo service only, never to the login service |
| Plain http address | `ConfigurationError`, except localhost or `allow_insecure_http` |

## Backoff

The wait before retry number `n` (counting from 0) is

```text
min(backoff_cap, backoff_base * 2 ** n) + a random part of up to backoff_base / 2
```

With the defaults (`max_retries=2`, `backoff_base=0.6`, `backoff_cap=8`) a read is tried three times, with waits of about 0.6 and 1.2 seconds. `max_retries=0` turns retries off, which is handy in tests.

## When the outcome is unknown

`OutcomeUnknownError` means the request went out and no usable answer came back. tap.az may have done the change.

| Call | How to check |
| --- | --- |
| `ads.create` | `ads.list("PENDING")` and look for the new ad |
| `ads.update` | `ads.get(ad_id)` and compare the text and price |
| `ads.delete` | `ads.get(ad_id)` raises `NotFoundError` when the delete went through |
| `ads.prolong` | `ads.get(ad_id)` and look at `expires_at` |
| `auth.verify` | `tap.me()`; if it works, the sign in went through |
| `auth.send_code` | Wait for the SMS; ask for a new code only if none arrives |

```python
from tapaz_sdk import OutcomeUnknownError

try:
    ad = tap.ads.create(635, body, properties=values, price=150000, photo_ids=ids)
except OutcomeUnknownError:
    pending = tap.ads.list("PENDING", first=20).items
    print("Check these before posting again:", [(a.id, a.title) for a in pending])
    raise
```

## Cloudflare

tap.az is behind Cloudflare. When Cloudflare answers with a challenge page (a `cf-mitigated: challenge` header, or a Cloudflare 403 or 503 HTML page), the SDK raises `BlockedError` at once. It does not retry, does not try to pass the challenge and never keeps Cloudflare cookies. Frequent `BlockedError` points at the network the code runs from.

## Sessions

- The session cookie goes to tap.az and the photo service, never to the login service.
- Cookies from tap.az answers only update cookies the session already has. New cookies are only taken during the sign in.
- Cloudflare cookies are dropped everywhere.
