from __future__ import annotations

import httpx
import pytest

from tapaz_sdk import (
    AuthenticationError,
    BlockedError,
    GraphQLError,
    NotSentError,
    OutcomeUnknownError,
    TransportError,
)

from .conftest import SALE

CHALLENGE = httpx.Response(403, headers={"server": "cloudflare", "content-type": "text/html",
                                         "cf-mitigated": "challenge"}, text="<html>challenge</html>")


def test_reads_retry_then_give_up(guest, site):
    site.force(httpx.Response(502), httpx.ReadTimeout("slow"))
    assert guest.catalog.regions()[0].id == "420"
    site.force(*[httpx.ReadTimeout("slow")] * 3)
    with pytest.raises(TransportError):
        guest.catalog.regions()


def test_connection_failures_retry_because_nothing_was_sent(guest, site):
    site.force(httpx.ConnectError("refused"))
    assert guest.catalog.regions()
    site.force(*[httpx.ConnectError("refused")] * 3)
    with pytest.raises(NotSentError):
        guest.catalog.regions()


def test_create_is_never_resent(tap, site):
    for failure in (httpx.ReadTimeout("slow"), httpx.Response(502), httpx.Response(200, text="<html>")):
        site.requests.clear()
        site.force(lambda r: _pass(site, r), failure)
        with pytest.raises(OutcomeUnknownError):
            tap.ads.create(635, "Flat", properties=SALE, price=10, photo_ids=["p"], email="a@b.az",
                           phones=["+994501234567"])
        assert site.ops() == ["Category", "CreateAd"]


def _pass(site, request):
    return site.graphql(request)


def test_delete_is_never_resent(tap, site):
    site.force(lambda r: site.graphql(r), httpx.ReadTimeout("slow"))
    with pytest.raises(OutcomeUnknownError):
        tap.ads.delete(5001)
    assert site.ops().count("DestroyAd") == 1


def test_cloudflare_challenge_is_reported_not_solved(guest, site):
    site.force(CHALLENGE)
    with pytest.raises(BlockedError):
        guest.catalog.regions()
    assert len(site.requests) == 1


def test_graphql_errors(tap, site):
    site.force(httpx.Response(200, json={"errors": [{"message": "Field 'x' doesn't exist", "path": ["x"]}]}))
    with pytest.raises(GraphQLError) as bad:
        tap.catalog.regions()
    assert bad.value.errors[0]["path"] == ["x"]
    site.force(httpx.Response(401, json={}))
    with pytest.raises(AuthenticationError):
        tap.ads.list()


def test_session_cookie_never_leaves_tap_az(tap, site):
    tap.auth.send_code("0501234567")
    tap.photos.upload(b"x")
    hosts = {r.url.host: r.headers.get("cookie") for r in site.requests}
    assert hosts == {"api.digit-u.id": None, "photos.tap.az": "_tapaz_session=good"}


def test_client_cookie_jar_stays_empty(tap, site):
    site.force(lambda r: httpx.Response(200, json={"data": {"regions": []}},
                                        headers=[("set-cookie", "__cf_bm=x; path=/")]))
    tap.catalog.regions()
    assert not tap._http.cookies
    tap.catalog.regions()
    assert "__cf_bm" not in (site.requests[-1].headers.get("cookie") or "")


def test_raw_graphql(tap, site):
    data = tap.graphql("query Regions { regions(scope: ALL) { legacyResourceId name default } }",
                       operation="Regions", safe=True, auth=False)
    assert data["regions"][0]["name"] == "Baku"
