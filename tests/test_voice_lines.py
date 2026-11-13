"""Lines she says without waiting for an answer (13 Nov 2026, owner chose them; idea from the Jessa voice agent):
a greeting when voice mode opens, an instant "Okay." / "Right." when the fisher stops talking, and "One moment."
if the answer takes longer. Fixed text, so each is rendered once and then served from the cache."""
from pathlib import Path

import pytest

from app import explain
from app.config import ROOT
from tests.test_voice import client, fake_eleven  # noqa: F401  (fixtures)

KEYS = ["say.greeting", "say.ack.0", "say.ack.1", "say.wait"]


def test_english_lines_are_the_approved_words():
    assert explain.t("en", "say.greeting") == "Hi, I'm the Sea Safe assistant. Where are you heading out today?"
    assert [explain.t("en", k) for k in ("say.ack.0", "say.ack.1", "say.wait")] == ["Okay.", "Right.", "One moment."]


@pytest.mark.parametrize("lang", ["kn", "ar"])
def test_every_language_has_the_lines(lang):
    for k in KEYS:
        assert explain.t(lang, k) not in (k, explain.t("en", k))


def test_lines_endpoint_gives_text_and_audio(fake_eleven, client):  # noqa: F811
    r = client.get("/api/voice/lines", params={"lang": "en"}).json()
    assert r["ok"]
    assert r["greeting"]["text"] == explain.t("en", "say.greeting")
    assert [a["text"] for a in r["acks"]] == ["Okay.", "Right."] and r["wait"]["text"] == "One moment."
    urls = [r["greeting"]["url"], r["wait"]["url"], *[a["url"] for a in r["acks"]]]
    assert all(u.startswith("/api/voice/audio/") for u in urls) and len(set(urls)) == 4
    assert client.get(r["greeting"]["url"]).status_code == 200
    assert explain.t("en", "say.greeting") in [c["json"]["text"] for c in fake_eleven["tts"]]


def test_lines_endpoint_refuses_a_language_without_a_voice(fake_eleven, client):  # noqa: F811
    assert client.get("/api/voice/lines", params={"lang": "xx"}).json() == {"ok": False}


def test_page_greets_and_fills_the_gap():
    js = (Path(ROOT) / "static" / "voicemode.js").read_text(encoding="utf-8")
    assert "/api/voice/lines" in js
    assert "WAIT_MS = 1500" in js                      # "One moment." only if the answer is not back by then
    assert "V.ackNext" in js                           # "Okay." and "Right." take turns: never the same twice running
