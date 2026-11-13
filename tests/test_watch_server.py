"""Watch this trip, on the server (owner, 13 Nov 2026): the trip is checked again every 15 minutes with the same
verdict code until departure, and a phone notification (Web Push) is sent only when the verdict changes. Works with
the page closed. Notifications go only to the browsers' own push services. No network: the verdict check and the
push sender are fakes."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import service, watch
from app.config import ROOT, load_app

SUB = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc123", "keys": {"p256dh": "BPk", "auth": "xyz"}}
TRIP = {"region": "uae", "place": "khor_fakkan", "departure_local": "2099-11-13T14:00", "trip_hours": 4,
        "trip_length_given_by_user": True, "lang": "en", "map_point": None}


@pytest.fixture
def box(monkeypatch, tmp_path):
    """A fresh watch store and key folder, a fake verdict check and a fake push sender."""
    monkeypatch.setattr(watch, "DIR", tmp_path)
    state = {"verdict": "SAFE", "ok": True, "sent": [], "gone": False}

    def fake_assess(region, place, dep, hours, given, mode="live", map_point=None):
        if not state["ok"]:
            return {"ok": False, "error": "past_time"}
        return {"ok": True, "verdict": state["verdict"], "place": {"id": place, "kind": "harbour"},
                "departure": dep, "trip_hours": hours}

    def fake_send(sub, payload):
        if state["gone"]:
            raise watch.Gone("410")
        state["sent"].append((sub["endpoint"], payload))
    monkeypatch.setattr(service, "assess_trip", fake_assess)
    monkeypatch.setattr(watch, "send", fake_send)
    return state


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_public_key_is_made_once_and_kept(box, client):
    k1 = client.get("/api/push/key").json()
    k2 = client.get("/api/push/key").json()
    assert k1["ok"] and k1["key"] == k2["key"] and len(k1["key"]) > 80      # an uncompressed P-256 point, base64url


def test_start_and_stop_a_watch(box, client):
    r = client.post("/api/watch", json={"subscription": SUB, **TRIP}).json()
    assert r["ok"] and r["verdict"] == "SAFE" and r["id"]
    assert len(watch.all_watches()) == 1
    assert client.post("/api/watch/stop", json={"id": r["id"]}).json() == {"ok": True}
    assert watch.all_watches() == []


def test_only_the_browsers_push_services(box, client):
    bad = {**SUB, "endpoint": "http://169.254.169.254/latest/meta-data"}
    assert client.post("/api/watch", json={"subscription": bad, **TRIP}).status_code == 422
    for ok in ("https://fcm.googleapis.com/fcm/send/x", "https://updates.push.services.mozilla.com/wpush/v2/x",
               "https://web.push.apple.com/x", "https://db5p.notify.windows.com/w/?token=x"):
        assert watch.allowed_endpoint(ok), ok
    for bad in ("https://evil.example.com/x", "http://fcm.googleapis.com/x", "https://fcm.googleapis.com.evil.com/x"):
        assert not watch.allowed_endpoint(bad), bad


def test_a_trip_that_cannot_be_checked_is_not_watched(box, client):
    box["ok"] = False
    assert client.post("/api/watch", json={"subscription": SUB, **TRIP}).json()["ok"] is False
    assert watch.all_watches() == []


def test_no_notification_while_nothing_changes(box, client):
    client.post("/api/watch", json={"subscription": SUB, **TRIP})
    watch.check_all()
    assert box["sent"] == []


def test_a_change_sends_one_notification(box, client):
    client.post("/api/watch", json={"subscription": SUB, **TRIP})
    box["verdict"] = "CAUTION"
    watch.check_all()
    watch.check_all()                                         # the same change is not sent twice
    assert len(box["sent"]) == 1
    endpoint, payload = box["sent"][0]
    assert endpoint == SUB["endpoint"]
    assert payload["title"] == "Khor Fakkan: now CAUTION"
    assert "was SAFE" in payload["body"] and payload["url"] == "/"


def test_watching_ends_at_departure(box, client):
    client.post("/api/watch", json={"subscription": SUB, **{**TRIP, "departure_local": "2000-01-01T06:00"}})
    box["ok"] = True
    watch.check_all()
    assert watch.all_watches() == [] and box["sent"] == []


def test_a_phone_that_unsubscribed_is_forgotten(box, client):
    client.post("/api/watch", json={"subscription": SUB, **TRIP})
    box["verdict"], box["gone"] = "UNSAFE", True
    watch.check_all()
    assert watch.all_watches() == []


def test_checks_every_15_minutes_and_has_a_limit():
    cfg = load_app()["watch"]
    assert cfg["check_minutes"] == 15 and cfg["max_watches"] >= 1


def test_page_and_service_worker_handle_notifications():
    sw = (Path(ROOT) / "static" / "sw.js").read_text(encoding="utf-8")
    assert 'addEventListener("push"' in sw and 'addEventListener("notificationclick"' in sw
    assert "pywebpush" in (Path(ROOT) / "requirements.txt").read_text(encoding="utf-8")


def _subscriber_keys():
    """A real browser-style subscription key pair (P-256 point + 16-byte auth secret), base64url."""
    import base64
    import os

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    pub = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    enc = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()  # noqa: E731
    return {"p256dh": enc(pub), "auth": enc(os.urandom(16))}


def test_real_sender_signs_and_encrypts_and_spots_unsubscribed(monkeypatch, tmp_path):
    """The real send(), with real encryption; only the network call is faked."""
    import pywebpush
    monkeypatch.setattr(watch, "DIR", tmp_path)
    seen = []

    class Resp:
        def __init__(self, code):
            self.status_code, self.text, self.headers, self.reason = code, "", {}, "Gone" if code == 410 else "Created"

    status = {"code": 201}

    def fake_post(url, data=None, headers=None, timeout=None, **kw):
        seen.append((url, headers, data))
        return Resp(status["code"])
    monkeypatch.setattr(pywebpush.requests, "post", fake_post)
    sub = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": _subscriber_keys()}
    watch.send(sub, {"title": "Khor Fakkan: now CAUTION", "body": "x", "url": "/"})
    url, headers, data = seen[0]
    assert url == sub["endpoint"] and headers["content-encoding"] == "aes128gcm"
    assert headers["authorization"].startswith("vapid t=") and b"CAUTION" not in data     # signed and encrypted
    status["code"] = 410
    with pytest.raises(watch.Gone):
        watch.send(sub, {"title": "t", "body": "b", "url": "/"})
