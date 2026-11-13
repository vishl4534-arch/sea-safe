"""Talking over her (owner, 13 Nov 2026; layered like the Jessa voice agent's barge-in): while she speaks, the
page keeps listening; clear speech stops her and is recorded. The server then decides: no words, or only her
own words heard back through the speaker, means it was noise and she carries on ("resume"); real words are a
new question, answered as usual. ElevenLabs and the model are fakes."""
from pathlib import Path

from app import llm, voice
from app.config import ROOT
from tests.test_voice import client, fake_eleven, tool_call  # noqa: F401  (fixtures)

LINE = "Alright, leaving from Gangolli on Tuesday at 11 in the morning: that's unsafe. Waves up to 2 metres."


def post(client, interrupted=LINE):  # noqa: F811
    return client.post("/api/voice/ask", files={"audio": ("q.webm", b"audio", "audio/webm")},
                       data={"region": "karnataka", "lang": "en", "mode": "karnataka_2025_05_20",
                             "interrupted": interrupted}).json()


def test_no_words_means_noise_and_she_carries_on(fake_eleven, client, monkeypatch):  # noqa: F811
    fake_eleven["transcript"] = ""
    monkeypatch.setattr(llm, "complete", lambda *a: (_ for _ in ()).throw(AssertionError("no model call")))
    assert post(client) == {"ok": True, "resume": True}
    assert fake_eleven["tts"] == []                          # nothing new is said


def test_her_own_words_heard_back_mean_noise(fake_eleven, client, monkeypatch):  # noqa: F811
    fake_eleven["transcript"] = "leaving from Gangolli on Tuesday"
    monkeypatch.setattr(llm, "complete", lambda *a: (_ for _ in ()).throw(AssertionError("no model call")))
    assert post(client) == {"ok": True, "resume": True}


def test_real_words_are_a_new_question(fake_eleven, client, monkeypatch):  # noqa: F811
    fake_eleven["transcript"] = "wait, what about Malpe tomorrow?"
    monkeypatch.setattr(llm, "complete", lambda messages, tools: (
        {"role": "assistant", "content": "Sure, when will you leave from Malpe?"}, "fake (test)"))
    r = post(client)
    assert r["ok"] and not r.get("resume") and r["transcript"] == "wait, what about Malpe tomorrow?"


def test_without_an_interruption_silence_still_says_not_heard(fake_eleven, client):  # noqa: F811
    fake_eleven["transcript"] = ""
    r = post(client, interrupted="")
    assert r["ok"] and not r.get("resume") and r["spoken"]


def test_echo_check():
    assert voice.is_echo("", LINE) and voice.is_echo("Gangolli on Tuesday at 11", LINE)
    assert not voice.is_echo("stop, what about tomorrow?", LINE)


def test_page_listens_while_she_speaks():
    js = (Path(ROOT) / "static" / "voicemode.js").read_text(encoding="utf-8")
    assert "BARGE_MS" in js and "function interrupt(" in js and "function resumeSpeech(" in js
    assert 'fd.append("interrupted"' in js
