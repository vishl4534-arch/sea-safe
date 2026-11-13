"""Voice mode, typed: /api/voice/text runs the same chat and reads the reviewed spoken answer (13 Nov 2026).
ElevenLabs and the model are fakes from tests/test_voice.py and tests/test_chat.py."""
from pathlib import Path

from app import llm
from app.config import ROOT
from tests.test_chat import scripted, tool_msg
from tests.test_voice import client, fake_eleven  # noqa: F401  (fixtures)


def test_typed_question_in_voice_mode_is_answered_aloud(fake_eleven, client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "assess_trip", place="gangolli", day="today", hour=11, minute=0, back_by_hour=-1, back_by_minute=0,
        back_day="same", trip_hours=6, trip_length_given_by_user=True)], []))
    r = client.post("/api/voice/text", json={"question": "Gangolli at 11 for 6 hours?", "region": "karnataka",
                                             "lang": "en", "mode": "karnataka_2025_05_20"}).json()
    assert r["ok"] and r["transcript"] == "Gangolli at 11 for 6 hours?"
    assert r["cards"][0]["result"]["verdict"] == "UNSAFE" and r["audio_url"].startswith("/api/voice/audio/")
    client.get(r["audio_url"])
    assert fake_eleven["tts"][0]["json"]["text"] == r["spoken"]          # the voice reads exactly the template


def test_voice_mode_greeting_is_spoken_too(fake_eleven, client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "Hi Vish! Where are you heading out from?"}], []))
    r = client.post("/api/voice/text", json={"question": "hi I'm Vish", "region": "karnataka", "lang": "en",
                                             "mode": "karnataka_2025_05_20"}).json()
    assert r["spoken"] == "Hi Vish! Where are you heading out from?" and r["cards"] == []


def test_voice_mode_text_is_checked(client):  # noqa: F811
    assert client.post("/api/voice/text", json={"question": "", "region": "karnataka"}).status_code == 422
    assert client.post("/api/voice/text", json={"question": "x" * 1001, "region": "karnataka"}).status_code == 422
    assert client.post("/api/voice/text", json={"question": "hi", "region": "karnataka",
                                                "history": [{"role": "system", "content": "x"}]}).status_code == 422


def test_voice_mode_keeps_noise_out_and_never_records_while_speaking():
    js = (Path(ROOT) / "static" / "voicemode.js").read_text(encoding="utf-8")
    assert "noiseSuppression: true" in js and "echoCancellation: true" in js
    assert 'band.type = "bandpass"' in js and "SPEECH_MS = 250" in js
    assert 'if (V.state === "speaking" && V.outAn)' in js            # while speaking, only her voice is measured
