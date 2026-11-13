"""Voice: ElevenLabs speech-to-text and text-to-speech, with a fake ElevenLabs (no key, no network).
The voice only reads reviewed spoken templates; it never decides anything."""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import explain, llm, service, voice, weather
from app.config import load_app

MP3 = b"ID3fake-mp3-bytes"


class Resp:
    def __init__(self, code, body=None, content=b""):
        self.status_code, self._body, self.content = code, body, content
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        return self._body


@pytest.fixture
def fake_eleven(monkeypatch, tmp_path):
    """A fake ElevenLabs that records every call."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(voice, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(weather, "fetch_points", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))
    calls = {"stt": [], "tts": [], "transcript": "Is it safe to leave from Gangolli at 11?", "tts_status": 200}

    def fake_post(url, **kw):
        if url.endswith("/speech-to-text"):
            calls["stt"].append(kw)
            return Resp(200, {"text": calls["transcript"]})
        calls["tts"].append({"url": url, **kw})
        return Resp(calls["tts_status"], {"detail": "x"} if calls["tts_status"] != 200 else None, MP3)

    class FakeStream:                                  # ElevenLabs streaming text-to-speech
        def __init__(self, url, kw):
            self.status_code = calls["tts_status"]
            calls["tts"].append({"url": url, **kw})

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"detail": "x"}'

        def iter_bytes(self):
            yield MP3[:5]
            yield MP3[5:]

    monkeypatch.setattr(voice, "_http", SimpleNamespace(
        post=fake_post, stream=lambda method, url, **kw: FakeStream(url, kw)))
    monkeypatch.setattr(voice, "_pending", {})
    monkeypatch.setattr(voice, "_fetches", {})
    return calls


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ---- availability -------------------------------------------------------------------
def test_voice_off_without_a_key(monkeypatch, client):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert client.get("/api/voice/status").json()["available"] is False
    r = client.post("/api/voice/ask", files={"audio": ("q.webm", b"x", "audio/webm")}, data={"region": "karnataka"})
    assert r.json() == {"ok": False, "message": explain.t("en", "voice.unavailable")}


def test_every_enabled_language_has_a_voice():
    v = load_app()["voice"]["languages"]
    for lang in load_app()["languages"]:
        assert lang in v and v[lang]["voice_id"] and v[lang]["stt"] and v[lang]["tts"]


# ---- speech-to-text -------------------------------------------------------------------
def test_transcribe_uses_scribe_and_the_screen_language(fake_eleven):
    text = voice.transcribe(b"audio", "q.webm", "audio/webm", "kn")
    assert text == fake_eleven["transcript"]
    sent = fake_eleven["stt"][0]
    assert sent["data"] == {"model_id": load_app()["voice"]["stt_model"], "language_code": "kan",
                            "tag_audio_events": "false"}          # background sounds are not words
    assert sent["headers"]["xi-api-key"] == "test-key"


# ---- text-to-speech -------------------------------------------------------------------
def test_synthesize_uses_the_language_voice_and_caches(fake_eleven):
    aid = voice.synthesize("Gangolli: UNSAFE.", "ar")
    assert voice.audio_path(aid).read_bytes() == MP3
    sent = fake_eleven["tts"][0]
    assert sent["url"].endswith("/" + load_app()["voice"]["languages"]["ar"]["voice_id"])
    assert sent["json"]["language_code"] == "ar" and sent["json"]["model_id"] == load_app()["voice"]["tts_model"]
    voice.synthesize("Gangolli: UNSAFE.", "ar")          # same text again: no second paid call
    assert len(fake_eleven["tts"]) == 1


def test_overlong_text_is_never_sent(fake_eleven):
    with pytest.raises(voice.VoiceError):
        voice.synthesize("x" * 5000, "en")
    assert fake_eleven["tts"] == []


@pytest.mark.parametrize("aid", ["../../.env", "abc", "0" * 23, "g" * 24])
def test_audio_ids_cannot_reach_other_files(aid):
    assert voice.audio_path(aid) is None


# ---- what is spoken -------------------------------------------------------------------
@pytest.mark.parametrize("lang", ["en", "kn"])
def test_spoken_answer_is_templated_and_complete(fake_eleven, lang):
    r = service.assess_trip("karnataka", "gangolli", "2025-05-20T11:00", 6, False, "karnataka_2025_05_20")
    said = explain.spoken(r, lang)
    assert "{" not in said and "km/h" not in said and "ಕಿಮೀ/ಗಂ" not in said     # units spoken as words
    assert explain.t(lang, "say.advice.UNSAFE") in said                         # verdict from code
    assert explain.t(lang, "say.verdict_line.UNSAFE").split("}")[-1].strip(" :,") in said
    assert explain.t(lang, "say.disclaimer") in said                            # forecast, not a guarantee
    assert explain.t(lang, "say.trip_assumed", hours=6) in said                  # assumed trip length
    assert len(said) < load_app()["voice"]["max_spoken_chars"]


def test_spoken_safe_answer_in_arabic(fake_eleven):
    r = service.assess_trip("uae", "dibba_al_hisn", "2025-02-25T05:00", 6, True, "uae_2025_02_25")
    said = explain.spoken(r, "ar")
    assert "آمن" in said and "كم/س" not in said
    assert "مدتها" not in said                       # a trip length the user gave is not read back


# ---- the endpoints ---------------------------------------------------------------------
def tool_call(name, **args):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_voice_ask_end_to_end(fake_eleven, client, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda messages, tools: (tool_call(
        "assess_trip", place="gangolli", day="today", hour=11, trip_hours=6,
        trip_length_given_by_user=True), "fake"))
    r = client.post("/api/voice/ask", files={"audio": ("q.webm", b"audio", "audio/webm")},
                    data={"region": "karnataka", "lang": "en", "mode": "karnataka_2025_05_20"}).json()
    assert r["ok"] and r["transcript"] == fake_eleven["transcript"]
    assert r["cards"][0]["result"]["verdict"] == "UNSAFE"
    assert "leaving from Gangolli on Tuesday at 11 in the morning: that's unsafe." in r["spoken"]
    audio = client.get(r["audio_url"])          # fetched by the server as soon as the answer was known, streamed
    assert audio.status_code == 200 and audio.content == MP3 and audio.headers["content-type"] == "audio/mpeg"
    assert len(fake_eleven["tts"]) == 1 and fake_eleven["tts"][0]["url"].endswith("/stream")
    assert fake_eleven["tts"][0]["json"]["text"] == r["spoken"]      # the voice reads exactly the template
    again = client.get(r["audio_url"])                                # second play: from the cache, no new call
    assert again.content == MP3 and len(fake_eleven["tts"]) == 1


def test_voice_ask_with_silence_says_not_heard(fake_eleven, client):
    fake_eleven["transcript"] = ""
    r = client.post("/api/voice/ask", files={"audio": ("q.webm", b"audio", "audio/webm")},
                    data={"region": "uae", "lang": "ar"}).json()
    assert r["ok"] and r["spoken"] == explain.t("ar", "say.not_heard") and r["audio_url"]


def test_voice_failure_keeps_the_written_answer(fake_eleven, client, monkeypatch):
    fake_eleven["tts_status"] = 500
    monkeypatch.setattr(llm, "complete", lambda messages, tools: (tool_call(
        "assess_trip", place="gangolli", day="today", hour=11, trip_hours=6,
        trip_length_given_by_user=True), "fake"))
    r = client.post("/api/voice/ask", files={"audio": ("q.webm", b"audio", "audio/webm")},
                    data={"region": "karnataka", "lang": "en", "mode": "karnataka_2025_05_20"}).json()
    assert r["ok"] and "Gangolli: UNSAFE" in r["reply"]               # the written answer is complete
    audio = client.get(r["audio_url"])
    assert audio.status_code == 502                                    # the page then shows "voice not working"
    assert not list(voice.AUDIO_DIR.glob("*.part"))                    # no half file left behind


def test_unknown_audio_id_is_404(fake_eleven, client):
    assert client.get("/api/voice/audio/" + "a" * 24).status_code == 404
    assert client.get("/api/voice/audio/..%2F..%2F.env").status_code == 404


def test_listen_button_recomputes_the_answer(fake_eleven, client):
    r = client.post("/api/voice/say", json={"region": "karnataka", "place": "gangolli",
                                            "departure_local": "2025-05-20T11:00", "trip_hours": 6,
                                            "trip_length_given_by_user": False, "mode": "karnataka_2025_05_20",
                                            "lang": "kn"}).json()
    assert r["ok"] and explain.t("kn", "verdict.UNSAFE") in r["spoken"]
    client.get(r["audio_url"])
    assert fake_eleven["tts"][0]["json"]["language_code"] == "kn"


# ---- times are spoken the way people say them, never "09:00" ------------------------------
import re  # noqa: E402

CLOCK = re.compile(r"\d{1,2}:\d{2}")


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_spoken_answers_never_contain_clock_digits(fake_eleven, lang):
    for args in [("karnataka", "gangolli", "2025-05-20T11:00", 6, False, "karnataka_2025_05_20"),
                 ("karnataka", "malpe", "2025-05-20T22:00", 8, True, "karnataka_2025_05_20")]:
        said = explain.spoken(service.assess_trip(*args), lang)
        assert not CLOCK.search(said), said
    s = service.find_safest_time("karnataka", "gangolli", "2025-05-20T04:00", "2025-05-20T23:00", 6, False,
                                 "karnataka_2025_05_20")
    assert not CLOCK.search(explain.safest_spoken(s, lang))


@pytest.mark.parametrize("hour,en,kn,ar", [
    (0, "at midnight", "ಮಧ್ಯರಾತ್ರಿ 12 ಗಂಟೆಗೆ", "منتصف الليل"),
    (4, "at 4 in the early morning", "ಬೆಳಗಿನ ಜಾವ 4 ಗಂಟೆಗೆ", "الساعة 4 فجراً"),
    (9, "at 9 in the morning", "ಬೆಳಿಗ್ಗೆ 9 ಗಂಟೆಗೆ", "الساعة 9 صباحاً"),
    (12, "at noon", "ಮಧ್ಯಾಹ್ನ 12 ಗಂಟೆಗೆ", "الساعة 12 ظهراً"),
    (14, "at 2 in the afternoon", "ಮಧ್ಯಾಹ್ನ 2 ಗಂಟೆಗೆ", "الساعة 2 بعد الظهر"),
    (17, "at 5 in the evening", "ಸಂಜೆ 5 ಗಂಟೆಗೆ", "الساعة 5 مساءً"),
    (21, "at 9 at night", "ರಾತ್ರಿ 9 ಗಂಟೆಗೆ", "الساعة 9 ليلاً"),
])
def test_spoken_time_words(hour, en, kn, ar):
    ts = f"2026-11-13T{hour:02d}:00"
    assert (explain.say_time("en", ts), explain.say_time("kn", ts), explain.say_time("ar", ts)) == (en, kn, ar)


def test_trip_past_midnight_names_the_next_day(fake_eleven):
    said = explain.spoken(service.assess_trip("karnataka", "malpe", "2025-05-20T22:00", 8, True,
                                              "karnataka_2025_05_20"), "en")
    assert "leaving from Malpe on Tuesday at 10 at night" in said
    assert "You'd be back on Wednesday around 6 in the morning." in said


# ---- shorter spoken answers (12 Nov 2026) ----------------------------------------------------------
@pytest.mark.parametrize("field,value,said", [
    ("wave_height", 2.16, "2.2"), ("wave_height", 0.5, "0.5"), ("wind_gusts", 39.2, "39"), ("wind_gusts", 23.0, "23"),
    ("wave_height", 1.96, "1.96"),      # 2.0 would be UNSAFE: the exact value is said
    ("wind_gusts", 39.6, "39.6"),       # 40 would be over the caution line
    ("wind_gusts", 35.96, "35.96"),     # 36 would be inside the near-line margin
    ("visibility", 1852.4, "1852.4"),   # 1852 would be at the caution line (lower is worse)
    ("visibility", 380.0, "380"),
])
def test_spoken_numbers_are_rounded_but_never_cross_a_line(field, value, said):
    assert explain.say_num(field, value) == said


@pytest.mark.parametrize("lang", ["en", "kn"])
def test_short_spoken_answer_keeps_every_reason_and_drops_the_thresholds(lang):
    r = service.assess_trip("karnataka", "gangolli", "2025-05-20T14:00", 7, True, "karnataka_2025_05_20")
    said = explain.spoken(r, lang)
    for reason in r["reasons"]:
        assert explain.t(lang, f"say.param.{reason['param']}") in said              # one line per parameter
    assert "1852" not in said and explain.t(lang, "say.advice.UNSAFE") in said      # threshold stays on the card
    assert explain.t(lang, "say.disclaimer") in said and len(said) < 450


# ---- conversational style (13 Nov 2026) ----------------------------------------------------------
@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_openers_are_chosen_by_code_and_repeat_for_the_same_question(lang):
    region, mode = ("uae", "uae_2025_02_25") if lang == "ar" else ("karnataka", "karnataka_2025_05_20")
    place = "khor_fakkan" if lang == "ar" else "malpe"
    day = "2025-02-25" if lang == "ar" else "2025-05-20"
    said = {h: explain.spoken(service.assess_trip(region, place, f"{day}T{h:02d}:00", 6, False, mode), lang)
            for h in range(5, 11)}
    openers = {explain.t(lang, f"say.opener.{i}") for i in range(explain.OPENERS)}
    assert all(any(s.startswith(o) for o in openers) for s in said.values())
    assert explain.spoken(service.assess_trip(region, place, f"{day}T05:00", 6, False, mode), lang) == said[5]


def test_several_reasons_are_joined_like_speech():
    said = explain.spoken(service.assess_trip("karnataka", "gangolli", "2025-05-20T14:00", 7, True,
                                              "karnataka_2025_05_20"), "en")
    assert "Watch out for the waves: up to 2.2 metres around 2 in the afternoon, over the unsafe line." in said
    assert "And visibility: down to 380 metres around 4 in the evening, under the caution line." in said
    assert said.endswith("Stay safe.")
