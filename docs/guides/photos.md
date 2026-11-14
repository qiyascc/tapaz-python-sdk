# Photos

Photos go to the tap.az photo service before the ad is created. Each upload returns an id; the ad lists its photos by those ids in `photo_ids`. Uploads need a session.

## Upload

```python
photo = tap.photos.upload("flat.jpg")
photo = tap.photos.upload(open("flat.png", "rb"))
photo = tap.photos.upload(raw_bytes, "flat.jpg")
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `photo` | | A path (`str` or `Path`), a binary file object, or bytes |
| `filename` | the file's name, or `photo.jpg` | The name sent with the upload |
| `content_type` | guessed from the name, else `image/jpeg` | The MIME type |

An empty file, a file opened in text mode or any other type raises `InvalidRequestError` before the upload. A photo that is too big for tap.az comes back as `BadRequestError`.

The result is a {py:class}`~tapaz_sdk.Photo` with `id`, `thumbnail_url` and `raw`.

## Several photos

```python
from pathlib import Path

photo_ids = [tap.photos.upload(path).id for path in sorted(Path("photos").glob("*.jpg"))]
```

The order of `photo_ids` is the order on the ad; the first is the main photo. With the async client, upload in parallel:

```python
photos = await asyncio.gather(*(tap.photos.upload(path) for path in paths))
photo_ids = [p.id for p in photos]
```

`gather` keeps the order of its arguments, so the ids stay in the order of `paths`.

## Rotate

```python
turned = tap.photos.rotate(photo.id, 90)
```

The angle is `90`, `180` or `270` (90 by default). Rotating returns a **new** photo with a new id; put that id in the ad.

## Retries

Unlike ad mutations, uploads and rotations are retried with backoff when the network fails. A repeated upload can at most leave an unused photo on the photo service, which does no harm, so retrying is the better default here.
