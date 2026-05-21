from __future__ import annotations

import requests

from src.llm import openrouter_client


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._payload


def test_openrouter_call_uses_nvidia_model(monkeypatch):
    calls = []
    monkeypatch.setattr(openrouter_client, "_secret_from_streamlit", lambda: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_post(url, headers, json, timeout):
        calls.append(json["model"])
        assert headers["Authorization"] == "Bearer test-key"
        return FakeResponse(200, {"choices": [{"message": {"content": "{\"ok\": true}"}}]})

    monkeypatch.setattr(openrouter_client.requests, "post", fake_post)

    result = openrouter_client.call_openrouter([{"role": "user", "content": "test"}])

    assert result == "{\"ok\": true}"
    assert calls == [openrouter_client.DEFAULT_OPENROUTER_MODEL]


def test_openrouter_call_without_key_returns_none(monkeypatch):
    monkeypatch.setattr(openrouter_client, "_secret_from_streamlit", lambda: None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    assert openrouter_client.call_openrouter([{"role": "user", "content": "test"}]) is None
