# Django

Ads kept in a Django model and posted by a management command, with the tap.az session stored in the database so every worker shares it.

## Models

```python
from django.db import models


class TapAzSession(models.Model):
    cookie = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)


class Listing(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft"
        POSTING = "posting"
        POSTED = "posted"
        UNKNOWN = "unknown"
        INVALID = "invalid"

    category_id = models.PositiveIntegerField()
    body = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    properties = models.JSONField(default=dict)
    photos = models.JSONField(default=list)
    state = models.CharField(max_length=10, choices=State.choices, default=State.DRAFT)
    tapaz_id = models.CharField(max_length=20, blank=True)
    tapaz_url = models.URLField(blank=True)
    problems = models.JSONField(default=list, blank=True)
```

## The client

```python
from tapaz_sdk import TapAz

from .models import TapAzSession


def client() -> TapAz:
    row = TapAzSession.objects.first()
    return TapAz(row.cookie if row else None)


def remember(tap: TapAz) -> None:
    TapAzSession.objects.update_or_create(pk=1, defaults={"cookie": tap.cookie})
```

SMS login needs a person, so sign in once from the shell and store the cookie:

```python
from listings.tapaz import client, remember

tap = client()
tap.auth.send_code("050 123 45 67")
tap.auth.verify("050 123 45 67", "1234")
remember(tap)
```

## The command

`listings/management/commands/post_to_tapaz.py`:

```python
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from tapaz_sdk import InvalidRequestError, MutationError, OutcomeUnknownError, TapAzError

from listings.models import Listing
from listings.tapaz import client, remember


class Command(BaseCommand):
    help = "Post draft listings to tap.az"

    def handle(self, *args, **options):
        with client() as tap:
            try:
                tap.me()
            except TapAzError as exc:
                raise CommandError(f"Sign in to tap.az first: {exc}")
            for listing in Listing.objects.filter(state=Listing.State.DRAFT):
                self.post(tap, listing)
            remember(tap)

    def post(self, tap, listing):
        listing.state = Listing.State.POSTING
        listing.save(update_fields=["state"])
        price = float(listing.price) if listing.price is not None else None
        try:
            tap.ads.validate(listing.category_id, listing.body, properties=listing.properties, price=price,
                             photo_ids=["check"] * len(listing.photos))
            ids = [tap.photos.upload(Path(settings.MEDIA_ROOT) / name).id for name in listing.photos]
            ad = tap.ads.create(listing.category_id, listing.body, properties=listing.properties, price=price,
                                photo_ids=ids)
        except InvalidRequestError as exc:
            listing.state, listing.problems = Listing.State.INVALID, list(exc.errors) or [{"error": str(exc)}]
        except MutationError as exc:
            listing.state, listing.problems = Listing.State.INVALID, list(exc.errors)
        except OutcomeUnknownError:
            listing.state = Listing.State.UNKNOWN
        except TapAzError as exc:
            listing.state, listing.problems = Listing.State.DRAFT, [{"error": str(exc)}]
        else:
            listing.state, listing.tapaz_id, listing.tapaz_url = Listing.State.POSTED, ad.id or "", ad.url or ""
            listing.problems = []
        listing.save()
        self.stdout.write(f"{listing.pk}: {listing.state} {listing.tapaz_url}")
```

- `POSTING` is saved before the request, so a crash halfway leaves the row out of the next run instead of posting it twice.
- `INVALID` rows carry the problems from `exc.errors`, ready to show in the admin next to the fields.
- `UNKNOWN` rows need a look at the pending tab on tap.az.
- `float(listing.price)` turns the `Decimal` from the model field into a plain number for the API.

Posting uploads photos and can take a while; run the command from cron or a task queue, not from a web request.
