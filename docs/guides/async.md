# Async

`AsyncTapAz` has the same namespaces, methods, arguments and results as `TapAz`. Add `await`.

```python
import asyncio
import os

from tapaz_sdk import AdTab, AsyncTapAz


async def main() -> None:
    async with AsyncTapAz(os.environ["TAPAZ_COOKIE"]) as tap:
        for ad in await tap.ads.all(AdTab.PUBLISHED):
            print(ad.id, ad.title, ad.price, ad.url)
        for ad in await tap.ads.all(AdTab.REJECTED):
            print(ad.id, ad.reject_reason)


asyncio.run(main())
```

This is the script from [examples/list_ads_async.py](https://github.com/qiyascc/tapaz-python-sdk/blob/main/examples/list_ads_async.py) in the repository.

## Creating and closing

Use `async with`, or `await tap.close()` when you are done. The constructor takes the same arguments as `TapAz`; `http_client=` must be an `httpx.AsyncClient`.

`tap.cookie`, `tap.signed_in`, `tap.use_cookie(...)` and `tap.forget_session()` are plain attributes and methods, without `await`.

## Doing things side by side

Uploading photos in parallel is the most common win:

```python
async def upload_all(tap: AsyncTapAz, paths):
    photos = await asyncio.gather(*(tap.photos.upload(p) for p in paths))
    return [photo.id for photo in photos]
```

Reading the details of many ads:

```python
ads = await asyncio.gather(*(tap.ads.get(ad_id) for ad_id in ids))
```

Keep the number of parallel requests modest, with a semaphore if the list is long:

```python
gate = asyncio.Semaphore(4)

async def get(ad_id):
    async with gate:
        return await tap.ads.get(ad_id)

ads = await asyncio.gather(*(get(ad_id) for ad_id in ids))
```

## Sessions

One client holds one session. Do not run `auth.verify` on a client while other calls use it: signing in replaces the session. For several accounts, use one client each.

## Waiting

Backoff waits use `asyncio.sleep`, so retries never block the event loop. The retry rules are the same as in the sync client; see [Safety and retries](safety.md).
