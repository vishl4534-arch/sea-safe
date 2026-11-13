"""Chat: the guard, the tool loop (with a fake model), and Gemini -> Groq fallback.
No network: the model and the weather are replaced with fakes."""
import json

import pytest

from app import chat, llm, service
from tests.test_text import CALM, fake_result


# ---- guard -------------------------------------------------------------------------
@pytest.mark.parametrize("text", [
    "Here is the check for Malpe, tomorrow morning.",
    "ಮಲ್ಪೆಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆಯ ಪರಿಶೀಲನೆ ಇಲ್ಲಿದೆ.",
    "إليك الفحص لميناء خورفكان صباح الغد.",
])
def test_guard_allows_neutral_intro(text):
    assert chat.guard(text, after_tool=True) == text


@pytest.mark.parametrize("text", [
    "Waves will be 2 m, so stay home.",            # a number
    "It is safe to go.",                            # verdict word
    "Conditions are UNSAFE this afternoon.",
    "The sea is calm.",                             # weather judgement
    "Here is the safest departure time for Gangolli today.",   # 'safest' framing
    "This is the best time to go.",
    "إليك أفضل وقت للخروج.",
    "ಇದು ಸುರಕ್ಷಿತ.",                                # Kannada verdict word
    "البحر آمن اليوم.",                             # Arabic verdict word
    "ಅಲೆಗಳು ೨ ಮೀ.",                                  # Kannada digit
    "الأمواج ٢ متر.",                               # Arabic-Indic digit
    "x" * 300,                                      # too long
])
def test_guard_blocks_numbers_verdicts_and_long_text(text):
    assert chat.guard(text, after_tool=True) is None


def test_guard_allows_times_in_a_clarifying_question():
    assert chat.guard("Which harbour do you leave from at 5?", after_tool=False)


def test_guard_blocks_verdict_even_without_tool():
    assert chat.guard("Yes, it is safe.", after_tool=False) is None


# ---- tool loop ---------------------------------------------------------------------
def tool_msg(name, **args):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": "c1", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


def scripted(replies, seen):
    it = iter(replies)

    def fake_complete(messages, tools):
        seen.append((messages, tools))
        return next(it), "fake (test)"
    return fake_complete


@pytest.fixture
def fake_service(monkeypatch):
    calls = []

    def fake_assess(region_id, place, dep, hours, given, mode, map_point):
        calls.append((place, dep, hours, given, mode))
        r = fake_result([{**CALM, "wave_height": 2.4}])
        r.update(departure=dep, trip_hours=hours, trip_length_given_by_user=given, ok=True)
        return r
    monkeypatch.setattr(service, "assess_trip", fake_assess)
    return calls


@pytest.fixture
def sentence_on(monkeypatch):
    """The model's intro sentence is off by default; these tests switch it on to test the guard path."""
    from app import config
    for lang in config.load_app()["languages"].values():
        monkeypatch.setitem(lang, "model_sentence", True)


def test_model_sentence_is_off_by_default_for_every_language():
    import yaml
    from app.config import ROOT
    raw = yaml.safe_load((ROOT / "config" / "app.yaml").read_text(encoding="utf-8"))
    assert all(v["model_sentence"] is False for v in raw["languages"].values())


def test_chat_calls_tool_and_reply_comes_from_templates(monkeypatch, fake_service, sentence_on):
    seen = []
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("assess_trip", place="malpe", day="tomorrow", hour=5, trip_hours=6,
                 trip_length_given_by_user=True),
        {"role": "assistant", "content": "It is totally safe, waves 0.5 m!"},   # model misbehaves
    ], seen))
    out = chat.chat([{"role": "user", "content": "Is it safe to leave Malpe at 5 tomorrow?"}], "en", "karnataka")
    from datetime import datetime
    from app.tools import resolve_day
    now = datetime.fromisoformat(service.clock_info("karnataka", "live")["now"])
    assert fake_service == [("malpe", resolve_day("tomorrow", 5, now), 6, True, "live")]
    assert "totally safe" not in out["reply"]                 # guard dropped the model's sentence
    assert out["reply"].startswith("Here is the check.")
    assert "Malpe: UNSAFE" in out["reply"]                     # verdict from code
    assert "unsafe line (2 m)" in out["reply"]
    assert "Trip length: 6 hours (as you chose)" in out["reply"]
    assert out["context"]["place"] == "malpe" and out["cards"][0]["result"]["verdict"] == "UNSAFE"
    # every tool parameter is required, no optional ones
    for t in seen[0][1]:
        p = t["function"]["parameters"]
        assert set(p["required"]) == set(p["properties"]) and p["additionalProperties"] is False


