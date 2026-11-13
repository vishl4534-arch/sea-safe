"""More kinds of questions (13 Nov 2026): weather details, explaining the app, official warnings and contacts.
All answers are reviewed templates; every number comes from the data, the config or code."""
from datetime import date

import pytest

from app import chat, explain, llm, service
from app.sun import sun_times
from tests.test_chat import scripted, tool_msg

KA, KA_REPLAY, UAE, UAE_REPLAY = "karnataka", "karnataka_2025_05_20", "uae", "uae_2025_02_25"


@pytest.mark.parametrize("lat,lon,d,tz,rise,set_", [
    (13.3476, 74.6994, date(2025, 5, 20), "Asia/Kolkata", "06:04", "18:51"),     # Malpe
    (24.5143, 54.3759, date(2026, 11, 13), "Asia/Dubai", "06:37", "17:37"),      # Abu Dhabi
])
def test_sun_times(lat, lon, d, tz, rise, set_):
    assert sun_times(lat, lon, d, tz) == (rise, set_)


def test_replay_files_carry_the_new_details_and_old_values_are_unchanged():
    r = service.assess_trip(KA, "gangolli", "2025-05-20T14:00", 7, True, KA_REPLAY)
    v = r["hours"][0]["values"]
    assert {"air_temperature", "rain", "sea_temperature"} <= set(v)
    assert r["verdict"] == "UNSAFE" and r["reasons"][0]["value"] == 2.16                # approved replay story intact


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_details_answer_has_data_numbers_verdict_and_disclaimer(lang):
    r = service.assess_trip(UAE, "dibba_al_hisn", "2025-02-25T17:00", 4, True, UAE_REPLAY)
    said = explain.details_spoken(r, lang)
    assert explain.t(lang, f"say.details.verdict.{r['verdict']}") in said and explain.t(lang, "say.disclaimer") in said
    assert explain.say_clock(lang, explain.sun_for(r)[1]) in said                  # sunset spoken from code


def test_one_detail_only():
    r = service.assess_trip(UAE, "dibba_al_hisn", "2025-02-25T17:00", 4, True, UAE_REPLAY)
    sun = explain.details_spoken(r, "en", "sun")
    assert "Sunrise is at 6:43 in the morning and sunset at 6:14 in the evening." in sun
    assert "degrees" not in sun and "safety check" not in sun and explain.t("en", "say.disclaimer") in sun
    rain = explain.details_spoken(r, "en", "rain")
    assert "No rain expected." in rain and "Sunrise" not in rain and "safety check looks safe" in rain


def test_card_has_sunrise_and_sunset():
    r = service.assess_trip(KA, "malpe", "2025-05-20T05:00", 6, False, KA_REPLAY)
    assert explain.render(r, "en")["sun"] == "Sunrise 06:04, sunset 18:51 (local time)."


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
@pytest.mark.parametrize("topic", ["verdicts", "how_decided", "sources", "near_line", "boats", "accuracy",
                                   "data_source", "missing_data", "memory", "limits"])
def test_every_faq_topic_is_reviewed_text_with_config_numbers(lang, topic):
    said = explain.faq_spoken(topic, lang, KA)
    assert said and "{" not in said
    if topic == "how_decided":
        assert all(n in said for n in ("1.25", "37", "40", "1852", "2", "43", "63"))


def test_faq_sources_written_lists_every_source_title():
    text = explain.faq_text("sources", "en", KA)
    assert "FAO/ILO/IMO" in text and "WMO-No. 306" in text and "India Meteorological Department" in text


@pytest.mark.parametrize("region,lang,said", [
    (KA, "en", "In an emergency at sea, call the Indian Coast Guard on 1 5 5 4."),
    (KA, "kn", "ಭಾರತೀಯ ಕರಾವಳಿ ಕಾವಲು ಪಡೆ, 1 5 5 4"),
    (UAE, "en", "In an emergency at sea, call the UAE Coast Guard on 9 9 6."),
    (UAE, "ar", "خفر السواحل، 9 9 6"),
])
def test_approved_coast_guard_numbers(region, lang, said):
    assert said in explain.official_spoken(region, lang)
    text = explain.official_text(region, lang)
    assert ("1554" if region == KA else "996") in text and "https://" in text          # written: number and its source


