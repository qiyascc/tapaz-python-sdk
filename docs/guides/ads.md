# Posting ads

`tap.ads.create` posts an ad in a leaf category. Before it sends anything it loads the category, checks every value the way the tap.az form does and, when contact details are missing, reads them from the account. This page covers every argument and every check.

Posting needs a session; see [Signing in](../getting-started/sign-in.md).

## The call

```python
ad = tap.ads.create(
    635,
    "3 room flat in Yasamal, renovated, close to the metro.",
    properties={"740": "3722", "737": 85, "812": "Elmler Akademiyasi metro", "900": True},
    price=150000,
    photo_ids=[photo.id],
)
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `category_id` | | A leaf category, as a number or text |
| `body` | | The text of the ad, 1 to 5000 characters |
| `properties` | `None` | Property id to value, see [Categories and properties](catalog.md#kinds-and-values) |
| `price` | `None` | A positive number, in AZN |
| `title` | `None` | Up to 100 characters. Only needed when the category has `title_required` |
| `region_id` | the `default_region` setting | From `catalog.regions()`. 420 is Baku |
| `photo_ids` | `None` | Ids from `photos.upload`, in display order |
| `contact_type` | `ContactType.CALLS_AND_MESSAGES` | How buyers may reach you |
| `name` | `None` | Contact name, up to 100 characters |
| `email` | the account email | Contact email |
| `phones` | the account phone | One to three phone numbers |

The result is an {py:class}`~tapaz_sdk.Ad`, see [Reading ads](managing.md#read-one-ad).

## What is checked before sending

All of these raise {py:class}`~tapaz_sdk.InvalidRequestError` before the ad is sent. Wherever possible the problems are collected and reported together in `exc.errors`, a tuple of `{"field": ..., "error": ...}` dicts.

**Arguments**

- `body` is not empty and at most 5000 characters.
- `title`, when given, is at most 100 characters.
- `price`, when given, is a positive number. `True`, `0` and text that is not a number are refused.
- Ids contain no `/`, `?` or spaces.
- `contact_type` is one of the three types.
- `phones` has one to three entries, each with 9 to 12 digits.

**The category**

- The category exists. Otherwise `InvalidRequestError` names it.
- It is a leaf. A parent category such as "Real estate" cannot hold ads.

**Properties**

- Every key is a property of the category.
- Every required property that is active has a value.
- A value for a property that is not active (a dependent property whose parent choice does not enable it, or a hidden one) is refused.
- Collections get the id of a valid option. For dependent properties the valid options are loaded for the chosen parent.
- Ranges get a number between `min` and `max`.
- Booleans get `True` or `False`.
- Strings get non empty text.

**Category rules**

- A price when the category has `price_required`.
- At least one photo when it has `photo_required`.
- A title when it has `title_required`.

**Contacts**

- After filling in the account's phone and email, the ad must have a phone number and an email.

### Reading the problems

```python
from tapaz_sdk import InvalidRequestError

try:
    tap.ads.create(635, "Flat", properties={"737": 5000000})
except InvalidRequestError as exc:
    for problem in exc.errors:
        print(f"{problem['field']}: {problem['error']}")
```

might print

```text
properties.737: 'Area' must be between 1 and 100000
properties.740: 'Listing type' is required
price: price is required in this category
photo_ids: at least one photo is required in this category
```

for a category whose area property runs from 1 to 100000.

The exact wording comes from `messages.yaml` and can be changed; see [Messages](messages.md).

## Check without posting

```python
property_set = tap.ads.validate(635, body, properties=values, price=150000, photo_ids=["x"])
```

`validate` takes the same `category_id`, `body`, `properties`, `price`, `title` and `photo_ids` as `create`, runs the same property and category checks, and returns the property set it would send, grouped by kind:

```python
{
    "collection": [{"legacyId": "740", "value": "3722"}, {"legacyId": "812", "value": "Elmler Akademiyasi metro"}],
    "range": [{"legacyId": "737", "value": 85.0}],
    "boolean": [{"legacyId": "900", "value": True}],
}
```

Use it to check a form in your own product before the user presses a button. It reads the category, so it makes a request, but it never posts.

## Contacts

By default the ad shows the phone number and the email of the account, and buyers can call and write. To change that:

```python
from tapaz_sdk import ContactType

ad = tap.ads.create(
    635, body,
    properties=values,
    price=150000,
    photo_ids=ids,
    contact_type=ContactType.ONLY_MESSAGES,
    name="Leyla",
    phones=["050 123 45 67", "055 765 43 21"],
    email="sales@example.az",
)
```

| `ContactType` | Meaning |
| --- | --- |
| `CALLS_AND_MESSAGES` | Buyers can call and write. The default |
| `ONLY_CALLS` | Buyers can only call |
| `ONLY_MESSAGES` | The phone number is hidden; buyers write through tap.az |

The contact type can be given as text in any case, such as `"only_messages"`.

When `phones` or `email` is missing, the SDK reads the account with `tap.me()` and uses its phone and email. If the account has neither, `InvalidRequestError` asks you to pass them.

## Regions

```python
region = next(r for r in tap.catalog.regions() if r.name == "Sumqayıt")
ad = tap.ads.create(635, body, properties=values, price=150000, photo_ids=ids, region_id=region.id)
```

Without `region_id` the ad goes to `default_region` (`420`, Baku). Set `TAPAZ_DEFAULT_REGION` to change it for every ad.

## Titles

Most categories have titles generated by tap.az from the properties (`title_required` is `False`), and `title` can be left out. Where the category asks for a title, pass one of up to 100 characters.

## After posting

A new ad usually comes back with `status` `PENDING` while tap.az moderates it. It then moves to `APPROVED` or `PUBLISHED`, or to `REJECTED` with a `reject_reason`. Categories with a free limit may put an ad over the limit into `AWAITING_PAYMENT`; paying is done on the tap.az website.

## When tap.az refuses

| Error | Meaning |
| --- | --- |
| `MutationError` | tap.az refused the ad. `exc.errors` lists the problems and `exc.codes` their codes |
| `BannedError` | The account is banned (`USER_BANNED_ERROR`) |
| `UnconfirmedError` | The phone or email of the account is not confirmed (`UNCONFIRMED`) |
| `AuthenticationError` | The session is missing or expired |

`BannedError` and `UnconfirmedError` are subclasses of `MutationError`, so `except MutationError` catches all three.

## Timeouts

A timeout, a dropped connection or a 5xx while posting raises `OutcomeUnknownError`, and the ad is not sent again. tap.az may have created it. Look at `tap.ads.list("PENDING")` before posting again; see [Safety and retries](safety.md).
