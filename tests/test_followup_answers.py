"""Follow-up answers from the owner's first real-mic test (13 Nov 2026):
1. "What time do you recommend I leave by?" (safer times): short bullets with leave-by and back-by, and no
   verdict badge, because the trip the fisher planned is not the one shown.
2. "What time do I come back by?": the return time is the first line, written and spoken."""
from app import chat, explain, llm, service
from tests.test_chat import scripted, tool_msg

UAE, UAR = "uae", "uae_2025_02_25"


def safest(place="dibba_al_hisn", hours=4):
    return service.find_safest_time(UAE, place, "2025-02-25T00:00", "2025-02-25T23:00", hours, True, UAR)


def test_one_safe_window_says_leave_by_and_back_by():
    sres = {"case": "some_safe", "trip_hours": 4, "search_from": "2025-02-25T00:00", "search_to": "2025-02-25T23:00",
            "safe_windows": [("2025-02-25T10:00", "2025-02-25T13:00")], "caution_windows": [], "unsafe_windows": [],
            "shown": safest()["shown"]}
    b = explain.safest_bullets(sres, "en").split("\n")
    assert b[1] == "• Leave by 13:00 at the latest: back by 17:00."
    assert all(x.startswith("• ") for x in b) and b[-1] == "• Forecast, not a guarantee: check the official warnings."


def test_a_single_safe_hour_says_leave_at():
    sres = {"case": "some_safe", "trip_hours": 4, "search_from": "2025-02-25T00:00", "search_to": "2025-02-25T23:00",
            "safe_windows": [("2025-02-25T13:00", "2025-02-25T13:00")], "caution_windows": [],
            "unsafe_windows": [("2025-02-25T15:00", "2025-02-25T20:00")], "shown": safest()["shown"]}
    b = explain.safest_bullets(sres, "en").split("\n")
    # one SAFE hour: said once, with the return time (owner, 13 Nov 2026), not listed and then repeated
    assert b[0] == "• Dibba Al-Hisn, 4-hour trip: the only SAFE time to leave is Tue 25 Feb, 13:00, back by 17:00."
    assert sum("13:00" in x for x in b) == 1
    assert any(x.startswith("• UNSAFE: do not leave") for x in b)


def test_spoken_safer_time_says_when_to_leave_and_be_back():
    base = {"case": "some_safe", "trip_hours": 4, "search_from": "2025-02-25T00:00", "search_to": "2025-02-25T23:00",
            "caution_windows": [], "unsafe_windows": [], "shown": safest()["shown"]}
    one_hour = explain.safest_spoken({**base, "safe_windows": [("2025-02-25T13:00", "2025-02-25T13:00")]}, "en")
    assert one_hour.endswith("the only SAFE time to leave for a 4-hour trip is at 1 in the afternoon, "
                             "and you'd be back at 5 in the evening.")
    assert one_hour.count("1 in the afternoon") == 1          # said once, not listed and then repeated
    window = explain.safest_spoken({**base, "safe_windows": [("2025-02-25T06:00", "2025-02-25T09:00")]}, "en")
    assert window.endswith("Leave at 9 in the morning at the latest, and be back at 1 in the afternoon.")
    two = explain.safest_spoken({**base, "safe_windows": [("2025-02-25T06:00", "2025-02-25T07:00"),
                                                           ("2025-02-25T15:00", "2025-02-25T16:00")]}, "en")
    assert "be back" not in two                         # two windows: no single answer, so none is said
    for lang in ("kn", "ar"):
        said = explain.safest_spoken({**base, "safe_windows": [("2025-02-25T13:00", "2025-02-25T13:00")]}, lang)
        assert "{" not in said and explain.say_time(lang, "2025-02-25T17:00") in said


# ---- "Suggest tomorrow" (owner, 13 Nov 2026): today has one SAFE hour or none -> also say tomorrow's SAFE times
def tight_today(shown, safe=(("2025-02-25T13:00", "2025-02-25T13:00"),)):
    return {"ok": True, "case": "some_safe" if safe else "caution_only", "trip_hours": 4,
            "search_from": "2025-02-25T00:00", "search_to": "2025-02-25T23:00", "safe_windows": list(safe),
            "caution_windows": [] if safe else [("2025-02-25T06:00", "2025-02-25T19:00")], "unsafe_windows": [],
            "shown": shown, "options_checked": 20}


def roomy_tomorrow(shown):
    return {"ok": True, "case": "some_safe", "trip_hours": 4, "search_from": "2025-02-26T00:00",
            "search_to": "2025-02-26T19:00", "safe_windows": [("2025-02-26T06:00", "2025-02-26T10:00")],
            "caution_windows": [], "unsafe_windows": [], "shown": shown, "options_checked": 20}


def test_tomorrow_line_in_chat_and_voice():
    shown = safest()["shown"]
    sres = {**tight_today(shown), "tomorrow": roomy_tomorrow(shown)}
    assert "• Tomorrow: SAFE to leave Wed 26 Feb, 06:00 to 10:00." in explain.safest_bullets(sres, "en").split("\n")
    assert explain.safest_spoken(sres, "en").endswith(
        "Tomorrow there are more SAFE times: from 6 in the morning to 10 in the morning.")
    for lang in ("kn", "ar"):
        assert "{" not in explain.safest_bullets(sres, lang) + explain.safest_spoken(sres, lang)


