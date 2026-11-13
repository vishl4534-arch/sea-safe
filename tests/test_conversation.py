"""Multi-turn conversation behaviour found while testing real en / kn / ar chats by text and voice.
Each rule here is done by code, not trusted to the model."""
import json

import pytest

from app import chat, explain, llm, service, voice
from app.config import region as get_region
from app.tools import trip_from_return
from tests.test_chat import scripted, tool_msg

KA, KA_REPLAY = "karnataka", "karnataka_2025_05_20"       # replay clock: now 2025-05-20T04:00
UAE, UAE_REPLAY = "uae", "uae_2025_02_25"


def call(name, **args):
    return {"function": {"name": name, "arguments": json.dumps(args)}}


def assess(**over):
    args = dict(place="gangolli", day="same", hour=-1, back_by_hour=-1, trip_hours=6, trip_length_given_by_user=False)
    return call("assess_trip", **{**args, **over})


@pytest.fixture
def spy(monkeypatch):
    calls = []

    def fake_assess(region_id, place, dep, hours, given, mode, map_point):
        calls.append({"place": place, "dep": dep, "hours": hours, "given": given})
        return {"ok": True}

    def fake_safest(region_id, place, start, end, hours, given, mode, map_point):
        calls.append({"place": place, "start": start, "end": end, "hours": hours, "given": given})
        return {"ok": True}
    monkeypatch.setattr(service, "assess_trip", fake_assess)
    monkeypatch.setattr(service, "find_safest_time", fake_safest)
    return calls


# ---- places named in the user's own words ---------------------------------------------------
@pytest.mark.parametrize("region,text,expected", [
    (KA, "is it safe from kundapura at 6?", {"gangolli"}),
    (KA, "ಮಲ್ಪೆಯಿಂದ", {"malpe"}),                       # joined Kannada form "from Malpe"
    (KA, "what about mangalore", {"mangaluru"}),
    (UAE, "طيب، ودبا؟", {"dibba_al_hisn"}),             # joined Arabic form "and Dibba"
    (UAE, "RAK tomorrow night", {"rak_al_rams"}),
    (KA, "and from Bombay?", set()),
    (KA, "why is it unsafe", set()),
    (KA, "malpebeach", set()),                           # Latin names match whole words only
])
def test_mentioned_harbours(region, text, expected):
    assert chat.mentioned_harbours(text, get_region(region)) == expected


def test_place_named_by_the_user_overrides_the_model(spy):
    chat._run_tool(assess(place="dubai_umm_suqeim", hour=5, trip_length_given_by_user=True), UAE, UAE_REPLAY, None,
                   user_text="طيب ودبا؟")
    assert spy[0]["place"] == "dibba_al_hisn"


def test_place_is_not_changed_when_none_or_several_are_named(spy):
    chat._run_tool(assess(place="malpe"), KA, KA_REPLAY, None, CTX, user_text="why?")
    chat._run_tool(assess(place="malpe"), KA, KA_REPLAY, None, CTX, user_text="malpe or karwar?")
    assert [c["place"] for c in spy] == ["malpe", "malpe"]


# ---- departure: code keeps the previous one when the user does not say one --------------------
CTX = {"place": "gangolli", "departure": "2025-05-20T14:00", "trip_hours": 6, "given": True}


@pytest.mark.parametrize("over,expected", [
    ({}, "2025-05-20T14:00"),                                   # "what about Mangalore?"
    ({"hour": 18}, "2025-05-20T18:00"),                        # "and at 6 in the evening?" - same day
    ({"day": "tomorrow"}, "2025-05-21T14:00"),                 # "and tomorrow?" - same hour
    ({"day": "today", "hour": 5}, "2025-05-20T05:00"),
])
def test_departure_kept_from_the_previous_check(spy, over, expected):
    chat._run_tool(assess(**over), KA, KA_REPLAY, None, CTX)
    assert spy[0]["dep"] == expected


