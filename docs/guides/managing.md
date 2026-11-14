# Managing ads

Everything about the account's own ads lives under `tap.ads` and needs a session.

## Read one ad

```python
ad = tap.ads.get(5001)
print(ad.title, ad.status, ad.price, ad.url)
if ad.status == "REJECTED":
    print(ad.reject_reason)
```

`get` takes the ad id as a number or text and returns an {py:class}`~tapaz_sdk.Ad`. An ad that does not exist raises `NotFoundError`.

| `Ad` field | Meaning |
| --- | --- |
| `id` | The numeric id as text, such as `"5001"` |
| `global_id` | The GraphQL id |
| `title` | The title |
| `status` | An `AdStatus`, see below |
| `status_message` | The status text tap.az shows, when there is one |
| `reject_reason` | Why moderation rejected the ad |
| `path`, `url` | Path and full address on tap.az |
| `price` | The price as a `float`, or `None` |
| `expires_at` | When the ad expires |
| `updated_at` | When it was last changed |
| `thumbnail` | Address of the main photo |
| `is_author` | Whether the signed in account wrote the ad |
| `raw` | The whole answer |

### Statuses

| `AdStatus` | Meaning |
| --- | --- |
| `PENDING` | Waiting for moderation |
| `APPROVED`, `PUBLISHED` | Live. `status.is_live` is `True` for both |
| `REJECTED` | Rejected by moderation, see `reject_reason` |
| `EXPIRED` | Its time ran out; it can be prolonged |
| `ARCHIVED` | Archived |
| `AWAITING_PAYMENT` | Over the free limit, shown after payment on tap.az |
| `UNKNOWN` | A status this version does not know |

`AdStatus` is a string enum, so `ad.status == "REJECTED"` works.

## List the account's ads

```python
from tapaz_sdk import AdTab

page = tap.ads.list(AdTab.PUBLISHED, first=50)
for ad in page.items:
    print(ad.id, ad.title, ad.expires_at)
print(page.total, page.has_more)
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `status` | `None` | An `AdTab` or its name in any case. `None` lists every ad |
| `first` | `20` | Page size, 1 to 100 |
| `after` | `None` | Cursor of the previous page |

The tabs are `PENDING`, `PUBLISHED`, `REJECTED`, `EXPIRED`, `ARCHIVED` and `AWAITING_PAYMENT`. Another name raises `InvalidRequestError` with the list.

{py:class}`~tapaz_sdk.AdPage` has `items`, `total`, `next_cursor` and `has_more`. Pass `next_cursor` as `after` for the next page:

```python
cursor = None
while True:
    page = tap.ads.list("PUBLISHED", first=100, after=cursor)
    for ad in page.items:
        print(ad.id)
    if not page.has_more:
        break
    cursor = page.next_cursor
```

### Every ad at once

```python
published = tap.ads.all(AdTab.PUBLISHED)
rejected = tap.ads.all("rejected", page_size=100)
```

`all(status=None, page_size=50, max_pages=50)` follows the cursor and returns a tuple of `Ad`. `max_pages` stops a runaway loop; raise it for very large accounts.

## Edit an ad

```python
ad = tap.ads.update(
    5001,
    635,
    "3 room flat in Yasamal. Price reduced.",
    properties={"740": "3722", "737": 85, "812": "Yasamal", "900": True},
    price=140000,
    photo_ids=photo_ids,
)
```

`update(ad_id, category_id, body, *, properties, price, title, photo_ids, contact_type)` runs the same checks as `create` against the category, then sends:

- the text,
- the price,
- the photos,
- the contact type,
- the boolean properties.

The other properties (lists, ranges, text) are checked but not changed: tap.az only sets them when the ad is created. To change one of those, delete the ad and post a new one. An edit usually sends the ad back to moderation.

## Prolong an ad

```python
ok = tap.ads.prolong(5001)
```

Returns `True` when tap.az prolonged the ad. A refusal raises `MutationError` with tap.az's reason.

## Delete an ad

tap.az asks why an ad is deleted. The SDK reads the reasons tap.az offers for that ad and picks one for you:

```python
done = tap.ads.delete(5001)
print(done.deleted, done.reason)
```

The pick, in order:

1. the reason you pass as `reason_id`;
2. otherwise the reason whose id is the `delete_reason` setting (`6` by default);
3. otherwise the first reason that needs no written description.

Reasons that need a description are never picked, because the SDK has nothing to write there.

To choose yourself:

```python
for reason in tap.ads.delete_reasons(5001):
    print(reason.legacy_id, reason.name, reason.description_required)

tap.ads.delete(5001, reason_id=4)
```

{py:class}`~tapaz_sdk.DeleteReason` has `id` (the GraphQL id), `legacy_id` (the short number), `name` and `description_required`. `reason_id` may be either id. A reason that tap.az does not offer for the ad raises `InvalidRequestError`.

`delete` returns a {py:class}`~tapaz_sdk.Deleted` with `ad_id`, `deleted` and the `reason` name that was sent.

## Writes are not repeated

`update`, `prolong` and `delete` are never retried after a timeout, a dropped connection or a 5xx. They raise `OutcomeUnknownError`. Read the ad with `get` (or look for it in `list`) before trying again. See [Safety and retries](safety.md).