def fake_search(monkeypatch, today, tomorrow):
    calls = []

    def fake(region, place, start, end, hours, given, mode, map_point=None):
        calls.append(start[:10])
        return today if start[:10] == "2025-02-25" else tomorrow
    monkeypatch.setattr(service, "find_safest_time", fake)
    return calls


def ask_today(monkeypatch, day="today"):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "find_safest_time", place="khor_fakkan", day=day, trip_hours=4, trip_length_given_by_user=True)], []))
    return chat.chat([{"role": "user", "content": "when should I leave?"}], "en", UAE, UAR)


def test_tight_today_also_checks_tomorrow(monkeypatch):
    shown = safest()["shown"]
    calls = fake_search(monkeypatch, tight_today(shown), roomy_tomorrow(shown))
    out = ask_today(monkeypatch)
    assert calls == ["2025-02-25", "2025-02-26"]
    assert "• Tomorrow: SAFE to leave" in out["chat_text"] and "Tomorrow there are more SAFE times" in out["spoken"]


def test_no_safe_time_today_also_checks_tomorrow(monkeypatch):
    shown = safest()["shown"]
    fake_search(monkeypatch, tight_today(shown, safe=()), roomy_tomorrow(shown))
    assert "Tomorrow there are more SAFE times" in ask_today(monkeypatch)["spoken"]


def test_roomy_today_does_not_look_at_tomorrow(monkeypatch):
    shown = safest()["shown"]
    calls = fake_search(monkeypatch, tight_today(shown, safe=(("2025-02-25T06:00", "2025-02-25T09:00"),)),
                        roomy_tomorrow(shown))
    out = ask_today(monkeypatch)
    assert calls == ["2025-02-25"] and "Tomorrow" not in out["chat_text"]


def test_tomorrow_no_better_says_nothing_more(monkeypatch):
    shown = safest()["shown"]
    worse = {**roomy_tomorrow(shown), "case": "caution_only", "safe_windows": [],
             "caution_windows": [("2025-02-26T00:00", "2025-02-26T19:00")]}
    fake_search(monkeypatch, tight_today(shown), worse)
    assert "Tomorrow" not in ask_today(monkeypatch)["chat_text"]


def test_real_safest_answer_has_bullets_in_every_language():
    sres = safest()
    assert sres["ok"]
    for lang in ("en", "kn", "ar"):
        out = explain.safest_bullets(sres, lang)
        assert "{" not in out and out.startswith("• ")


def test_chat_shows_safer_times_as_bullets_without_a_badge(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "find_safest_time", place="dibba_al_hisn", day="today", trip_hours=4, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": "what time do you recommend I leave by?"}], "en", UAE, UAR)
    assert out["chat_text"].startswith("• Dibba") and out["no_badge"] is True


def test_one_trip_answer_keeps_its_badge(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "assess_trip", place="umm_al_quwain", day="today", hour=16, minute=0, back_by_hour=18, back_by_minute=0,
        back_day="same", trip_hours=2, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": "UAQ at 4pm back by 6"}], "en", UAE, UAR)
    assert not out.get("no_badge")


def test_come_back_question_is_answered_first(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "assess_trip", place="umm_al_quwain", day="today", hour=13, minute=0, back_by_hour=-1, back_by_minute=0,
        back_day="same", trip_hours=4, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": "So I leave at 1. And what time do I come back by?"}], "en", UAE, UAR)
    assert out["chat_text"].split("\n")[0] == "• Back by 17:00."
    assert out["spoken"].count("back around 5 in the evening") == 1      # said once, not twice


def test_come_back_question_answered_first_even_as_weather_details(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "weather_details", place="umm_al_quwain", day="today", hour=13, minute=0, trip_hours=4,
        trip_length_given_by_user=True, detail="all")], []))
    out = chat.chat([{"role": "user", "content": "And what time do I come back by?"}], "en", UAE, UAR)
    assert out["spoken"].startswith("You'll be back at 5 in the evening.")


def test_prompt_sends_return_time_questions_to_assess_trip():
    assert "come back" in chat._system_prompt(chat.get_region(UAE), "en", UAR, None, None, None)


def test_a_plain_trip_question_has_no_back_by_line(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "assess_trip", place="umm_al_quwain", day="today", hour=13, minute=0, back_by_hour=-1, back_by_minute=0,
        back_day="same", trip_hours=4, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": "UAQ at 1 for 4 hours"}], "en", UAE, UAR)
    assert not out["chat_text"].startswith("• Back by")


def test_asks_when_back_in_each_language():
    yes = ["what time do I come back by?", "when will I be back?", "When do I return?", "what time do i get back",
           "ಎಷ್ಟು ಗಂಟೆಗೆ ವಾಪಸ್ ಬರುತ್ತೇನೆ?", "متى أرجع؟"]
    no = ["UAQ at 1 for 4 hours", "back by 6, leaving at 2", "is it safe?"]
    assert all(chat.asks_when_back(x) for x in yes)
    assert not any(chat.asks_when_back(x) for x in no)