def test_departure_without_context_uses_screen_else_the_app_asks(spy):
    # The page no longer shows a departure, but an older page may still send one.
    chat._run_tool(assess(), KA, KA_REPLAY, None, page={"departure": "2025-05-20T08:00",
                                                         "trip_length_given_by_user": True, "trip_hours": 6})
    asked = chat._run_tool(assess(), KA, KA_REPLAY, None)["result"]
    assert [c["dep"] for c in spy] == ["2025-05-20T08:00"]
    assert asked["error"] == "need_details" and asked["need"] == ["time", "length"]


# ---- "back by 9": code works out the trip length --------------------------------------------
@pytest.mark.parametrize("dep,back,hours", [
    ("2025-05-20T14:00", 9, 7),      # 9 means 21:00 after an afternoon start
    ("2025-05-20T05:00", 12, 7),
    ("2025-05-20T05:00", 9, 4),
    ("2025-05-20T22:00", 6, 8),      # past midnight
    ("2025-05-20T14:00", 13, 23),    # 13:00 has already passed: the next day
])
def test_trip_from_return(dep, back, hours):
    assert trip_from_return(dep, back) == hours


def test_back_by_keeps_departure_and_sets_given(spy):
    # Kannada and Arabic "I'll be back at 9" once moved the departure to 05:00; now the model sends hour -1.
    chat._run_tool(assess(back_by_hour=9), KA, KA_REPLAY, None, CTX)
    assert spy[0] == {"place": "gangolli", "dep": "2025-05-20T14:00", "hours": 7, "given": True}


def test_trip_length_chosen_earlier_stays_given(spy):
    ctx = {**CTX, "trip_hours": 8, "given": True}
    chat._run_tool(assess(trip_hours=8), KA, KA_REPLAY, None, ctx)
    chat._run_tool(call("find_safest_time", place="gangolli", day="today", trip_hours=8,
                        trip_length_given_by_user=False), KA, KA_REPLAY, None, ctx)
    assert [c["given"] for c in spy] == [True, True, True]   # the third: tomorrow (today has no SAFE hour), also given


def test_safest_with_same_day_searches_the_previous_checks_day(spy):
    chat._run_tool(call("find_safest_time", place="gangolli", day="same", trip_hours=6,
                        trip_length_given_by_user=False), KA, KA_REPLAY, None,
                   {**CTX, "departure": "2025-05-21T14:00"})
    assert (spy[0]["start"], spy[0]["end"]) == ("2025-05-21T00:00", "2025-05-21T23:00")


# ---- days outside the forecast --------------------------------------------------------------
@pytest.mark.parametrize("tool,day,error", [
    ("assess_trip", "past", "past_time"), ("assess_trip", "later", "outside_window"),
    ("find_safest_time", "past", "past_time"), ("find_safest_time", "later", "outside_window"),
])
def test_outside_days_get_a_templated_limit(spy, tool, day, error):
    c = assess(day=day) if tool == "assess_trip" else call(
        "find_safest_time", place="bhatkal", day=day, trip_hours=6, trip_length_given_by_user=False)
    run = chat._run_tool(c, KA, KA_REPLAY, None)
    assert run["result"] == {"ok": False, "error": error} and spy == []


# ---- what is written and spoken ---------------------------------------------------------------
@pytest.mark.parametrize("lang", ["en", "kn"])
def test_no_intro_in_front_of_an_error(monkeypatch, lang):
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("find_safest_time", place="bhatkal", day="later", trip_hours=6, trip_length_given_by_user=False),
        {"role": "assistant", "content": "Here is the check."},
    ], []))
    out = chat.chat([{"role": "user", "content": "can I go next week from bhatkal?"}], lang, KA, KA_REPLAY)
    assert not out["reply"].startswith(explain.t(lang, "chat.neutral_intro"))
    assert out["reply"] == explain.error_text({"ok": False, "error": "outside_window"}, lang)
    assert out["cards"] == []


