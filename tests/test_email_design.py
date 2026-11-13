"""Watch emails look like Sea Safe (owner, 13 Nov 2026): an HTML email with the logo and wordmark, the verdict as
a coloured badge, the trip in rows, the disclaimer apart; plain text stays inside for mail apps without HTML.
A 512 px square logo is made for a sender account's profile picture."""
import struct
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import emails, mailer, service, watch
from app.config import ROOT
from tests.test_watch_server import SUB, TRIP


@pytest.fixture
def box(monkeypatch, tmp_path):
    monkeypatch.setattr(watch, "DIR", tmp_path)
    state = {"verdict": "SAFE", "mailed": []}

    def fake_assess(region, place, dep, hours, given, mode="live", map_point=None):
        return {"ok": True, "verdict": state["verdict"], "place": {"id": place, "kind": "harbour"},
                "departure": dep, "trip_hours": hours}
    monkeypatch.setattr(service, "assess_trip", fake_assess)
    monkeypatch.setattr(watch, "send", lambda sub, payload: None)
    monkeypatch.setattr(mailer, "send", lambda to, subject, body, html=None: state["mailed"].append((subject, body, html)))
    monkeypatch.setattr(watch, "_in_background", lambda fn: fn())
    monkeypatch.setenv("SMTP_USER", "seasafe.sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test-app-password")
    return state


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_confirmation_is_a_designed_email_with_text_inside(box, client):
    client.post("/api/watch", json={"subscription": SUB, "email": "fisher@example.com", **TRIP})
    subject, text, html = box["mailed"][0]
    assert "Sea Safe is watching your trip" in text                      # plain text for any mail app
    assert 'src="cid:seasafe-logo"' in html and "SEA SAFE" in html          # the logo and wordmark
    assert "Khor Fakkan" in html and "#1d7f47" in html and ">SAFE<" in html  # the place, the SAFE badge
    assert "Every 15 minutes until you leave" in html and "official warnings" in html


def test_change_email_shows_old_and_new_verdict(box, client):
    client.post("/api/watch", json={"email": "fisher@example.com", **TRIP})
    box["verdict"] = "CAUTION"
    watch.check_all()
    subject, text, html = box["mailed"][-1]
    assert subject == "Khor Fakkan: now CAUTION" and "was SAFE" in text
    assert ">SAFE<" in html and ">CAUTION<" in html and "#e2a400" in html


def test_arabic_email_reads_right_to_left():
    html = emails.html("ar", kicker="x", heading="دبا", badges=["SAFE"], rows=[("a", "b")], lead="c", note="d", footer="e")
    assert 'dir="rtl"' in html and 'lang="ar"' in html


def test_text_from_the_trip_is_escaped():
    html = emails.html("en", kicker="<b>", heading="<script>x</script>", badges=["SAFE"], rows=[], lead="", note="", footer="")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_real_sender_sends_html_with_the_logo_inside(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def login(self, user, password):
            pass

        def send_message(self, msg):
            sent["msg"] = msg
    monkeypatch.setenv("SMTP_USER", "seasafe.sender@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abcdabcdabcdabcd")
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTP)
    mailer._real_send("fisher@example.com", "Hello", "Plain body", html='<img src="cid:seasafe-logo">')
    parts = {p.get_content_type(): p for p in sent["msg"].walk()}
    assert "text/plain" in parts and "text/html" in parts and "image/png" in parts
    assert parts["image/png"]["Content-ID"] == "<seasafe-logo>"


def test_profile_picture_is_a_512_square_png():
    data = (Path(ROOT) / "brand" / "sea-safe-profile-512.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (512, 512)
