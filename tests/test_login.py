from __future__ import annotations

import base64
import json

import httpx
import pytest

from tapaz_sdk import (
    AuthenticationError,
    BadRequestError,
    InvalidCodeError,
    InvalidRequestError,
    MutationError,
    OutcomeUnknownError,
    RateLimitError,
    ServerError,
    SessionRequiredError,
)

from .conftest import SESSION


def test_send_code_normalises_the_phone(guest, site):
    sent = guest.auth.send_code("+994 50 123 45 67")
    assert sent.phone == "0501234567" and sent.code_requests_left == 2 and not sent.retried
    request = site.requests[0]
    assert request.url == "https://api.digit-u.id/auth"
    assert json.loads(request.content) == {"phone": "0501234567"}
    assert "cookie" not in request.headers
    assert request.headers["user-agent"].startswith("tapaz-python-sdk/")


def test_bad_numbers_are_refused_before_sending(guest, site):
    for phone in ("012 345 67 89", "12345", ""):
        with pytest.raises(InvalidRequestError):
            guest.auth.send_code(phone)
    assert site.requests == []


def test_verify_signs_in_and_keeps_only_the_session_cookie(guest, site):
    login = guest.auth.verify("050 123 45 67", "1234")
    assert login.user.id == "77" and login.user.email == "q@tap.test"
    assert login.cookie == SESSION and guest.cookie == SESSION and guest.signed_in
    verify = json.loads(site.requests[0].content)
    assert verify["phone"] == "0501234567" and base64.b64decode(verify["return_to"]) == b"https://tap.az/"
    assert site.last("LoginUser")["variables"] == {"accessToken": "digitu-token"}
    assert site.ops() == ["api.digit-u.id/auth/verify", "LoginUser", "CurrentUser"]
    assert "__cf_bm" not in guest.cookie
    assert "__cf_bm" not in site.requests[-1].headers.get("cookie", "")


def test_limits_and_wrong_codes(guest, site):
    with pytest.raises(RateLimitError):
        guest.auth.send_code("099 111 22 33")
    with pytest.raises(InvalidCodeError) as wrong:
        guest.auth.verify("0501234567", "0000")
    assert "earlier attempt" not in str(wrong.value)
    site.force(httpx.Response(422, json={"error": "phone", "message": "Unknown number"}))
    with pytest.raises(BadRequestError):
        guest.auth.send_code("0501234567")


def test_answers_without_a_known_error_are_retried(guest, site):
    site.force(httpx.Response(403, text="<html>busy</html>"), httpx.Response(401, json={"message": "x"}))
    sent = guest.auth.send_code("0501234567")
    assert sent.retried and "latest code" in str(sent.note)
    assert len(site.requests) == 3


def test_login_service_gives_up(guest, site):
    site.force(*[httpx.Response(500)] * 3)
    with pytest.raises(ServerError) as failed:
        guest.auth.send_code("0501234567")
    assert "3 attempts" in str(failed.value) and len(site.requests) == 3


def test_a_code_refused_after_a_retry_may_be_used(guest, site):
    site.force(httpx.Response(400, text=""))
    with pytest.raises(InvalidCodeError) as wrong:
        guest.auth.verify("0501234567", "0000")
    assert "earlier attempt" in str(wrong.value)


def test_a_timeout_on_send_is_not_repeated(guest, site):
    site.force(httpx.ReadTimeout("slow"))
    with pytest.raises(OutcomeUnknownError) as unknown:
        guest.auth.send_code("0501234567")
    assert "SMS" in str(unknown.value) and len(site.requests) == 1


def test_login_user_is_not_repeated(guest, site):
    site.force(lambda r: httpx.Response(200, json={"access_token": "digitu-token"}), httpx.Response(502))
    with pytest.raises(OutcomeUnknownError):
        guest.auth.verify("0501234567", "1234")
    assert site.ops() == ["api.digit-u.id/auth/verify", "LoginUser"]


def test_refused_login_token(guest, site):
    site.force(lambda r: httpx.Response(200, json={"access_token": "other"}))
    with pytest.raises(MutationError):
        guest.auth.verify("0501234567", "1234")
    assert not guest.signed_in


def test_session_import_export_and_expiry(tap, guest, site):
    assert tap.me().name == "Qiyas"
    tap.use_cookie("Cookie: _tapaz_session=old; cf_clearance=x; __cf_bm=y")
    assert tap.cookie == "_tapaz_session=old"
    with pytest.raises(AuthenticationError):
        tap.me()
    with pytest.raises(SessionRequiredError):
        guest.me()


def test_rotated_session_cookie_is_kept(tap, site):
    site.force(lambda r: httpx.Response(200, json={"data": {"regions": []}},
                                        headers=[("set-cookie", "_tapaz_session=new; path=/"),
                                                 ("set-cookie", "tracking=1; path=/"),
                                                 ("set-cookie", "cf_clearance=z; path=/")]))
    tap.catalog.regions()
    assert tap.cookie == "_tapaz_session=new"