@pytest.mark.parametrize("lang,region,replay,place,day", [
    ("en", KA, KA_REPLAY, "gangolli", "2025-05-20"), ("kn", KA, KA_REPLAY, "gangolli", "2025-05-20"),
    ("ar", UAE, UAE_REPLAY, "khor_fakkan", "2025-02-25")])
def test_safest_answer_speaks_only_the_windows(monkeypatch, lang, region, replay, place, day):
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("find_safest_time", place=place, day="today", trip_hours=6, trip_length_given_by_user=True),
        {"role": "assistant", "content": "Here are the departure times."},
    ], []))
    out = chat.chat([{"role": "user", "content": f"when is the best time today from {explain.t('en', 'place.' + place)}?"}],
                    lang, region, replay)
    res = service.find_safest_time(region, place, f"{day}T00:00", f"{day}T23:00", 6, True, replay, None)
    assert out["spoken"] == (f"{explain.safest_spoken(res, lang)} "
                             f"{explain.t(lang, 'say.disclaimer')}")
    assert explain.t(lang, f"place_from.{place}") in out["spoken"]            # says which harbour
    assert explain.spoken(res["shown"], lang) not in out["spoken"]       # the example trip is on the card only
    assert len(out["cards"]) == 1


def test_safest_keeps_the_users_own_departure_for_follow_ups(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("find_safest_time", place="gangolli", day="today", trip_hours=6, trip_length_given_by_user=False),
        {"role": "assistant", "content": "Here are the departure times."},
    ], []))
    out = chat.chat([{"role": "user", "content": "when is the best time today?"}], "en", KA, KA_REPLAY, context=CTX)
    assert out["context"]["departure"] == "2025-05-20T14:00"


# ---- voice: harbour names help speech-to-text hear them ----------------------------------------
@pytest.mark.parametrize("region,lang,term", [(UAE, "ar", "دبا"), (UAE, "ar", "Dibba"), (KA, "kn", "Kundapura"),
                                              (KA, "kn", "ಮಲ್ಪೆ")])
def test_harbour_keyterms(region, lang, term):
    terms = voice.harbour_keyterms(get_region(region), lang)
    assert term in terms
    assert len(terms) <= 100 and len(set(terms)) == len(terms)
    assert all(len(x) <= 50 and len(x.split()) <= 5 and not voice.BAD_KEYTERM & set(x) for x in terms)


# ---- a trip length the user said is read by code -------------------------------------------------
@pytest.mark.parametrize("text,hours", [
    ("Hello. Uh, I would like to take a six-hour fishing trip from, uh, the Umm Al Quwain harbor.", 6),
    ("for 8 hours", 8), ("a 10 hr trip", 10), ("a 12-hour trip", 12), ("24 hours", 24),
    ("ಆರು ಗಂಟೆಯ ಪ್ರಯಾಣ", 6), ("6 ಗಂಟೆಗಳ ಕಾಲ", 6), ("೮ ಗಂಟೆ ಕಾಲ", 8),
    ("رحلة 6 ساعات", 6), ("ست ساعات", 6), ("لمدة ساعتين", 2), ("٨ ساعات", 8),
    # clock times are not trip lengths
    ("at 6 in the morning", None), ("is it safe at 6?", None), ("6:00", None), ("back by 9", None),
    ("ಬೆಳಿಗ್ಗೆ 6 ಗಂಟೆಗೆ", None), ("الساعة 6 الصبح", None), ("الساعة ٦", None),
    ("twenty-four hours", None),        # left to the model rather than misread as 4
])
def test_stated_trip_hours(text, hours):
    assert chat.stated_trip_hours(text) == hours


