# tap.az Python SDK

A typed Python client for [tap.az](https://tap.az), the Azerbaijani classifieds site. It signs in with an SMS code, reads the category catalog with every property of every category, checks an ad the way the tap.az form does, posts it with photos, and lists, edits, prolongs and deletes the ads of the account. There is a sync client, `TapAz`, and an async one, `AsyncTapAz`, with the same methods.

```python
from tapaz_sdk import TapAz

with TapAz(saved_cookie) as tap:
    photo = tap.photos.upload("flat-1.jpg")
    ad = tap.ads.create(
        635,
        "3 room flat in Yasamal, renovated, close to the metro.",
        properties={"740": "3722", "737": 85, "812": "Elmler Akademiyasi metro", "900": True},
        price=150000,
        photo_ids=[photo.id],
    )
    print(ad.id, ad.status, ad.url)
```

:::{important}
This is not an official tap.az product. It talks to the same GraphQL API, photo service and login service as the tap.az website, as one signed in account, with its own User-Agent. It does not solve Cloudflare challenges: when one appears you get `BlockedError`.
:::

## Where to go next

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Installation
:link: getting-started/installation
:link-type: doc

Python versions, a virtual environment step by step, pip, uv and Poetry.
:::

:::{grid-item-card} Signing in
:link: getting-started/sign-in
:link-type: doc

The SMS code login, saving the session and loading it back.
:::

:::{grid-item-card} Quickstart
:link: getting-started/quickstart
:link-type: doc

Find a category, read its properties, post an ad.
:::

:::{grid-item-card} Categories and properties
:link: guides/catalog
:link-type: doc

How tap.az describes an ad, and how to fill in any category.
:::

:::{grid-item-card} Posting ads
:link: guides/ads
:link-type: doc

Every argument of `create`, the checks done before sending, contacts and regions.
:::

:::{grid-item-card} Safety and retries
:link: guides/safety
:link-type: doc

Which calls are retried and what an unknown outcome means.
:::

:::{grid-item-card} Examples
:link: examples/index
:link-type: doc

A session file, a category explorer, posting from JSON, CSV export, a prolong job, Django.
:::

:::{grid-item-card} API reference
:link: reference/api
:link-type: doc

Every class, method and field.
:::

::::

## What the SDK takes care of

- **SMS login.** tap.az signs in by phone only. The SDK sends the code, checks it and turns it into a session cookie you can save and reuse.
- **The form rules.** tap.az has thousands of categories, each with its own properties. Before an ad is sent, the SDK loads the category and checks every value the way the website form does: required properties, valid options, number ranges, properties that only apply after another choice, price, photo and title rules. Every problem is listed at once.
- **Ads are never posted twice.** A timeout on a create, an update, a delete, a prolong or the sign in raises `OutcomeUnknownError` instead of trying again.
- **Reads ride over hiccups.** Catalog reads, ad pages and photo uploads are retried with backoff.
- **No Cloudflare games.** Challenge pages raise `BlockedError`. Cloudflare cookies are dropped on the way in and on the way out.
- **Typed results.** Every answer is a frozen pydantic model, with the raw answer kept in `.raw`.
- **Everything is configurable.** Addresses, paths, region and delete reason defaults, timeouts, retries and every message.

```{toctree}
:hidden:
:caption: Getting started

getting-started/installation
getting-started/sign-in
getting-started/quickstart
getting-started/configuration
```

```{toctree}
:hidden:
:caption: Guides

guides/catalog
guides/ads
guides/managing
guides/photos
guides/async
guides/errors
guides/safety
guides/messages
guides/advanced
guides/testing
```

```{toctree}
:hidden:
:caption: Examples

examples/index
examples/session-file
examples/find-category
examples/post-from-json
examples/export-csv
examples/prolong-job
examples/django
```

```{toctree}
:hidden:
:caption: Reference

reference/api
reference/models
reference/changelog
reference/faq
```

```{toctree}
:hidden:
:caption: Project

project/development
project/about
```
