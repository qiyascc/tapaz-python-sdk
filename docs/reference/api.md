# API reference

Generated from the code. The code has no docstrings, so the explanations live in the guides; this page lists every public class, method and argument in one place, with a link to the guide for each part.

Import everything from the top level package: `from tapaz_sdk import TapAz, AdTab, MutationError`. The resource classes are reached through a client (`tap.auth`, `tap.catalog`, `tap.ads`, `tap.photos`).

## Clients

See [Quickstart](../getting-started/quickstart.md) and [Async](../guides/async.md).

```{eval-rst}
.. autoclass:: tapaz_sdk.TapAz
   :members: me, graphql, cookie, signed_in, use_cookie, forget_session, close

.. autoclass:: tapaz_sdk.AsyncTapAz
   :members: me, graphql, close
```

| Constructor argument | Meaning |
| --- | --- |
| `cookie` | Optional session cookie, a `Cookie` header string |
| `settings` | A ready `Settings` object |
| `config_file` | Path of a config file |
| `http_client` | Your own `httpx.Client` or `httpx.AsyncClient` |
| any setting | Such as `timeout=10` |

## `tap.auth`

See [Signing in](../getting-started/sign-in.md).

```{eval-rst}
.. autoclass:: tapaz_sdk.resources.Auth
   :members: send_code, verify, me
```

## `tap.catalog`

See [Categories and properties](../guides/catalog.md).

```{eval-rst}
.. autoclass:: tapaz_sdk.resources.Catalog
   :members: categories, category, property_options, regions, contact_types
```

## `tap.ads`

See [Posting ads](../guides/ads.md) and [Managing ads](../guides/managing.md).

```{eval-rst}
.. autoclass:: tapaz_sdk.resources.Ads
   :members: create, validate, update, delete, delete_reasons, prolong, get, list, all
```

## `tap.photos`

See [Photos](../guides/photos.md).

```{eval-rst}
.. autoclass:: tapaz_sdk.resources.Photos
   :members: upload, rotate
```

## Helpers

See [Advanced use](../guides/advanced.md#global-ids-and-numeric-ids).

```{eval-rst}
.. autofunction:: tapaz_sdk.gid
.. autofunction:: tapaz_sdk.legacy_id
```

## Settings

See [Configuration](../getting-started/configuration.md).

```{eval-rst}
.. autofunction:: tapaz_sdk.load_settings

.. autoclass:: tapaz_sdk.Settings
   :members: resolved_user_agent, check_transport
   :undoc-members: false

.. autoclass:: tapaz_sdk.Endpoints
   :members:
   :undoc-members: false
```

## Messages

See [Messages](../guides/messages.md).

```{eval-rst}
.. autofunction:: tapaz_sdk.messages.use
.. autofunction:: tapaz_sdk.messages.reset
.. autofunction:: tapaz_sdk.messages.catalog
.. autofunction:: tapaz_sdk.messages.text
```

## Errors

See [Errors](../guides/errors.md).

```{eval-rst}
.. autoexception:: tapaz_sdk.TapAzError
.. autoexception:: tapaz_sdk.ConfigurationError
.. autoexception:: tapaz_sdk.SessionRequiredError
.. autoexception:: tapaz_sdk.InvalidRequestError
.. autoexception:: tapaz_sdk.TransportError
.. autoexception:: tapaz_sdk.NotSentError
.. autoexception:: tapaz_sdk.OutcomeUnknownError
.. autoexception:: tapaz_sdk.BlockedError
.. autoexception:: tapaz_sdk.APIError
.. autoexception:: tapaz_sdk.AuthenticationError
.. autoexception:: tapaz_sdk.NotFoundError
.. autoexception:: tapaz_sdk.RateLimitError
.. autoexception:: tapaz_sdk.ServerError
.. autoexception:: tapaz_sdk.BadRequestError
.. autoexception:: tapaz_sdk.InvalidCodeError
.. autoexception:: tapaz_sdk.GraphQLError
.. autoexception:: tapaz_sdk.MutationError
   :members: codes
.. autoexception:: tapaz_sdk.BannedError
.. autoexception:: tapaz_sdk.UnconfirmedError
```
