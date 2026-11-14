# Categories and properties

tap.az covers everything from flats to phones to jobs, and every category asks for different details. A flat has rooms and an area, a car has a make and a year. tap.az calls these details **properties**. To post an ad you pick a leaf category and fill in its properties. This page explains how to find both.

Catalog calls need no session and are retried like other reads.

## The category tree

```python
for root in tap.catalog.categories():
    for category in root.walk():
        depth = (category.path or "").count("/")
        print("  " * depth, category.id, category.name, "(leaf)" if category.leaf else "")
```

`categories()` returns the top level categories as a tuple of {py:class}`~tapaz_sdk.Category`, each with its `children`, four levels deep. `walk()` yields the category itself and then everything below it.

| `Category` field | Meaning |
| --- | --- |
| `id` | The category id as text, such as `"635"` |
| `name` | The name tap.az shows |
| `path` | The path of the category on tap.az |
| `leaf` | `True` when the category has no children. Ads can only be posted in a leaf |
| `photo_required` | tap.az wants at least one photo |
| `price_required` | tap.az wants a price |
| `title_required` | The ad needs a title. When `False`, tap.az writes the title itself |
| `free_limit` | How many free ads the category allows, when tap.az says |
| `warning` | A warning tap.az shows on the form for this category |
| `children` | The sub categories |
| `properties` | The properties, filled in by `category()` only |
| `raw` | The whole answer |

The tree from `categories()` does not include properties, to keep it small. Ask for one category to get them.

## One category with its properties

```python
category = tap.catalog.category(635)
for prop in category.properties:
    print(prop.id, prop.name, prop.kind, prop.required)
```

`category(category_id)` accepts the id as a number or text. An unknown id raises `InvalidRequestError`.

`category.find_property("740")` returns one property by id, or `None`.

### Properties

Each property is a {py:class}`~tapaz_sdk.Property`:

| Field | Meaning |
| --- | --- |
| `id` | The property id as text, used as the key in `properties` |
| `name` | The label on the tap.az form |
| `kind` | A `PropertyKind`: `collection`, `range`, `boolean`, `string` or `other` |
| `required` | The form will not submit without it |
| `editable` | tap.az lets the value change after the ad is posted |
| `depends_on` | The id of another property this one depends on, see below |
| `unit` | A unit such as `m2`, for ranges |
| `hint` | The hint text under the field |
| `min`, `max`, `step` | The allowed range, for ranges |
| `hidden_when` | When set, the property is hidden for some values of another property |
| `options` | For collections, the choices as `Option` objects with `id` and `name` |

### Kinds and values

| `kind` | On the tap.az form | Value in `properties` |
| --- | --- | --- |
| `collection` | A list to pick from | The `id` of one option, as text or a number |
| `range` | A number field | An `int` or a `float` between `min` and `max`. Text such as `"85,5"` is accepted too |
| `boolean` | A tick box | `True` or `False` |
| `string` | A text field | Text |
| `other` | Something this SDK cannot fill in | Leave it out. Giving a value raises an error |

To turn an option name into its id (the names are whatever tap.az shows, in Azerbaijani):

```python
listing_type = category.find_property("740")
choice = next(o for o in listing_type.options if o.name == "Satılır")
values = {"740": choice.id}
```

`prop.option(option_id)` does the reverse lookup and returns the `Option` or `None`.

## Dependent properties

Some properties only exist after another choice. On a flat, picking "For rent" adds a "Rent period" field that is not there for "For sale". tap.az models this in two ways, and the SDK follows both.

**Options that enable properties.** An `Option` has `enables`, a tuple of property ids that become active when that option is chosen. In the example above, the "For rent" option enables the rent period property.

**Properties whose options depend on a parent.** A property with `depends_on` set takes its option list from the value chosen in the parent property. Its own `options` may be empty; the real list comes from:

```python
options = tap.catalog.property_options("3724")
for option in options:
    print(option.id, option.name, option.property_id)
```

`property_options(parent_option_id)` takes the **option id chosen in the parent**, not a property id. Each returned option carries `property_id`, the property it belongs to.

A complete lookup for a dependent value:

```python
category = tap.catalog.category(635)
values = {"740": "3724"}
for prop in category.properties:
    if prop.depends_on == "740":
        choices = [o for o in tap.catalog.property_options(values["740"]) if o.property_id == prop.id]
        print(prop.name, [(o.id, o.name) for o in choices])
```

The SDK does the same lookup when it checks an ad, so a dependent value that is not valid for the chosen parent is caught before sending.

## Hidden properties

`hidden_when` is a {py:class}`~tapaz_sdk.HiddenWhen` with `property` (a property id) and `options` (option ids). When the other property has one of those options, this property is hidden on the form and must be left out. The checks treat it as inactive.

## Regions

```python
for region in tap.catalog.regions():
    print(region.id, region.name, "default" if region.default else "")
```

Each is a {py:class}`~tapaz_sdk.Region` with `id`, `name` and `default`. Pass the id as `region_id` when posting. Without it the ad goes to the `default_region` setting, `420`, which is Baku.

## Contact types

```python
for kind in tap.catalog.contact_types():
    print(kind.id, kind.name, kind.default, kind.type)
```

Each is a {py:class}`~tapaz_sdk.ContactTypeInfo` with the id (`CALLS_AND_MESSAGES`, `ONLY_CALLS`, `ONLY_MESSAGES`), the name tap.az shows and whether it is the default. `kind.type` is the matching `ContactType` enum, or `None` for a type this SDK does not know.

## Cache what you can

The tree and the properties change rarely. If you post many ads, load `category()` once per category and keep it. The SDK loads the category again inside `create` and `validate` so the checks always use the current rules; your cache is for building forms and lookups.
