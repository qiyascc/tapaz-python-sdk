from __future__ import annotations

from pathlib import Path

from tapaz_sdk import TapAz

SESSION_FILE = Path("tapaz.session")


def sign_in(tap: TapAz) -> None:
    if SESSION_FILE.exists():
        tap.use_cookie(SESSION_FILE.read_text().strip())
        return
    phone = input("Phone: ")
    sent = tap.auth.send_code(phone)
    if sent.note:
        print(sent.note)
    login = tap.auth.verify(phone, input("SMS code: "))
    SESSION_FILE.write_text(login.cookie)
    print(f"Signed in as {login.user.name}")


def main() -> None:
    with TapAz() as tap:
        sign_in(tap)
        photos = [tap.photos.upload(path).id for path in sorted(Path("photos").glob("*.jpg"))]
        ad = tap.ads.create(
            635,
            "3 room flat in Yasamal, renovated, close to the metro.",
            properties={"740": "3722", "737": 85, "812": "Elmler Akademiyasi metro"},
            price=150000,
            photo_ids=photos,
        )
        print(ad.id, ad.status.value, ad.url)


if __name__ == "__main__":
    main()
