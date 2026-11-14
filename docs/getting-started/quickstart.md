# Quickstart

This walk through posts one ad from a short script: it finds the category, reads what the category asks for, uploads a photo and posts. It assumes the SDK is installed ([Installation](installation.md)) and that you can receive SMS codes on the phone of the tap.az account.

## 1. Sign in once

Create `signin.py`:

```python
from pathlib import Path

from tapaz_sdk import TapAz

with TapAz() as tap:
    phone = input("Phone: ")
    sent = tap.auth.send_code(phone)
    if sent.note:
        print(sent.note)
    login = tap.auth.verify(phone, input("SMS code: "))
    Path("tapaz.session").write_text(login.cookie)
    print("Signed in as", login.user.name)
```

Run it once. It writes the session cookie to `tapaz.session`; every other script reads it from there. Add the file to `.gitignore`.

## 2. Find the category

tap.az has a deep tree of categories. Ads can only be posted in a leaf, a category with no children. Walk the tree and search by name:

```python
from tapaz_sdk import TapAz

with TapAz() as tap:
    for root in tap.catalog.categories():
        for category in root.walk():
            if category.leaf and "Mənzil" in (category.name or ""):
                print(category.id, category.name, category.path)
```

`walk()` goes through a category and everything under it. Write down the id of the category you want. The examples on this page use `635`, the apartments category from the README.

## 3. Read what the category asks for

```python
with TapAz() as tap:
    category = tap.catalog.category(635)
    print("price required:", category.price_required, "photo required:", category.photo_required)
    for prop in category.properties:
        options = [(o.id, o.name) for o in prop.options]
        print(prop.id, prop.name, prop.kind.value, "required" if prop.required else "", prop.unit or "", options)
```

Every property has an id, a name, a kind and, for lists, the ids of its options. The output tells you what to put in `properties`:

| Kind | Value to give | Example |
| --- | --- | --- |
| `collection` | The id of one of `prop.options`, as text | `"3722"` |
| `range` | A number between `prop.min` and `prop.max` | `85` |
| `boolean` | `True` or `False` | `True` |
| `string` | Text | `"Elmler Akademiyasi metro"` |

The ids in these docs come from the README example. Always take the real ids from `catalog.category(...)`.

## 4. Check the ad without posting

```python
from pathlib import Path

from tapaz_sdk import InvalidRequestError, TapAz

values = {"740": "3722", "737": 85, "812": "Elmler Akademiyasi metro", "900": True}

with TapAz(Path("tapaz.session").read_text()) as tap:
    try:
        tap.ads.validate(635, "3 room flat in Yasamal, renovated, close to the metro.",
                         properties=values, price=150000, photo_ids=["placeholder"])
        print("The ad passes the checks")
    except InvalidRequestError as exc:
        for problem in exc.errors:
            print(problem["field"], problem["error"])
```

`validate` runs every check `create` runs and posts nothing. When something is wrong, `exc.errors` lists every problem, not only the first.

## 5. Upload the photo and post

```python
with TapAz(Path("tapaz.session").read_text()) as tap:
    photo = tap.photos.upload("flat-1.jpg")
    ad = tap.ads.create(
        635,
        "3 room flat in Yasamal, renovated, close to the metro.",
        properties=values,
        price=150000,
        photo_ids=[photo.id],
    )
    print(ad.id, ad.status, ad.url)
```

Line by line:

- `635` is the category id.
- The second argument is the text of the ad, up to 5000 characters.
- `properties` maps property ids to values, as in step 3.
- `price` is in AZN. Some categories require it, which the checks enforce.
- `photo_ids` are the ids from `photos.upload`.

The contact phone and email come from the account. The region is Baku (`420`) unless you pass `region_id`. More in [Posting ads](../guides/ads.md).

A new ad usually comes back with status `PENDING` while tap.az moderates it.

## 6. See it in the account

```python
with TapAz(Path("tapaz.session").read_text()) as tap:
    page = tap.ads.list("PENDING")
    for ad in page.items:
        print(ad.id, ad.title, ad.status)
```

## The same with async

```python
import asyncio
from pathlib import Path

from tapaz_sdk import AsyncTapAz


async def main() -> None:
    async with AsyncTapAz(Path("tapaz.session").read_text()) as tap:
        user = await tap.me()
        ads = await tap.ads.all("PUBLISHED")
        print(user.name, len(ads))


asyncio.run(main())
```

## Next steps

- [Categories and properties](../guides/catalog.md): dependent properties and hidden properties.
- [Posting ads](../guides/ads.md): contacts, regions, titles and every check.
- [Managing ads](../guides/managing.md): list, edit, prolong and delete.
