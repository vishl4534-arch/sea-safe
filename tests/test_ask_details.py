"""The bot asks for any trip detail the fisher has not given (harbour, departure time, trip length), keeps what
it knows across turns, and only checks once the trip is complete. Greetings get a friendly reply. 13 Nov 2026.
No network: the model is scripted and the weather comes from saved replay data."""
import pytest

from app import chat, explain, llm
from tests.test_chat import scripted, tool_msg

KA, KA_REPLAY = "karnataka", "karnataka_2025_05_20"       # replay clock: now 2025-05-20T04:00
UAE, UAE_REPLAY = "uae", "uae_2025_02_25"


def trip(**over):
    args = dict(place="malpe", day="same", hour=-1, minute=0, back_by_hour=-1, back_day="same", trip_hours=6,
                trip_length_given_by_user=False)
    return tool_msg("assess_trip", **{**args, **over})


def ask(lang, region, mode, question, reply, context=None):
    llm_replies = [reply] if isinstance(reply, dict) else reply
    return lambda monkeypatch: (monkeypatch.setattr(llm, "complete", scripted(llm_replies, [])),
                                chat.chat([{"role": "user", "content": question}], lang, region, mode, context=context))[1]


@pytest.mark.parametrize("lang,region,mode,place,question", [
    ("en", KA, KA_REPLAY, "malpe", "Can I go out from Malpe?"),
    ("kn", KA, KA_REPLAY, "malpe", "ಮಲ್ಪೆಯಿಂದ ಹೋಗಬಹುದಾ?"),
    ("ar", UAE, UAE_REPLAY, "dibba_al_hisn", "هل أقدر أطلع من دبا؟"),
])
def test_place_only_asks_for_time_and_length(monkeypatch, lang, region, mode, place, question):
    out = ask(lang, region, mode, question, trip(place=place))(monkeypatch)
    assert out["cards"] == [] and out["reply"] == out["spoken"]
    assert out["reply"] == explain.t(lang, "chat.ask_both", name=explain.t(lang, f"place.{place}"))
    assert out["context"] == {"place": place}


def test_time_without_length_asks_for_the_length_and_remembers_the_time(monkeypatch):
    out = ask("en", KA, KA_REPLAY, "Malpe at 5 tomorrow morning?", trip(day="tomorrow", hour=5))(monkeypatch)
    assert out["reply"] == "Malpe, leaving Wed 21 May, 05:00, got it. How long will you be at sea, or when will you be back?"
    assert out["context"] == {"place": "malpe", "departure": "2025-05-21T05:00"}


def test_length_without_time_asks_for_the_time_and_remembers_the_length(monkeypatch):
    out = ask("en", KA, KA_REPLAY, "Malpe, a 6 hour trip?", trip(trip_length_given_by_user=True))(monkeypatch)
    assert out["reply"] == "Malpe, a 6-hour trip, got it. What time will you leave?"
    assert out["context"] == {"place": "malpe", "trip_hours": 6, "given": True}


def test_the_answer_to_the_question_completes_the_trip(monkeypatch):
    # Turn 1 gave the place and the time; turn 2 ("6 hours") gives the length. Now it is checked.
    ctx = {"place": "malpe", "departure": "2025-05-21T05:00"}
    out = ask("en", KA, KA_REPLAY, "6 hours", trip(trip_hours=6, trip_length_given_by_user=True), ctx)(monkeypatch)
    r = out["cards"][0]["result"]
    assert (r["place"]["id"], r["departure"], r["trip_hours"], r["trip_length_given_by_user"]) == \
        ("malpe", "2025-05-21T05:00", 6, True)


def test_back_by_counts_as_the_length(monkeypatch):
    out = ask("en", KA, KA_REPLAY, "Malpe at 2 pm, back by 9", trip(day="today", hour=14, back_by_hour=9))(monkeypatch)
    r = out["cards"][0]["result"]
    assert (r["departure"], r["trip_hours"]) == ("2025-05-20T14:00", 7)


def test_all_harbours_asks_too_without_a_harbour_name(monkeypatch):
    c = tool_msg("check_all_harbours", day="today", hour=-1, minute=0, trip_hours=6, trip_length_given_by_user=False)
    out = ask("en", KA, KA_REPLAY, "which harbours are ok?", c)(monkeypatch)
    assert out["reply"] == explain.t("en", "chat.need_both_any")


