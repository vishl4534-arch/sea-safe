"""Kannada and Arabic get the same conversation as English (13 Nov 2026): the words fishers really say are
understood by code, and what is said back is natural in each language. Found by live kn / ar chats."""
import json

import pytest

from app import chat, explain, llm, service
from tests.test_chat import scripted

KA, KA_REPLAY = "karnataka", "karnataka_2025_05_20"
UAE, UAE_REPLAY = "uae", "uae_2025_02_25"


# ---- trip lengths, parts of the day, tides, return time, doubt: read by code -----------------------------
@pytest.mark.parametrize("text,hours", [
    ("6 ಗಂಟೆ ಸಮುದ್ರದಲ್ಲಿ ಇರುತ್ತೇನೆ", 6), ("4 ತಾಸು", 4), ("ಆರು ಗಂಟೆ ಹೊತ್ತು", 6),
    ("خمسة ساعات", 5), ("تلات ساعات", 3), ("ساعة واحدة", 1), ("اثنعش ساعة", 12), ("ساعتين", 2),
])
def test_spoken_trip_lengths(text, hours):
    assert chat.stated_trip_hours(text) == hours


@pytest.mark.parametrize("text", ["ಬೆಳಿಗ್ಗೆ 6 ಗಂಟೆ ಸಮುದ್ರಕ್ಕೆ ಹೋಗಬಹುದಾ?", "ನಾಳೆ 5 ಗಂಟೆಗೆ", "الساعة 5"])
def test_clock_times_are_not_trip_lengths(text):
    assert chat.stated_trip_hours(text) is None


@pytest.mark.parametrize("text,hour", [
    ("ಮಧ್ಯರಾತ್ರಿ ಹೊರಡಬಹುದಾ?", None), ("منتصف الليل", None), ("ಶುಭ ರಾತ್ರಿ", None),   # midnight / good night
    ("ಮುಂಜಾನೆ ಮಲ್ಪೆಯಿಂದ", 5), ("ಸಾಯಂಕಾಲ ಹೋಗಬಹುದಾ?", 17), ("في الصباح", 5), ("ليلاً", 21), ("بعد الظهر", 14),
])
def test_parts_of_the_day(text, hour):
    assert chat.stated_part_of_day(text) == hour


@pytest.mark.parametrize("text,tide", [("كم المدة؟", False), ("من المدينة", False), ("المد والجزر؟", True),
                                       ("ಉಬ್ಬರವಿಳಿತ?", True)])
def test_tides_only_when_asked(text, tide):
    assert chat.asks_about_tides(text) is tide


@pytest.mark.parametrize("text", ["ಎಷ್ಟೊತ್ತಿಗೆ ವಾಪಸ್ ಬರಬೇಕು?", "ಯಾವಾಗ ಹಿಂತಿರುಗಬೇಕು?", "امتى برجع؟", "متى الرجوع؟"])
def test_return_time_questions(text):
    assert chat.asks_when_back(text)


@pytest.mark.parametrize("text", ["ಪಕ್ಕಾನಾ?", "ಗ್ಯಾರಂಟಿನಾ?", "بجد؟", "عن جد؟"])
def test_doubt_in_everyday_words(text):
    assert chat.asks_if_sure(text)


@pytest.mark.parametrize("text", ["ಐದುವರೆಗೆ", "الخامسة والنصف", "5 وثلث"])
def test_half_past_and_twenty_past(text):
    assert chat.stated_minutes(text)


def test_abu_dhabi_written_as_two_words():
    from app.config import region
    assert chat.mentioned_harbours("من أبو ظبي", region(UAE)) == {"abu_dhabi_mina_zayed"}


# ---- Arabic counted nouns ---------------------------------------------------------------------------------
@pytest.mark.parametrize("hours,said", [(1, "ساعة واحدة"), (2, "ساعتين"), (6, "6 ساعات"), (12, "12 ساعة")])
def test_arabic_hours_agree_with_the_number(hours, said):
    assert said in explain.t("ar", "say.trip_assumed", hours=hours)


