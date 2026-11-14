# Models and enums

Everything the SDK returns is a frozen pydantic model. Fields are plain Python types, dates are timezone aware `datetime` objects, and models built from tap.az answers keep the original in `.raw`, which is left out of `repr()`. Being pydantic models, they have `model_dump()` and `model_dump_json()`.

| Model | Returned by | Guide |
| --- | --- | --- |
| `CodeSent` | `auth.send_code` | [Signing in](../getting-started/sign-in.md#what-send-code-returns) |
| `Login` | `auth.verify` | [Signing in](../getting-started/sign-in.md#what-verify-returns) |
| `User` | `auth.me`, `me()`, inside `Login` | [Signing in](../getting-started/sign-in.md) |
| `Category`, `Property`, `Option`, `HiddenWhen` | `catalog.categories`, `catalog.category`, `catalog.property_options` | [Categories and properties](../guides/catalog.md) |
| `Region` | `catalog.regions` | [Categories and properties](../guides/catalog.md#regions) |
| `ContactTypeInfo` | `catalog.contact_types` | [Categories and properties](../guides/catalog.md#contact-types) |
| `Ad` | `ads.create`, `ads.update`, `ads.get`, `ads.all` | [Managing ads](../guides/managing.md#read-one-ad) |
| `AdPage` | `ads.list` | [Managing ads](../guides/managing.md#list-the-account-s-ads) |
| `DeleteReason` | `ads.delete_reasons` | [Managing ads](../guides/managing.md#delete-an-ad) |
| `Deleted` | `ads.delete` | [Managing ads](../guides/managing.md#delete-an-ad) |
| `Photo` | `photos.upload`, `photos.rotate` | [Photos](../guides/photos.md) |

```{eval-rst}
.. autoclass:: tapaz_sdk.CodeSent
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.Login
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.User
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.Category
   :members: walk, find_property
   :undoc-members: false
.. autoclass:: tapaz_sdk.Property
   :members: option
   :undoc-members: false
.. autoclass:: tapaz_sdk.Option
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.HiddenWhen
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.Region
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.ContactTypeInfo
   :members: type
   :undoc-members: false
.. autoclass:: tapaz_sdk.Ad
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.AdPage
   :members: has_more
   :undoc-members: false
.. autoclass:: tapaz_sdk.DeleteReason
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.Deleted
   :members:
   :undoc-members: false
.. autoclass:: tapaz_sdk.Photo
   :members:
   :undoc-members: false
```

## Enums

| Enum | Values |
| --- | --- |
| `AdStatus` | `PENDING`, `APPROVED`, `PUBLISHED`, `REJECTED`, `EXPIRED`, `ARCHIVED`, `AWAITING_PAYMENT`, `UNKNOWN`. `is_live` is `True` for `APPROVED` and `PUBLISHED` |
| `AdTab` | `PENDING`, `PUBLISHED`, `REJECTED`, `EXPIRED`, `ARCHIVED`, `AWAITING_PAYMENT` |
| `ContactType` | `CALLS_AND_MESSAGES`, `ONLY_CALLS`, `ONLY_MESSAGES` |
| `PropertyKind` | `collection`, `range`, `boolean`, `string`, `other` |

All four are string enums: `AdStatus.PENDING == "PENDING"` is `True`.

```{eval-rst}
.. autoclass:: tapaz_sdk.AdStatus
   :members: is_live, parse
   :undoc-members:
   :member-order: bysource
.. autoclass:: tapaz_sdk.AdTab
   :members:
   :undoc-members:
   :member-order: bysource
.. autoclass:: tapaz_sdk.ContactType
   :members:
   :undoc-members:
   :member-order: bysource
.. autoclass:: tapaz_sdk.PropertyKind
   :members:
   :undoc-members:
   :member-order: bysource
```
