"""Watch emails (owner, 13 Nov 2026): the fisher may type an email when they watch a trip. They get a confirmation
when watching starts and the same "now CAUTION" message by email when the verdict changes. A watch can run on
email alone (an iPhone without the Home Screen app gets no notifications). Sent through Gmail (SMTP, an app
password in .env). The email is kept only with the watch. No network: the verdict check, push and mail are fakes."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import mailer, service, watch
from app.config import ROOT
from tests.test_watch_server import SUB, TRIP


@pytest.fixture
def box(monkeypatch, tmp_path):
    monkeypatch.setattr(watch, "DIR", tmp_path)
    state = {"verdict": "SAFE", "pushed": [], "mailed": []}

    def fake_assess(region, place, dep, hours, given, mode="live", map_point=None):
        return {"ok": True, "verdict": state["verdict"], "place": {"id": place, "kind": "harbour"},
                "departure": dep, "trip_hours": hours}
    monkeypatch.setattr(service, "assess_trip", fake_assess)
    monkeypatch.setattr(watch, "send", lambda sub, payload: state["pushed"].append(payload))
    monkeypatch.setattr(mailer, "send", lambda to, subject, body: state["mailed"].append((to, subject, body)))
    monkeypatch.setattr(watch, "_in_background", lambda fn: fn())      # send at once in tests
    monkeypatch.setenv("SMTP_USER", "seasafe.sender@gmail.com")       # email is set up on this server
    monkeypatch.setenv("SMTP_PASSWORD", "test-app-password")
    return state


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_starting_a_watch_emails_a_confirmation(box, client):
    r = client.post("/api/watch", json={"subscription": SUB, "email": "fisher@example.com", **TRIP}).json()
    assert r["ok"] and r["email"] is True
    to, subject, body = box["mailed"][0]
    assert to == "fisher@example.com" and subject == "Sea Safe is watching your trip from Khor Fakkan"
    assert "SAFE" in body and "every 15 minutes" in body and "official warnings" in body


def test_a_change_is_emailed_as_well_as_pushed(box, client):
    client.post("/api/watch", json={"subscription": SUB, "email": "fisher@example.com", **TRIP})
    box["verdict"] = "CAUTION"
    watch.check_all()
    assert box["pushed"][0]["title"] == "Khor Fakkan: now CAUTION"
    assert box["mailed"][-1][1] == "Khor Fakkan: now CAUTION" and "was SAFE" in box["mailed"][-1][2]


def test_email_alone_is_enough(box, client):
    r = client.post("/api/watch", json={"email": "fisher@example.com", **TRIP}).json()
    assert r["ok"]
    box["verdict"] = "UNSAFE"
    watch.check_all()
    assert box["pushed"] == [] and box["mailed"][-1][1] == "Khor Fakkan: now UNSAFE"


def test_needs_a_phone_or_an_email(box, client):
    assert client.post("/api/watch", json=TRIP).status_code == 422


def test_a_bad_email_is_refused(box, client):
    for bad in ("not-an-email", "a@b", "x" * 250 + "@example.com", "a b@example.com"):
        assert client.post("/api/watch", json={"email": bad, **TRIP}).status_code == 422, bad


def test_no_email_set_up_says_so(box, client, monkeypatch):
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(mailer, "send", mailer.__dict__["_real_send"])  # the real sender: not set up
    r = client.post("/api/watch", json={"subscription": SUB, "email": "fisher@example.com", **TRIP}).json()
    assert r["ok"] and r["email"] is False                        # watching works; the page says email is off


def test_the_email_goes_when_the_watch_ends(box, client):
    r = client.post("/api/watch", json={"email": "fisher@example.com", **TRIP}).json()
    client.post("/api/watch/stop", json={"id": r["id"]})
    assert "fisher@example.com" not in (watch.DIR / "watches.json").read_text(encoding="utf-8")


def test_gmail_sender(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["server"] = (host, port)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, msg):
            sent["msg"] = msg
    monkeypatch.setenv("SMTP_USER", "seasafe.sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcd efgh ijkl mnop")
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTP)
    mailer._real_send("fisher@example.com", "Hello", "Body text")
    assert sent["server"] == ("smtp.gmail.com", 465) and sent["login"] == ("seasafe.sender@gmail.com", "abcdefghijklmnop")
    assert sent["msg"]["To"] == "fisher@example.com" and sent["msg"]["Subject"] == "Hello"
    assert "Sea Safe" in sent["msg"]["From"] and sent["msg"].get_content().strip() == "Body text"


def test_page_asks_for_the_email():
    js = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")
    assert 'id="watch-email"' in js and 'store.set("watch_email"' in js


def test_no_way_to_tell_the_fisher_is_refused(box, client, monkeypatch):
    """No phone notifications and email not set up: nobody could be told, so the watch is not started."""
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    r = client.post("/api/watch", json={"email": "fisher@example.com", **TRIP}).json()
    assert r == {"ok": False, "message": "Email isn't set up on this server and this browser can't get notifications, "
                                         "so this trip can't be watched here."}
    assert watch.all_watches() == []


def test_headline_names_the_way_the_fisher_is_told():
    from app import explain
    assert "notification" in explain.t("en", "watch.on") and "email" in explain.t("en", "watch.on_by_email")
    assert "notification and an email" in explain.t("en", "watch.on_both")
    js = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")
    assert '"watch.on_both"' in js and '"watch.on_by_email"' in js
