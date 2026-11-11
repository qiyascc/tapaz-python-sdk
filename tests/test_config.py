from __future__ import annotations

import pytest

from tapaz_sdk import ConfigurationError, TapAz, messages


def test_environment(monkeypatch):
    monkeypatch.setenv("TAPAZ_COOKIE", "_tapaz_session=env; __cf_bm=x")
    monkeypatch.setenv("TAPAZ_MAX_RETRIES", "4")
    monkeypatch.setenv("TAPAZ_ENDPOINTS__PHOTO_UPLOAD", "/pond2")
    client = TapAz()
    assert client.cookie == "_tapaz_session=env" and client.settings.max_retries == 4
    assert client.settings.endpoints.photo_upload == "/pond2"
    assert "_tapaz_session" not in repr(client)


def test_config_file(tmp_path):
    path = tmp_path / "tapaz.toml"
    path.write_text('cookie = "_tapaz_session=file"\ntimeout = 12\ndefault_region = "421"\n')
    client = TapAz(config_file=str(path))
    assert client.signed_in and client.settings.timeout == 12 and client.settings.default_region == "421"


def test_plain_http_is_refused():
    with pytest.raises(ConfigurationError):
        TapAz(graphql_url="http://tap.example/graphql")
    assert TapAz(graphql_url="http://localhost:8000/graphql").settings.graphql_url.startswith("http://localhost")


def test_user_agent():
    assert TapAz().settings.resolved_user_agent().startswith("tapaz-python-sdk/")
    assert TapAz(user_agent="my-crm/1.0").settings.resolved_user_agent() == "my-crm/1.0"


def test_messages_can_be_replaced():
    try:
        messages.use({"error": {"session": "Login again"}})
        assert messages.text("error.session") == "Login again"
        with pytest.raises(KeyError):
            messages.use({"error": {"nope": "x"}})
    finally:
        messages.reset()
