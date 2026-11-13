"""Speed rules: a hard time cap per model provider, asking the next provider early when the first is slow,
and fetching the spoken answer before the page asks for it."""
import threading
import time
from types import SimpleNamespace

import pytest

from app import llm, voice
from tests.test_chat import Resp
from tests.test_voice import MP3

OK = {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}


@pytest.fixture
def two_providers(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDERS", "groq,gemini")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    calls = []

    def provider(delays):
        def fake_post(url, **kw):
            name = "groq" if "groq" in url else "gemini"
            calls.append(name)
            time.sleep(delays[name])
            return Resp(200, OK)
        monkeypatch.setattr(llm, "_post", fake_post)
    return provider, calls


def test_stalled_provider_is_cut_off_at_the_cap(monkeypatch, two_providers):
    provider, calls = two_providers
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "0.3")
    monkeypatch.setenv("LLM_HEDGE_SECONDS", "10")          # no early second call: only the cap applies
    provider({"groq": 3, "gemini": 0})                      # Groq hangs far longer than any network timeout
    t = time.monotonic()
    assert llm.complete([], [])[1].startswith("gemini")
    assert time.monotonic() - t < 1.0 and calls == ["groq", "gemini"]


def test_slow_first_provider_gets_company_after_the_hedge_time(monkeypatch, two_providers):
    provider, calls = two_providers
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "4")
    monkeypatch.setenv("LLM_HEDGE_SECONDS", "0.2")
    provider({"groq": 2, "gemini": 0.05})
    t = time.monotonic()
    assert llm.complete([], [])[1].startswith("gemini")
    assert time.monotonic() - t < 0.8                       # did not wait for Groq's 2 s


def test_fast_first_provider_is_the_only_call(monkeypatch, two_providers):
    provider, calls = two_providers
    monkeypatch.setenv("LLM_HEDGE_SECONDS", "0.5")
    provider({"groq": 0.05, "gemini": 0})
    assert llm.complete([], [])[1].startswith("groq") and calls == ["groq"]


def test_both_stalled_raises_within_the_caps(monkeypatch, two_providers):
    provider, calls = two_providers
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "0.2")
    monkeypatch.setenv("LLM_HEDGE_SECONDS", "10")
    provider({"groq": 3, "gemini": 3})
    t = time.monotonic()
    with pytest.raises(llm.LLMUnavailable):
        llm.complete([], [])
    assert time.monotonic() - t < 1.0


# ---- the spoken answer is fetched as soon as it is known -------------------------------------------
@pytest.fixture
def slow_eleven(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setattr(voice, "AUDIO_DIR", tmp_path)
    monkeypatch.setattr(voice, "_pending", {})
    monkeypatch.setattr(voice, "_fetches", {})
    state = {"calls": 0, "status": 200, "release": threading.Event()}

    class Stream:
        def __init__(self):
            state["calls"] += 1
            self.status_code = state["status"]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"refused"

        def iter_bytes(self):
            yield MP3[:5]
            state["release"].wait(2)       # the rest arrives later, while the page is already playing
            yield MP3[5:]
    monkeypatch.setattr(voice, "_http", SimpleNamespace(stream=lambda *a, **kw: Stream()))
    return state


def test_prepare_starts_fetching_and_the_page_joins_it(slow_eleven):
    aid = voice.prepare("Malpe: SAFE.", "en")
    time.sleep(0.1)
    assert slow_eleven["calls"] == 1                         # started before the page asked
    chunks = voice.open_stream(aid)
    assert next(chunks) == MP3[:5]                           # first audio is there at once
    slow_eleven["release"].set()
    assert b"".join(chunks) == MP3[5:]
    time.sleep(0.05)
    assert voice.audio_path(aid).read_bytes() == MP3 and slow_eleven["calls"] == 1


def test_prefetch_failure_is_a_clean_error_and_can_be_retried(slow_eleven):
    slow_eleven["status"] = 401
    aid = voice.prepare("Malpe: SAFE.", "en")
    with pytest.raises(voice.VoiceError):
        voice.open_stream(aid)
    slow_eleven["status"] = 200
    slow_eleven["release"].set()
    assert b"".join(voice.open_stream(aid)) == MP3          # the page's next try starts a fresh fetch
