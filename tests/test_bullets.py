"""Chat answers for one trip are short bullet points; the spoken answer has no "Be careful out there."
(owner request, 13 Nov 2026). Saved replay data, no network."""
import pytest

from app import chat, explain, llm, service
from tests.test_chat import scripted, tool_msg

UAE, UAR = "uae", "uae_2025_02_25"
KA, KAR = "karnataka", "karnataka_2025_05_20"


def check(region, mode, place, dep, hours, given=True):
    return service.assess_trip(region, place, dep, hours, given, mode)


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_caution_is_spoken_without_the_filler_line(lang):
    res = check(UAE, UAR, "umm_al_quwain", "2025-02-25T16:00", 2)
    assert res["verdict"] == "CAUTION"
    said = explain.spoken(res, lang)
    assert explain.t(lang, "say.advice.CAUTION") not in said
    assert explain.t(lang, "say.disclaimer") in said


def test_unsafe_still_says_dont_go():
    res = check(UAE, UAR, "dubai_al_hamriya", "2025-02-25T11:00", 6)
    assert res["verdict"] == "UNSAFE"
    assert explain.t("en", "say.advice.UNSAFE") in explain.spoken(res, "en")
    assert "• Don't take a small boat out." in explain.bullets(res, "en")


def test_bullets_are_short_direct_and_complete():
    res = check(UAE, UAR, "umm_al_quwain", "2025-02-25T16:00", 2)
    b = explain.bullets(res, "en").split("\n")
    assert b[0] == "• Umm Al Quwain: leaving Tue 25 Feb, 16:00, back 18:00 (2 h, your choice)."
    assert any("over the caution line (1.25 m)" in x or "close to the caution line" in x for x in b)
    assert not any("Replay" in x for x in b)                     # no replay labels (owner, 13 Nov 2026)
    assert b[-1] == "• Forecast, not a guarantee: check the official warnings."
    assert all(x.startswith("• ") for x in b) and "Be careful" not in " ".join(b)


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_safe_bullets_in_every_language(lang):
    res = check(UAE, UAR, "dibba_al_hisn", "2025-02-25T06:00", 5)
    out = explain.bullets(res, lang)
    assert res["verdict"] == "SAFE" and "{" not in out and out.count("• ") == 3          # trip, all-clear, disclaimer (no replay line)


def test_chat_returns_bullets_for_one_trip_and_spoken_for_the_voice(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "assess_trip", place="umm_al_quwain", day="today", hour=16, minute=0, back_by_hour=18, back_by_minute=0,
        back_day="same", trip_hours=2, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": "UAQ at 4pm back by 6"}], "en", UAE, UAR)
    # no bullet points any more (owner, 13 Nov 2026): the chat shows the conversational answer the voice says
    assert out["chat_text"] is None and "•" not in out["spoken"] and "Be careful" not in out["spoken"]
    assert out["spoken"].split(",")[0] in ("Okay", "Alright", "Right")


def test_approximate_times_add_the_which_hours_line_to_the_bullets(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "assess_trip", place="umm_al_quwain", day="today", hour=16, minute=10, back_by_hour=18, back_by_minute=30,
        back_day="same", trip_hours=3, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": "UAQ around 4:10, back by 6:30"}], "en", UAE, UAR)
    assert out["chat_text"] is None and out["spoken"].startswith("Your times are not exactly on the hour")


def test_lists_and_talk_have_no_bullets(monkeypatch):
    monkeypatch.setattr(llm, "complete", scripted([{"role": "assistant", "content": "Hi! Where are you heading out from?"}], []))
    assert chat.chat([{"role": "user", "content": "hi"}], "en", KA, KAR).get("chat_text") is None


def test_every_card_view_carries_its_bullets():
    res = check(UAE, UAR, "umm_al_quwain", "2025-02-25T16:00", 2)
    assert explain.render(res, "en")["bullets"] == explain.bullets(res, "en")


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_server_down_message_exists(lang):
    text = explain.t(lang, "error.server_down")
    assert text != "error.server_down" and text != explain.t(lang, "error.generic")
