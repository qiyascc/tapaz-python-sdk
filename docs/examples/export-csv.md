# Export to CSV

Every ad of the account, one row each, with the tab it is in.

```python
import csv
import sys

from tapaz_sdk import AdTab

FIELDS = ["id", "tab", "status", "title", "price", "expires_at", "updated_at", "reject_reason", "url"]


def main(path: str) -> None:
    from session_file import signed_in_client

    count = 0
    with signed_in_client() as tap, open(path, "w", newline="", encoding="utf-8-sig") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        for tab in AdTab:
            for ad in tap.ads.all(tab, page_size=100):
                writer.writerow({
                    "id": ad.id,
                    "tab": tab.value.lower(),
                    "status": ad.status.value,
                    "title": ad.title or "",
                    "price": "" if ad.price is None else f"{ad.price:g}",
                    "expires_at": ad.expires_at.isoformat() if ad.expires_at else "",
                    "updated_at": ad.updated_at.isoformat() if ad.updated_at else "",
                    "reject_reason": ad.reject_reason or "",
                    "url": ad.url or "",
                })
                count += 1
    print(f"{count} ads written to {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tapaz-ads.csv")
```

`utf-8-sig` makes Excel show Azerbaijani letters correctly. `f"{ad.price:g}"` writes `150000` rather than `150000.0`.

For pandas:

```python
import pandas as pd

with signed_in_client() as tap:
    frame = pd.DataFrame([ad.model_dump(exclude={"raw"}) for ad in tap.ads.all()])
print(frame[["id", "title", "status", "price"]])
```

Models are pydantic models, so `model_dump()` turns each ad into a dict.