def test_arabic_decimals_are_left_alone():
    assert explain._ar_counts("1.5 ساعات") == "1.5 ساعات"


# ---- spoken Kannada: speed said as "ಗಂಟೆಗೆ 37 ಕಿಲೋಮೀಟರ್", not "37 ಕಿಲೋಮೀಟರ್ ಪ್ರತಿ ಗಂಟೆಗೆ" -------------------------
def test_kannada_speed_word_order():
    r = service.assess_trip(KA, "gangolli", "2025-05-20T05:00", 6, False, KA_REPLAY)
    said = explain.spoken(r, "kn")
    assert "ಗಂಟೆಗೆ 37 ಕಿಲೋಮೀಟರ್" in said and "ಪ್ರತಿ ಗಂಟೆಗೆ" not in said and "{" not in said


def test_english_spoken_answer_is_unchanged_by_the_amount_slot():
    r = service.assess_trip(KA, "gangolli", "2025-05-20T05:00", 6, False, KA_REPLAY)
    assert "37 kilometres per hour" in explain.spoken(r, "en")


# ---- the follow-up question: spoken times, and no empty departure -----------------------------------------
@pytest.mark.parametrize("lang,place,spoken_time", [("en", "malpe", "on Tuesday at 5 in the evening"),
                                                    ("kn", "malpe", "ಮಂಗಳವಾರ ಸಂಜೆ 5 ಗಂಟೆಗೆ"),
                                                    ("ar", "ajman", "يوم الثلاثاء الساعة 5 مساءً")])
def test_follow_up_question_says_the_time_aloud(lang, place, spoken_time):
    res = {"need": ["length"], "place": place, "departure": "2025-05-20T17:00"}
    assert spoken_time in chat.need_text(res, lang, spoken=True)
    assert "17:00" in chat.need_text(res, lang)                 # the chat bubble keeps the written time


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_best_time_question_never_says_an_empty_departure(lang):
    text = chat.need_text({"need": ["length"], "place": "malpe", "departure": None}, lang)
    assert text == explain.t(lang, "chat.need_length", from_place=explain.t(lang, "place_from.malpe"))


# ---- "when will I be back?" answered by code, never by the model's own time ---------------------------------
def test_return_time_question_without_a_tool_is_checked_by_code(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "ستعود حوالي الساعة 19:00 اليوم."}], []))
    ctx = {"place": "dibba_al_hisn", "departure": "2025-02-25T14:00", "trip_hours": 5, "given": True}
    out = chat.chat([{"role": "user", "content": "امتى برجع؟"}], "ar", UAE, UAE_REPLAY, context=ctx)
    assert "19:00" in out["chat_text"] and out["cards"]          # the time comes from the check
    assert "ستعود حوالي" not in out["reply"]                     # not the model's sentence
    assert out["chat_text"].startswith("• " + explain.t("ar", "chat.b.back_by", back="19:00"))


# ---- small talk: the model is told this language's blocked words ------------------------------------------
@pytest.mark.parametrize("lang,region,word", [("kn", KA, "ಸುರಕ್ಷಿತ"), ("ar", UAE, "آمن")])
def test_prompt_lists_the_blocked_words_of_the_language(monkeypatch, lang, region, word):
    seen = []
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "ok"}], seen))
    chat.chat([{"role": "user", "content": "hi"}], lang, region, KA_REPLAY if lang == "kn" else UAE_REPLAY)
    system = seen[0][0][0]["content"]
    assert word in system.split("never use any of these words")[1]


def test_kannada_and_arabic_have_every_english_key():
    for lang in ("kn", "ar"):
        tr = json.load(open(f"translations/{lang}.json", encoding="utf-8"))
        en = json.load(open("translations/en.json", encoding="utf-8"))
        assert set(en) - set(tr) == set()