def test_follow_up_why_calls_the_assessment_again(monkeypatch, fake_service, sentence_on):
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("assess_trip", place="malpe", day="tomorrow", hour=5, trip_hours=6,
                 trip_length_given_by_user=True),
        {"role": "assistant", "content": "Here is the check again for Malpe."},
    ], []))
    ctx = {"place": "malpe", "departure": "2026-11-13T05:00", "trip_hours": 6, "given": True}
    out = chat.chat([{"role": "user", "content": "why is it unsafe?"}], "en", "karnataka", context=ctx)
    assert len(fake_service) == 1 and "Here is the check again for Malpe." in out["reply"]


def test_language_switch_off_uses_templates_only_and_one_model_call(monkeypatch, fake_service):
    from app import config
    cfg = config.load_app()
    monkeypatch.setitem(cfg["languages"]["kn"], "model_sentence", False)
    seen = []
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("assess_trip", place="malpe", day="tomorrow", hour=5, trip_hours=6,
                 trip_length_given_by_user=True),
        {"role": "assistant", "content": "ಇದು ನನ್ನ ವಾಕ್ಯ."},   # would be the second call; must not happen
    ], seen))
    out = chat.chat([{"role": "user", "content": "ಮಲ್ಪೆ?"}], "kn", "karnataka")
    assert len(seen) == 1                                         # no second round trip
    assert out["reply"].startswith("ಪರಿಶೀಲನೆ ಇಲ್ಲಿದೆ.")  # templated intro


def test_small_talk_is_the_models_own_words_even_with_the_switch_off(monkeypatch):
    # Owner request 13 Nov 2026: greetings get a conversational reply (through the guard); model_sentence
    # now only governs the words around a check.
    from app import config
    monkeypatch.setitem(config.load_app()["languages"]["ar"], "model_sentence", False)
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "أهلاً! من أي ميناء ستخرج؟"}], []))
    out = chat.chat([{"role": "user", "content": "مرحبا"}], "ar", "uae")
    assert out["reply"] == "أهلاً! من أي ميناء ستخرج؟"


def test_no_tool_reply_with_verdict_is_replaced(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "Yes it is safe."}], []))
    out = chat.chat([{"role": "user", "content": "safe?"}], "en", "karnataka")
    assert out["reply"] == ("I can check the sea for one harbour and one time. Which harbour do you want to leave "
                            "from? Mangaluru, Malpe, Gangolli, Bhatkal, Honnavar, Tadri, Belekeri, Karwar.")


def test_no_model_available_gives_templated_message(monkeypatch):
    def boom(messages, tools):
        raise llm.LLMUnavailable("down")
    monkeypatch.setattr(llm, "complete", boom)
    out = chat.chat([{"role": "user", "content": "hi"}], "kn", "karnataka")
    assert out["reply"] == "ಚಾಟ್ ಈಗ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ. ನಕ್ಷೆ ಮತ್ತು ಬಣ್ಣಗಳು ಕೆಲಸ ಮಾಡುತ್ತಿವೆ: ಪರಿಶೀಲಿಸಲು ಬಂದರು ಅಥವಾ ಸಮುದ್ರವನ್ನು ಒತ್ತಿ."


@pytest.mark.parametrize("value,ok", [("2026-11-13T05:00", True), ("2026-11-13T05:00:00", True),
                                      ("2026-11-13T05:30", False), ("tomorrow 5am", False)])
def test_time_pattern_accepts_what_both_providers_send(value, ok):
    import re
    from app.tools import TIME_PATTERN
    assert bool(re.match(TIME_PATTERN, value)) == ok


# ---- provider fallback -------------------------------------------------------------
class Resp:
    def __init__(self, code, body):
        self.status_code, self._body, self.text = code, body, json.dumps(body)

    def json(self):
        return self._body


def test_falls_back_from_gemini_to_groq(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDERS", "gemini,groq")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GROQ_API_KEY", "y")
    urls = []

    def fake_post(url, **kw):
        urls.append(url)
        if "googleapis" in url:
            return Resp(429, {"error": "rate limited"})
        return Resp(200, {"choices": [{"message": {"role": "assistant", "content": "hello"}}]})
    monkeypatch.setattr(llm, "_post", fake_post)
    msg, provider = llm.complete([{"role": "user", "content": "hi"}], [])
    assert provider.startswith("groq") and len(urls) == 2


