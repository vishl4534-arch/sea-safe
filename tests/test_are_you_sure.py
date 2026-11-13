"""'Are you sure?' after an answer gets the reviewed answer about how far to trust a forecast, not the same
check repeated word for word (owner's test chat, 13 Nov 2026). The context of the trip is kept."""
import pytest

from app import chat, explain, llm
from app.config import region as get_region
from tests.test_chat import scripted, tool_msg

UAE, UAE_REPLAY = "uae", "uae_2025_02_25"
KA, KA_REPLAY = "karnataka", "karnataka_2025_05_20"
CTX = {"place": "dibba_al_hisn", "departure": "2025-02-25T16:00", "trip_hours": 2, "given": True}


@pytest.mark.parametrize("text", ["Are u sure?", "are you sure", "you sure?", "really?", "can I trust this?",
                                  "is that right?", "ಖಚಿತವಾ?", "ನಿಜವಾ?", "متأكد؟", "أكيد؟"])
def test_doubt_is_recognised(text):
    assert chat.asks_if_sure(text, get_region(UAE))


@pytest.mark.parametrize("text", ["are you sure it's ok at 5?", "really? what about Dibba", "Dibba at 4pm", "why?",
                                  "I'm sure I'll be back by 6", "hello"])
def test_new_questions_are_not_doubt(text):
    assert not chat.asks_if_sure(text, get_region(UAE))


@pytest.mark.parametrize("lang,region,mode,q", [("en", UAE, UAE_REPLAY, "Are u sure?"), ("ar", UAE, UAE_REPLAY, "متأكد؟"),
                                                 ("kn", KA, KA_REPLAY, "ಖಚಿತವಾ?")])
def test_are_you_sure_gets_the_accuracy_answer_even_if_the_model_checks_again(monkeypatch, lang, region, mode, q):
    place = "dibba_al_hisn" if region == UAE else "malpe"
    ctx = {**CTX, "place": place, "departure": "2025-02-25T16:00" if region == UAE else "2025-05-20T16:00"}
    monkeypatch.setattr(llm, "complete", scripted([tool_msg(
        "assess_trip", place=place, day="same", hour=-1, minute=0, back_by_hour=-1, back_by_minute=0, back_day="same",
        trip_hours=2, trip_length_given_by_user=True)], []))
    out = chat.chat([{"role": "user", "content": q}], lang, region, mode, context=ctx)
    assert out["reply"] == explain.faq_text("accuracy", lang, region) and out["cards"] == []
    assert out["context"] == ctx                     # the trip is kept for the next question


def test_prompt_routes_doubt_to_accuracy():
    prompt = chat._system_prompt(get_region(KA), "en", KA_REPLAY, None, None, {})
    assert '"are you sure?"' in prompt and "explain_app(topic=accuracy)" in prompt
