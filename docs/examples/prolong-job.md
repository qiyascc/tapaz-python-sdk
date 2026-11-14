# A prolong job

Prolong every expired ad once a day.

```python
import logging
import sys

from tapaz_sdk import AdTab, MutationError, OutcomeUnknownError, TapAzError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("prolong")


def main() -> int:
    from session_file import signed_in_client

    failures = 0
    with signed_in_client() as tap:
        expired = tap.ads.all(AdTab.EXPIRED)
        log.info("%d expired ads", len(expired))
        for ad in expired:
            try:
                if tap.ads.prolong(ad.id):
                    log.info("prolonged %s %s", ad.id, ad.title)
            except MutationError as exc:
                log.warning("tap.az refused %s: %s", ad.id, exc)
                failures += 1
            except OutcomeUnknownError:
                log.warning("no answer for %s, it will be checked tomorrow", ad.id)
            except TapAzError as exc:
                log.error("could not prolong %s: %s", ad.id, exc)
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

Whether an ad can be prolonged, and whether it costs anything, is decided by tap.az for the account and the category. A refusal comes back as `MutationError` with tap.az's reason.

Schedule it with cron:

```text
0 9 * * * cd /home/shop/tapaz && .venv/bin/python prolong.py >> prolong.log 2>&1
```

or with Windows Task Scheduler from CMD:

```bat
schtasks /Create /SC DAILY /ST 09:00 /TN "tapaz prolong" /TR "C:\tapaz\.venv\Scripts\python.exe C:\tapaz\prolong.py"
```

Set `TAPAZ_SESSION_FILE` to an absolute path when the job does not start in the script's folder.
