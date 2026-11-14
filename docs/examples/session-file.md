# A session file

tap.az signs in by SMS, which needs a person to read the code. Do it once, keep the cookie, and every later run starts signed in.

```python
import os
from pathlib import Path

from tapaz_sdk import AuthenticationError, TapAz

SESSION = Path(os.environ.get("TAPAZ_SESSION_FILE", "tapaz.session"))


def sign_in(tap: TapAz) -> None:
    phone = os.environ.get("TAPAZ_PHONE") or input("Phone: ")
    sent = tap.auth.send_code(phone)
    if sent.note:
        print(sent.note)
    login = tap.auth.verify(phone, input("SMS code: "))
    SESSION.write_text(login.cookie)
    SESSION.chmod(0o600)
    print("Signed in as", login.user.name)


def signed_in_client() -> TapAz:
    tap = TapAz(SESSION.read_text().strip() if SESSION.exists() else None)
    if tap.signed_in:
        try:
            tap.me()
            return tap
        except AuthenticationError:
            print("The saved session expired")
    sign_in(tap)
    return tap


if __name__ == "__main__":
    with signed_in_client() as tap:
        user = tap.me()
        print(user.name, user.phone, "shop" if user.is_shop else "private")
        SESSION.write_text(tap.cookie)
```

- `tap.signed_in` only says whether a cookie is loaded; `tap.me()` asks tap.az whether it still works.
- On `AuthenticationError` the script signs in again and overwrites the file.
- The cookie is written again at the end, so cookies tap.az renewed are kept.
- `chmod(0o600)` keeps the file private on Linux and macOS.

Other scripts import `signed_in_client`:

```python
from session_file import signed_in_client

with signed_in_client() as tap:
    print(len(tap.ads.all("PUBLISHED")))
```
