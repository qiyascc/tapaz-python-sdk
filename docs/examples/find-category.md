# Find a category

Posting needs a leaf category id and the ids of its properties and options. This script searches the tree by a word in the name, then prints every property of the chosen category as a Python template you can paste into your code.

```python
import sys

from tapaz_sdk import PropertyKind, TapAz


def search(tap: TapAz, word: str) -> None:
    word = word.lower()
    for root in tap.catalog.categories():
        for category in root.walk():
            if category.leaf and word in (category.name or "").lower():
                print(f"{category.id:>6}  {category.name}  ({category.path})")


def describe(prop) -> str:
    parts = [prop.name]
    if prop.kind == PropertyKind.COLLECTION and prop.options:
        shown = ", ".join(f"{o.id}={o.name}" for o in prop.options[:12])
        parts.append(shown + (" ..." if len(prop.options) > 12 else ""))
    if prop.kind == PropertyKind.RANGE and prop.min is not None and prop.max is not None:
        parts.append(f"{prop.min:g} to {prop.max:g} {prop.unit or ''}".strip())
    if prop.required:
        parts.append("required")
    if prop.depends_on:
        parts.append(f"depends on {prop.depends_on}")
    if prop.hidden_when:
        parts.append(f"hidden when {prop.hidden_when.property} is one of {list(prop.hidden_when.options)}")
    return "; ".join(parts)


EMPTY = {PropertyKind.COLLECTION: '""', PropertyKind.RANGE: "0", PropertyKind.BOOLEAN: "False",
         PropertyKind.STRING: '""'}


def template(tap: TapAz, category_id: str) -> None:
    category = tap.catalog.category(category_id)
    print(f"# {category.name}")
    print(f"# price required: {category.price_required}, photo required: {category.photo_required}, "
          f"title required: {category.title_required}")
    if category.warning:
        print(f"# tap.az says: {category.warning}")
    print("properties = {")
    for prop in category.properties:
        if prop.kind in EMPTY:
            print(f'    "{prop.id}": {EMPTY[prop.kind]},  # {describe(prop)}')
    print("}")


if __name__ == "__main__":
    with TapAz() as tap:
        if len(sys.argv) == 3 and sys.argv[1] == "search":
            search(tap, sys.argv[2])
        elif len(sys.argv) == 3 and sys.argv[1] == "show":
            template(tap, sys.argv[2])
        else:
            print("usage: find_category.py search <word> | show <category id>")
```

Run it in two steps:

```bash
python find_category.py search mənzil
python find_category.py show 635
```

The second command prints something like this (names and ids here are from the SDK's test data; tap.az shows its own):

```python
properties = {
    "740": "",  # Listing type; 3722=For sale, 3724=For rent; required
    "994": "",  # Rent period; required; depends on 740
    "737": 0,  # Area; 1 to 100000 m2; required
    "812": "",  # Location; required
    "900": False,  # Repaired
}
```

Fill in the values, delete the lines you do not need, and run `tap.ads.validate(...)` to check the result. A property that `depends on` another takes its options from `tap.catalog.property_options(<chosen parent option>)`; see [Categories and properties](../guides/catalog.md#dependent-properties).

The catalog is public, so this script needs no session.
