# Post from JSON

Ads described in JSON files, one per ad, with the photos next to them. The script checks each ad against its category first, uploads the photos only when the ad is valid, posts it and writes the result back.

```text
ads/
    flat-yasamal/
        ad.json
        1.jpg
        2.jpg
    iphone-13/
        ad.json
        1.jpg
```

`ad.json`:

```json
{
  "category_id": 635,
  "body": "3 room flat in Yasamal, renovated, close to the metro.",
  "price": 150000,
  "properties": {"740": "3722", "737": 85, "812": "Elmler Akademiyasi metro", "900": true},
  "contact_type": "CALLS_AND_MESSAGES"
}
```

Any keyword argument of `tap.ads.create` can go into the file.

```python
import json
import sys
from pathlib import Path

from tapaz_sdk import InvalidRequestError, MutationError, OutcomeUnknownError, TapAz

PHOTOS = {".jpg", ".jpeg", ".png", ".webp"}


def post(tap: TapAz, folder: Path) -> None:
    if (folder / "posted.json").exists() or (folder / "unknown.txt").exists():
        return
    spec = json.loads((folder / "ad.json").read_text(encoding="utf-8"))
    category_id, body = spec.pop("category_id"), spec.pop("body")
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in PHOTOS)
    try:
        tap.ads.validate(category_id, body, properties=spec.get("properties"), price=spec.get("price"),
                         title=spec.get("title"), photo_ids=["check"] * len(files))
    except InvalidRequestError as exc:
        print(f"{folder.name}: not valid")
        for problem in exc.errors or [{"field": "", "error": str(exc)}]:
            print(f"    {problem['field']}: {problem['error']}")
        return
    photo_ids = [tap.photos.upload(path).id for path in files]
    try:
        ad = tap.ads.create(category_id, body, photo_ids=photo_ids, **spec)
    except MutationError as exc:
        print(f"{folder.name}: tap.az refused it: {exc}")
        return
    except OutcomeUnknownError:
        (folder / "unknown.txt").write_text("check the pending tab before posting again\n")
        print(f"{folder.name}: no answer, check the pending tab")
        return
    (folder / "posted.json").write_text(json.dumps({"id": ad.id, "url": ad.url, "status": ad.status.value}))
    print(f"{folder.name}: posted {ad.id} {ad.url}")


def main(root: str) -> None:
    from session_file import signed_in_client

    with signed_in_client() as tap:
        for folder in sorted(Path(root).iterdir()):
            if (folder / "ad.json").exists():
                post(tap, folder)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "ads")
```

- `validate` runs before any upload, with placeholder photo ids, so an invalid ad costs nothing.
- `posted.json` marks a folder as done; a rerun skips it.
- `unknown.txt` marks an unknown outcome; the folder is skipped until you check the pending tab and remove the file.
- Photos are uploaded in name order; `1.jpg` becomes the main photo.
- `signed_in_client` is from [A session file](session-file.md).