@pytest.mark.parametrize("greeting,reply", [
    ("hi", "Hello! Where will you go out from today, when will you leave, and for how long?"),
    ("hi im vish how are u", "Hi Vish, I'm well, thank you! Where are you heading out from, and when?"),
    ("ಹಾಯ್", "ನಮಸ್ಕಾರ! ಇವತ್ತು ಯಾವ ಬಂದರಿನಿಂದ, ಎಷ್ಟು ಗಂಟೆಗೆ ಹೊರಡುತ್ತೀರಿ?"),
    ("مرحبا، كيف حالك؟", "أهلاً! أنا بخير، شكراً. من أي ميناء ستخرج اليوم، ومتى؟"),
])
def test_greetings_get_the_models_friendly_reply(monkeypatch, greeting, reply):
    lang = "kn" if "ಹಾ" in greeting else "ar" if "مرحبا" in greeting else "en"
    region, mode = (UAE, UAE_REPLAY) if lang == "ar" else (KA, KA_REPLAY)
    out = ask(lang, region, mode, greeting, {"role": "assistant", "content": reply})(monkeypatch)
    assert out["reply"] == reply and out["cards"] == []


def test_a_greeting_that_talks_about_safety_is_replaced(monkeypatch):
    out = ask("en", KA, KA_REPLAY, "hi", {"role": "assistant", "content": "Hi! The sea is calm and safe today."})(monkeypatch)
    assert "safe" not in out["reply"].lower().replace("sea safe", "") and out["cards"] == []


def test_prompt_has_the_conversation_rule_and_no_old_never_ask():
    prompt = chat._system_prompt(chat.get_region(KA), "en", KA_REPLAY, None, None, {})
    assert "greetings and small talk" in prompt.lower() and "Use their name" in prompt
    assert "NEVER ask for a time" not in prompt and "NEVER ask for a trip length" not in prompt
    assert "only the user's words count" in prompt


# ---- "leaving at 5" at 09:35 means 17:00 (owner's chat, 13 Nov 2026) ----------------------------------------
LIVE_CLOCK = {"now": "2026-11-13T09:00", "window_end": "2026-11-15T09:00", "default_departure": "2026-11-13T10:00",
              "replay": None}


@pytest.fixture
def at_0935(monkeypatch):
    from app import service
    seen = []
    monkeypatch.setattr(service, "clock_info", lambda region, mode: LIVE_CLOCK)
    monkeypatch.setattr(service, "assess_trip", lambda region, place, dep, hours, given, mode, mp:
                        seen.append((dep, hours)) or {"ok": True})
    return seen


@pytest.mark.parametrize("text", ["leaving at 5 being back by 10", "UAQ at 5", "الساعة 5", "5 ಕ್ಕೆ"])
def test_a_bare_hour_that_has_passed_means_the_evening(at_0935, text):
    chat._run_tool(trip(place="umm_al_quwain", day="today", hour=5, back_by_hour=10)["tool_calls"][0], UAE, "live", None,
                   {}, text, {})
    assert at_0935 == [("2026-11-13T17:00", 5)]


@pytest.mark.parametrize("text", ["at 5 am", "5 in the morning", "الساعة 5 الصبح", "ಬೆಳಿಗ್ಗೆ 5 ಕ್ಕೆ"])
def test_a_morning_hour_that_was_said_is_kept_and_reported_as_past(at_0935, text):
    run = chat._run_tool(trip(place="umm_al_quwain", day="today", hour=5, trip_length_given_by_user=True)["tool_calls"][0],
                         UAE, "live", None, {}, text, {})
    assert at_0935 == [] and run["result"]["error"] == "past_time_at"


def test_a_past_time_is_caught_before_asking_for_the_length(monkeypatch, at_0935):
    monkeypatch.setattr(llm, "complete", scripted([trip(place="umm_al_quwain", day="today", hour=5)], []))
    out = chat.chat([{"role": "user", "content": "UAQ at 5 am"}], "en", UAE, "live")
    assert out["reply"] == "Fri 13 Nov, 05:00 has already passed. Tell me a later time, like tomorrow at 05:00."
    assert out["context"] == {"place": "umm_al_quwain"}


def test_a_future_morning_hour_is_not_moved(at_0935):
    chat._run_tool(trip(place="umm_al_quwain", day="today", hour=11, trip_length_given_by_user=True)["tool_calls"][0],
                   UAE, "live", None, {}, "at 11", {})
    assert at_0935 == [("2026-11-13T11:00", 6)]
