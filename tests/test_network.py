from __future__ import annotations

from utils import network


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload


class DummySession:
    def close(self):
        return None


def test_get_paper_like_versions_collects_latest_builds(monkeypatch):
    def fake_session():
        return DummySession()

    def fake_request(_session, _method, url, logger=None, **kwargs):
        if url.endswith("/projects/paper"):
            return DummyResponse({"versions": ["1.20.5", "1.20.6"]})
        if url.endswith("/versions/1.20.6/builds"):
            return DummyResponse(
                {
                    "builds": [
                        {"build": 21, "downloads": {"application": {"name": "paper-1.20.6-21.jar"}}}
                    ]
                }
            )
        if url.endswith("/versions/1.20.5/builds"):
            return DummyResponse(
                {
                    "builds": [
                        {"build": 17, "downloads": {"application": {"name": "paper-1.20.5-17.jar"}}}
                    ]
                }
            )
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(network, "create_robust_session", fake_session)
    monkeypatch.setattr(network, "safe_request", fake_request)

    versions = network.get_paper_like_versions("paper")

    assert list(versions) == ["1.20.6", "1.20.5"]
    assert versions["1.20.6"]["latest_build"] == 21
    assert versions["1.20.5"]["download_name"] == "paper-1.20.5-17.jar"


def test_get_vanilla_versions_filters_snapshots(monkeypatch):
    def fake_session():
        return DummySession()

    def fake_request(_session, _method, url, logger=None, **kwargs):
        assert url == network.SERVER_FLAVORS["vanilla"]["api_base"]
        return DummyResponse(
            {
                "versions": [
                    {"id": "1.20.6", "type": "release", "url": "https://example/release.json"},
                    {"id": "24w14a", "type": "snapshot", "url": "https://example/snapshot.json"},
                ]
            }
        )

    monkeypatch.setattr(network, "create_robust_session", fake_session)
    monkeypatch.setattr(network, "safe_request", fake_request)

    versions = network.get_vanilla_versions("vanilla")

    assert list(versions) == ["1.20.6"]
    assert versions["1.20.6"]["url"] == "https://example/release.json"