def test_malformed_tool_call_triggers_fallback(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDERS", "gemini,groq")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GROQ_API_KEY", "y")

    def fake_post(url, **kw):
        if "googleapis" in url:
            return Resp(200, {"choices": [{"message": {"role": "assistant", "tool_calls": [
                {"id": "a", "type": "function", "function": {"name": "assess_trip", "arguments": "{not json"}}]}}]})
        return Resp(200, {"choices": [{"message": {"role": "assistant", "content": "ok"}}]})
    monkeypatch.setattr(llm, "_post", fake_post)
    assert llm.complete([], [])[1].startswith("groq")


def test_all_providers_failing_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDERS", "gemini,groq")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(llm.LLMUnavailable):
        llm.complete([], [])


def test_slow_first_provider_times_out_and_second_answers(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDERS", "groq,gemini")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    timeouts = []

    def fake_post(url, **kw):
        timeouts.append(kw["timeout"])
        if "groq" in url:
            raise llm.httpx.ReadTimeout("no answer in time")
        return Resp(200, {"choices": [{"message": {"role": "assistant", "content": "ok"}}]})
    monkeypatch.setattr(llm, "_post", fake_post)
    assert llm.complete([], [])[1].startswith("gemini")
    assert timeouts == [4.0, 4.0]                       # about 4 s per model call


def test_both_providers_timing_out_leaves_map_working(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDERS", "groq,gemini")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("GEMINI_API_KEY", "y")

    def fake_post(url, **kw):
        raise llm.httpx.ConnectTimeout("down")
    monkeypatch.setattr(llm, "_post", fake_post)
    out = chat.chat([{"role": "user", "content": "Malpe at 5?"}], "en", "karnataka")
    assert out["reply"].startswith("The chat is not working right now. The map and the colours still work")
    # the verdict does not depend on the model at all
    res = service.assess_trip("karnataka", "gangolli", "2025-05-20T11:00", 6, False, "karnataka_2025_05_20")
    assert res["ok"] and res["verdict"] == "UNSAFE"


# ---- the chat never asks for a time; it knows local harbour names ------------------------
def test_prompt_carries_aliases_and_on_screen_defaults(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "?"}], seen))
    chat.chat([{"role": "user", "content": "From Kundapura."}], "en", "karnataka", "karnataka_2025_05_20",
              page={"place": "malpe", "departure": "2025-05-20T08:00", "trip_hours": 8,
                    "trip_length_given_by_user": True})
    prompt = seen[0][0][0]["content"]
    assert "gangolli: Gangolli / Gangolli (also called: Kundapura" in prompt
    assert "The harbour selected on screen is 'malpe'." in prompt
    assert "departure day=today hour=8, trip length 8 hours (trip_length_given_by_user=true)" in prompt
    assert "never guess a time" in prompt
    assert "Never work out a date yourself" in prompt


def test_past_on_screen_departure_falls_back_to_the_default(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "?"}], seen))
    chat.chat([{"role": "user", "content": "Gangoli"}], "en", "karnataka", "karnataka_2025_05_20",
              page={"departure": "2020-01-01T05:00"})
    assert "On screen now: departure day=today hour=5" in seen[0][0][0]["content"]


# ---- day words are turned into dates by code, not by the model --------------------------
from datetime import datetime  # noqa: E402

from app.tools import resolve_day, resolve_range  # noqa: E402


@pytest.mark.parametrize("now,day,hour,expected", [
    ("2026-11-13T00:00", "tomorrow", 6, "2026-11-13T06:00"),     # just after midnight: the coming morning
    ("2026-11-13T03:00", "tomorrow", 5, "2026-11-13T05:00"),
    ("2026-11-13T04:00", "tomorrow", 5, "2026-11-14T05:00"),     # from 04:00 tomorrow is the next date
    ("2026-11-13T15:00", "today", 17, "2026-11-13T17:00"),
    ("2026-11-13T15:00", "day_after_tomorrow", 5, "2026-11-15T05:00"),
    ("2026-11-13T01:00", "day_after_tomorrow", 5, "2026-11-14T05:00"),
])
def test_day_words_resolve_by_code(now, day, hour, expected):
    assert resolve_day(day, hour, datetime.fromisoformat(now)) == expected


def test_safest_ranges():
    now, end = datetime(2026, 11, 13, 15), datetime(2026, 11, 15, 15)
    assert resolve_range("tomorrow", now, end) == ("2026-11-14T00:00", "2026-11-14T23:00")
    assert resolve_range("next_48_hours", now, end) == ("2026-11-13T15:00", "2026-11-15T15:00")


def test_tools_take_day_words_not_dates():
    from app.tools import schemas
    for tool in schemas(["malpe"], 24):
        props = tool["function"]["parameters"]["properties"]
        assert not any("local" in k for k in props)
        if tool["function"]["name"] not in ("explain_app", "official_info"):     # these take no time at all
            assert "day" in props