def test_stated_length_overrides_the_model(spy):
    # Groq sent trip_length_given_by_user=false for "a six-hour fishing trip" (6 is also the default).
    q = "I would like to take a six-hour fishing trip from the Umm Al Quwain harbor. Is it safe?"
    chat._run_tool(assess(place="umm_al_quwain", hour=5, trip_hours=6), UAE, UAE_REPLAY, None, user_text=q)
    chat._run_tool(call("find_safest_time", place="umm_al_quwain", day="today", trip_hours=6,
                        trip_length_given_by_user=False), UAE, UAE_REPLAY, None, user_text="best time for 8 hours?")
    assert (spy[0]["hours"], spy[0]["given"]) == (6, True)
    assert (spy[1]["hours"], spy[1]["given"]) == (8, True)


def test_return_time_wins_over_a_stated_length(spy):
    chat._run_tool(assess(back_by_hour=9), KA, KA_REPLAY, None, CTX, user_text="6 hours, back by 9")
    assert spy[0]["hours"] == 7


# ---- midnight is said the way people say it ------------------------------------------------------
def test_midnight_is_the_end_of_the_day_before():
    r = service.assess_trip(UAE, "umm_al_quwain", "2025-02-26T00:00", 6, True, UAE_REPLAY)  # 00:00 Wednesday
    said = explain.spoken(r, "en")
    assert "leaving from Umm Al Quwain on Tuesday at midnight" in said
    assert "You'd be back around 6 in the morning." in said
    r = service.assess_trip(UAE, "umm_al_quwain", "2025-02-25T18:00", 6, True, UAE_REPLAY)  # back at 00:00
    assert "You'd be back around midnight." in explain.spoken(r, "en")


# ---- "which harbours are safe at 1 pm?" checks every harbour, never one picked by the model -----------
@pytest.mark.parametrize("lang,region,replay", [("en", UAE, UAE_REPLAY), ("ar", UAE, UAE_REPLAY), ("kn", KA, KA_REPLAY)])
def test_all_harbours_answer(monkeypatch, lang, region, replay):
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("check_all_harbours", day="today", hour=13, trip_hours=4, trip_length_given_by_user=False),
    ], []))
    q = "So which all harbors is it safe to go on a fishing trip at 1:00 p.m., for 4 hours?"
    out = chat.chat([{"role": "user", "content": q}], lang, region, replay)
    day = replay[-10:].replace("_", "-")
    res = service.assess_region(region, f"{day}T13:00", 4, replay)
    for hid, r in res["harbours"].items():
        name = explain.place_name(lang, r["place"])
        assert name in out["reply"]                                           # the card / text lists every harbour
        assert (name in out["spoken"]) == (r["verdict"] != "CAUTION")         # the voice names SAFE and UNSAFE ones
    assert explain.t(lang, "say.disclaimer") in out["spoken"] and explain.t(lang, "disclaimer") in out["reply"]
    assert "Open-Meteo" in out["reply"] and out["cards"] == []
    assert out["context"]["departure"] == f"{day}T13:00" and out["context"]["given"] is True


@pytest.mark.parametrize("dep,expected", [
    ("2025-02-25T13:00", "Dibba Al-Hisn looks safe. Abu Dhabi – Mina Zayed, Dubai – Umm Suqeim and Dubai – Al Hamriya "
                         "are unsafe. The others are a caution."),
    ("2025-02-26T05:00", "Dibba Al-Hisn and Khor Fakkan look safe. The others are a caution."),
])
def test_all_harbours_speech_is_short(dep, expected):
    res = service.assess_region(UAE, dep, 4, UAE_REPLAY)
    said = explain.region_spoken({**res, "departure": dep, "trip_hours": 4}, "en")
    assert expected in said and "Umm Al Quwain" not in said                  # CAUTION harbours are summed up


