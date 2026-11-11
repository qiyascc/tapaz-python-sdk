from __future__ import annotations

import pytest

from tapaz_sdk import AdStatus, AdTab, InvalidRequestError, MutationError, NotFoundError, gid

from .conftest import SALE


def test_create_builds_the_ad_params(tap, site):
    ad = tap.ads.create(635, "3 room flat, renovated, near the metro.", properties=SALE, price=150000,
                        photo_ids=["p1", "p2"])
    assert ad.id == "5002" and ad.status == AdStatus.PENDING
    assert ad.url == "https://tap.az/elanlar/dasinmaz-emlak/menziller/5002"
    params = site.last("CreateAd")["variables"]["p"]
    assert params["categoryId"] == gid("Category", 635) and params["regionId"] == gid("Region", 420)
    assert params["source"] == "DESKTOP" and params["photoIds"] == ["p1", "p2"] and params["price"] == 150000.0
    assert params["propertySet"] == {
        "collection": [{"legacyId": "740", "value": "3722"}, {"legacyId": "812", "value": "Nizami metro"}],
        "range": [{"legacyId": "737", "value": 85.0}],
        "boolean": [{"legacyId": "900", "value": True}],
    }
    assert params["contactAttributes"] == {"contactType": "CALLS_AND_MESSAGES", "email": "q@tap.test",
                                           "phones": ["+994501112233"]}
    assert "title" not in params


def test_create_with_contact_skips_the_profile(tap, site):
    tap.ads.create("635", "Flat", properties=SALE, price=1000, photo_ids=["p"], contact_type="only_messages",
                   name="Qiyas", email="me@example.com", phones=["+994551234567"])
    assert "CurrentUser" not in site.ops()
    contact = site.last("CreateAd")["variables"]["p"]["contactAttributes"]
    assert contact == {"contactType": "ONLY_MESSAGES", "email": "me@example.com", "phones": ["+994551234567"],
                       "name": "Qiyas"}


def test_dependent_property(tap, site):
    rent = {"740": "3724", "994": "38046", "737": 60, "812": "Yasamal"}
    assert tap.ads.validate(635, "Flat for rent", properties=rent, price=800, photo_ids=["p"])["collection"][1] == {
        "legacyId": "994", "value": "38046"}
    with pytest.raises(InvalidRequestError) as missing:
        tap.ads.validate(635, "Flat for rent", properties={**rent, "994": "1"}, price=800,
                         photo_ids=["p"])
    assert "not an option" in str(missing.value)
    with pytest.raises(InvalidRequestError) as inactive:
        tap.ads.validate(635, "Flat", properties={**SALE, "994": "38046"}, price=800, photo_ids=["p"])
    assert "only applies" in str(inactive.value)


def test_validation_collects_every_problem(tap, site):
    with pytest.raises(InvalidRequestError) as bad:
        tap.ads.create(635, "Flat", properties={"740": "3722", "737": 0, "900": "yes", "1": "x"})
    fields = {e["field"] for e in bad.value.errors}
    assert fields == {"properties.1", "properties.737", "properties.900", "properties.812", "price", "photo_ids"}
    assert "CreateAd" not in site.ops()
    with pytest.raises(InvalidRequestError):
        tap.ads.create(606, "Flat", properties=SALE, price=1, photo_ids=["p"])
    with pytest.raises(InvalidRequestError):
        tap.ads.create(635, "", properties=SALE)
    with pytest.raises(InvalidRequestError):
        tap.ads.create(635, "Flat", price=-5)
    with pytest.raises(InvalidRequestError):
        tap.ads.create(635, "Flat", phones=["12"])


def test_site_validation_errors(tap):
    with pytest.raises(MutationError) as refused:
        tap.ads.create(635, "Flat", properties=SALE, price=1, photo_ids=["p"])
    assert refused.value.codes == frozenset({"VALIDATION_ERROR"}) and "price: is too low" in str(refused.value)


def test_update_sends_only_booleans(tap, site):
    ad = tap.ads.update(5001, 635, "New text", properties=SALE, price=140000, photo_ids=["p1"])
    assert ad.id == "5001"
    variables = site.last("UpdateAd")["variables"]
    assert variables["id"] == gid("Ad", 5001) and variables["source"] == "DESKTOP"
    assert variables["p"] == {"body": "New text", "contactType": "CALLS_AND_MESSAGES", "photoIds": ["p1"],
                              "propertySet": {"boolean": [{"legacyId": "900", "value": True}]}, "price": 140000.0}


def test_delete_prefers_the_configured_reason(tap, site):
    done = tap.ads.delete(5001)
    assert done.deleted and done.reason == "No longer selling"
    assert site.last("DestroyAd")["variables"] == {"id": gid("Ad", 5001), "reason": gid("DeleteReason", 6),
                                                    "source": "DESKTOP"}
    tap.ads.delete("5001", reason_id=4)
    assert site.last("DestroyAd")["variables"]["reason"] == gid("DeleteReason", 4)
    with pytest.raises(InvalidRequestError):
        tap.ads.delete("5001", reason_id=20)
    reasons = tap.ads.delete_reasons(5001)
    assert [r.legacy_id for r in reasons] == ["4", "6", "20"] and reasons[2].description_required


def test_get_list_all_prolong(tap, site):
    ad = tap.ads.get(5001)
    assert ad.status == AdStatus.APPROVED and ad.status.is_live and ad.price == 150000.0
    assert ad.thumbnail == "https://tap.azstatic.com/p/1.jpg" and ad.updated_at is not None
    with pytest.raises(NotFoundError):
        tap.ads.get(9999)
    page = tap.ads.list(AdTab.PUBLISHED, first=5)
    assert page.total == 1 and not page.has_more
    assert site.last("MyAds")["variables"] == {"status": "PUBLISHED", "first": 5, "after": None}
    tap.ads.create(635, "Flat", properties=SALE, price=10, photo_ids=["p"])
    assert [a.id for a in tap.ads.all(page_size=1)] == ["5001", "5002"]
    with pytest.raises(InvalidRequestError):
        tap.ads.list("deleted")
    assert tap.ads.prolong(5001) is True
    assert site.last("ProlongAds")["variables"] == {"ids": [gid("Ad", 5001)]}


def test_photos(tap, site, tmp_path):
    photo = tap.photos.upload(b"\xff\xd8jpeg", "flat.jpg")
    assert photo.id == "tap/2026/11/06/x.jpg" and photo.thumbnail_url.endswith("x.jpg")
    request = site.requests[-1]
    assert request.url.path == "/pond" and request.url.params["lang"] == "az"
    assert b'name="images[]"; filename="flat.jpg"' in request.content and b"image/jpeg" in request.content
    file = tmp_path / "room.png"
    file.write_bytes(b"\x89PNG")
    tap.photos.upload(file)
    assert b'filename="room.png"' in site.requests[-1].content and b"image/png" in site.requests[-1].content
    rotated = tap.photos.rotate(photo.id, 180)
    assert rotated.id == "tap/r.jpg" and site.requests[-1].url.params["angle"] == "180"
    with pytest.raises(InvalidRequestError):
        tap.photos.rotate(photo.id, 45)
    with pytest.raises(InvalidRequestError):
        tap.photos.upload(b"")
