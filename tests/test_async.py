from __future__ import annotations

import httpx
import pytest

from tapaz_sdk import OutcomeUnknownError

from .conftest import SALE


async def test_async_create_and_list(atap, site):
    ad = await atap.ads.create(635, "Flat", properties=SALE, price=10, photo_ids=["p"])
    assert ad.id == "5002"
    page = await atap.ads.list()
    assert page.total == 2


async def test_async_login(site):
    from tapaz_sdk import AsyncTapAz

    from .conftest import _quiet

    client = _quiet(AsyncTapAz(http_client=httpx.AsyncClient(transport=httpx.MockTransport(site))))
    sent = await client.auth.send_code("050 123 45 67")
    assert sent.code_requests_left == 2
    login = await client.auth.verify("050 123 45 67", "1234")
    assert login.user.name == "Qiyas" and client.signed_in


async def test_async_destroy_is_not_resent(atap, site):
    site.force(lambda r: site.graphql(r), httpx.ReadTimeout("slow"))
    with pytest.raises(OutcomeUnknownError):
        await atap.ads.delete(5001)


async def test_async_context_manager():
    from tapaz_sdk import AsyncTapAz

    async with AsyncTapAz() as client:
        assert client.settings.graphql_url == "https://tap.az/graphql"