def test_all_harbours_speech_when_none_or_all_are_safe():
    res = service.assess_region(KA, "2025-05-20T13:00", 4, KA_REPLAY)
    said = explain.region_spoken({**res, "departure": "2025-05-20T13:00", "trip_hours": 4}, "en")
    assert "no harbour looks safe. Mangaluru and Gangolli are unsafe. The others are a caution." in said
    fake = {"departure": "2025-02-25T13:00", "trip_hours": 4,
            "harbours": {k: {**v, "verdict": "SAFE"} for k, v in service.assess_region(UAE, "2025-02-25T13:00", 4,
                                                                                         UAE_REPLAY)["harbours"].items()}}
    assert "every harbour looks safe." in explain.region_spoken(fake, "en")


# ---- "right now" is said as "now" (live, current hour) --------------------------------------------
@pytest.mark.parametrize("lang,region,replay,place,word", [
    ("en", UAE, UAE_REPLAY, "abu_dhabi_mina_zayed", "leaving from Abu Dhabi – Mina Zayed now:"),
    ("ar", UAE, UAE_REPLAY, "abu_dhabi_mina_zayed", "الآن،"), ("kn", KA, KA_REPLAY, "malpe", "ಈಗ ಮಲ್ಪೆಯಿಂದ ಹೊರಟರೆ,")])
def test_leaving_now_is_said_as_now(lang, region, replay, place, word):
    day = replay[-10:].replace("_", "-")
    r = service.assess_trip(region, place, f"{day}T05:00", 6, False, replay)
    assert word not in explain.spoken(r, lang)
    r["leaving_now"] = True
    said = explain.spoken(r, lang)
    assert word in said and "  " not in said


def test_leaving_now_flag_only_for_the_current_live_hour(spy, monkeypatch):
    monkeypatch.setattr(service, "clock_info", lambda region, mode: {
        "now": "2026-11-13T00:00", "window_end": "2026-11-15T00:00", "default_departure": "2026-11-13T01:00"})
    monkeypatch.setattr(service, "assess_trip", lambda *a: {"ok": True})
    now = chat._run_tool(assess(place="ajman", day="today", hour=0, trip_length_given_by_user=True), UAE, "live", None)
    later = chat._run_tool(assess(place="ajman", day="today", hour=14, trip_length_given_by_user=True), UAE, "live", None)
    assert now["result"].get("leaving_now") is True and "leaving_now" not in later["result"]


def test_all_harbours_answer_comes_with_a_card(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("check_all_harbours", day="today", hour=14, trip_hours=4, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": "which harbour is okay at 2 pm?"}], "en", UAE, UAE_REPLAY)
    v = out["region"]
    assert v["departure"] == "2025-02-25T14:00" and v["trip_hours"] == 4
    assert sum(len(g["places"]) for g in v["groups"]) == len(service.assess_region(UAE, "2025-02-25T14:00", 4, UAE_REPLAY)["harbours"])
    assert v["disclaimer"] and v["attribution"] == "Weather data by Open-Meteo.com" and v["warnings"]


@pytest.mark.parametrize("page", [{"departure": None, "trip_hours": None}, {"departure": "soon", "trip_hours": "4"},
                                  {"departure": 5, "trip_hours": 99, "trip_length_given_by_user": True}, "junk", None])
def test_a_bad_page_state_never_crashes_the_chat(monkeypatch, page):
    monkeypatch.setattr(llm, "complete", scripted([
        tool_msg("assess_trip", place="malpe", day="same", hour=-1, back_by_hour=-1, trip_hours=6,
                 trip_length_given_by_user=False)], []))
    out = chat.chat([{"role": "user", "content": "is it safe from Malpe?"}], "en", KA, KA_REPLAY, page=page)
    # a bad page state is dropped, so nothing is known: the app asks for the time and the length
    assert out["cards"] == [] and out["reply"] == chat.need_text({"need": ["time", "length"], "place": "malpe"}, "en")
    assert out["context"] == {"place": "malpe"}


def test_rest_of_the_day_questions_use_the_day_windows():
    prompt = chat._system_prompt(chat.get_region(KA), "en", KA_REPLAY, None, None, None)
    assert 'would the conditions become worse today, or is it always safe?" -> find_safest_time' in prompt