# ---- owner's voice test, 13 Nov 2026: no harbour named, and a goodbye blocked by the guard ----------------
@pytest.mark.parametrize("lang,region,mode,q,place", [
    ("en", KA, KA_REPLAY, "Hello. I'm leaving at 2:00 p.m. today. Is that fine?", "mangaluru"),
    ("kn", KA, KA_REPLAY, "ಇವತ್ತು ಮಧ್ಯಾಹ್ನ 2 ಗಂಟೆಗೆ ಹೊರಡುತ್ತೇನೆ, ಹೋಗಬಹುದಾ?", "mangaluru"),
    ("ar", UAE, UAE_REPLAY, "بطلع اليوم الساعة 2 الظهر، تمام؟", "abu_dhabi_mina_zayed")])
def test_a_harbour_the_user_never_named_is_not_used(monkeypatch, lang, region, mode, q, place):
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "assess_trip", "arguments": json.dumps({
            "place": place, "day": "today", "hour": 14, "minute": 0, "back_by_hour": -1, "back_by_minute": 0,
            "back_day": "same", "trip_hours": 6, "trip_length_given_by_user": False})}}]}], []))
    out = chat.chat([{"role": "user", "content": q}], lang, region, mode)
    assert out["cards"] == []                                            # nothing checked for a guessed harbour
    from app.config import region as reg
    assert out["reply"] == chat.ask_place(lang, reg(region), out["context"]["departure"])   # time said back, harbour asked
    assert out["context"]["departure"].endswith("T14:00") and "place" not in out["context"]


def test_the_harbour_named_next_completes_the_trip(monkeypatch):
    ctx = {"departure": "2025-05-20T14:00"}
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "assess_trip", "arguments": json.dumps({
            "place": "malpe", "day": "same", "hour": -1, "minute": 0, "back_by_hour": -1, "back_by_minute": 0,
            "back_day": "same", "trip_hours": 3, "trip_length_given_by_user": True})}}]}], []))
    out = chat.chat([{"role": "user", "content": "from Malpe, 3 hours"}], "en", KA, KA_REPLAY, context=ctx)
    assert out["cards"] and out["cards"][0]["result"]["departure"] == "2025-05-20T14:00"


@pytest.mark.parametrize("lang,q", [("en", "Okay, okay, fine. Thank you. I'll be leaving shortly. Bye."),
                                    ("kn", "ಸರಿ, ಧನ್ಯವಾದ. ಹೋಗಿ ಬರುತ್ತೇನೆ"), ("ar", "تمام، شكراً. مع السلامة")])
def test_a_blocked_goodbye_gets_a_goodbye_not_the_harbour_list(monkeypatch, lang, q):
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "Goodbye! Stay safe out there."}], []))
    region, mode = (UAE, UAE_REPLAY) if lang == "ar" else (KA, KA_REPLAY)
    out = chat.chat([{"role": "user", "content": q}], lang, region, mode, context={"place": "malpe"})
    assert out["reply"] == explain.t(lang, "chat.bye")


def test_other_blocked_small_talk_after_a_check_offers_more_help(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "It looks safe to me!"}], []))
    out = chat.chat([{"role": "user", "content": "nice"}], "en", KA, KA_REPLAY, context={"place": "malpe"})
    assert out["reply"] == explain.t("en", "chat.anything_else")


@pytest.mark.parametrize("lang,region", [("en", KA), ("kn", KA), ("ar", UAE)])
def test_the_voice_asks_which_harbour_without_reading_every_name(lang, region):
    from app.config import region as reg
    r = reg(region)
    for departure in (None, "2025-05-20T14:00"):
        said = chat.ask_place(lang, r, departure, spoken=True)
        assert explain.t(lang, f"place.{r['harbours'][-1]['id']}") not in said      # no list of harbours aloud
        assert explain.t(lang, f"place.{r['harbours'][-1]['id']}") in chat.ask_place(lang, r, departure)  # written: listed


def test_no_tool_and_no_place_speaks_the_short_question(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "It looks safe!"}], []))
    out = chat.chat([{"role": "user", "content": "is it ok?"}], "en", KA, KA_REPLAY)
    assert out["spoken"] == "Which harbour will you leave from?" and "Karwar" in out["reply"]