def test_without_approved_contacts_says_local_emergency_number(monkeypatch):
    region = dict(explain.get_region(KA), emergency_contacts=[])
    monkeypatch.setattr(explain, "get_region", lambda rid: region)
    assert "call your local emergency number" in explain.official_spoken(KA, "en")


def test_faq_answer_has_no_check_intro(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg("explain_app", topic="verdicts")], []))
    out = chat.chat([{"role": "user", "content": "what does caution mean?"}], "en", KA, KA_REPLAY)
    assert out["reply"] == explain.faq_text("verdicts", "en", KA) and out["spoken"] == explain.faq_spoken("verdicts", "en", KA)


@pytest.mark.parametrize("q,tides", [("Can you tell me the tides?", True), ("high tide at Malpe?", True),
                                     ("ಉಬ್ಬರವಿಳಿತ ಹೇಗಿದೆ?", True), ("المد والجزر اليوم؟", True),
                                     ("is it safe at 5?", False), ("what are the current conditions?", False)])
def test_tide_questions_are_recognised(q, tides):
    assert chat.asks_about_tides(q) is tides


@pytest.mark.parametrize("reply", [
    {"role": "assistant", "content": "Which harbour?"},                         # the model gave up
    tool_msg("weather_details", detail="all", place="malpe", day="today", hour=-1, back_by_hour=-1, trip_hours=6,
             trip_length_given_by_user=False),                                  # the model read the weather instead
])
def test_tides_get_the_limits_answer(monkeypatch, reply):
    monkeypatch.setattr(llm, "complete", scripted([reply], []))
    out = chat.chat([{"role": "user", "content": "Can you tell me the tides?"}], "en", KA, KA_REPLAY)
    assert out["spoken"] == explain.faq_spoken("limits", "en", KA) and out["cards"] == []


@pytest.mark.parametrize("q,hour", [
    ("Will it rain at Khor Fakkan this afternoon?", 14), ("is it safe tonight?", 21), ("tomorrow morning?", 5),
    ("ಮಧ್ಯಾಹ್ನ ಮಳೆ ಬರುತ್ತಾ?", 14), ("ನಾಳೆ ರಾತ್ರಿ ಹೋಗಬಹುದಾ?", 21), ("بكرة الصبح؟", 5), ("هل بتمطر العصر؟", 14),
    ("Good morning, is it safe at Malpe?", None), ("مساء الخير", None), ("morning or evening?", None), ("is it safe now?", None),
])
def test_part_of_day_read_by_code(q, hour):
    assert chat.stated_part_of_day(q) == hour


def test_part_of_day_fills_a_missing_hour_only(monkeypatch):
    seen = []
    monkeypatch.setattr(service, "assess_trip", lambda region, place, dep, *a: seen.append(dep) or {"ok": True})
    call = lambda h: {"function": {"name": "assess_trip", "arguments": __import__("json").dumps(dict(
        place="khor_fakkan", day="today", hour=h, back_by_hour=-1, trip_hours=4, trip_length_given_by_user=True))}}
    chat._run_tool(call(-1), UAE, UAE_REPLAY, None, user_text="is it safe this afternoon?")
    chat._run_tool(call(16), UAE, UAE_REPLAY, None, user_text="is it safe this afternoon?")      # the model's hour wins
    asked = chat._run_tool(call(-1), UAE, UAE_REPLAY, None, user_text="is it safe at 3 this afternoon?")  # model's job
    assert seen == ["2025-02-25T14:00", "2025-02-25T16:00"]
    assert asked["result"]["need"] == ["time"]          # the model sent no hour: the app asks, never guesses


def test_table_shows_the_new_details():
    r = service.assess_trip(KA, "malpe", "2025-05-20T05:00", 6, False, KA_REPLAY)
    row = explain.render(r, "en")["hours"][0]["values"]
    assert row["rain"] != "–" and row["air_temperature"] != "–" and row["sea_temperature"] != "–"
