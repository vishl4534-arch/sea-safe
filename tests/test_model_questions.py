"""The model words the follow-up question (owner, 13 Nov 2026): code still decides WHAT is missing (harbour,
departure time, trip length) and says back what it understood; the model only phrases the question. Its words
pass the same guard as the rest (no digits, no verdict or safety words), must be one short question, and fall
back to the reviewed template otherwise. No network: the model is scripted."""
from app import chat, explain, llm
from app.config import load_app
from tests.test_ask_details import KA, KA_REPLAY, trip
from tests.test_chat import scripted


def run(monkeypatch, question, worded, tool=None):
    seen = []
    replies = [tool or trip(place="malpe"), {"role": "assistant", "content": worded}]
    monkeypatch.setattr(llm, "complete", scripted(replies, seen))
    return chat.chat([{"role": "user", "content": question}], "en", KA, KA_REPLAY), seen


def test_models_question_follows_what_code_understood(monkeypatch):
    out, seen = run(monkeypatch, "hi, I'm Vish. Can I go out from Malpe?",
                    "When are you heading out, Vish, and how long will you be at sea?")
    assert out["reply"] == "Malpe, got it. When are you heading out, Vish, and how long will you be at sea?"
    assert out["spoken"] == out["reply"]
    ask = seen[1][0][0]["content"]                          # the system message of the wording call
    assert "what time they will leave" in ask and "how many hours" in ask
    assert seen[1][1] == []                                  # no tools: it can only write the question


def test_length_question_keeps_the_departure_said_back_by_code(monkeypatch):
    out, _ = run(monkeypatch, "Malpe at 5 tomorrow morning?", "And how long do you plan to stay out?",
                 trip(day="tomorrow", hour=5))
    assert out["reply"] == "Malpe, leaving Wed 21 May, 05:00, got it. And how long do you plan to stay out?"
    assert out["context"] == {"place": "malpe", "departure": "2025-05-21T05:00"}


def test_numbers_or_safety_words_fall_back_to_the_template(monkeypatch):
    template = explain.t("en", "chat.ask_both", name="Malpe")
    for bad in ("Leaving at 5 then?", "Is it safe for you to go out now?", "What time will you leave",
                "What time will you leave? " * 8, "When will you go?\nAnd for how long?"):
        out, _ = run(monkeypatch, "Can I go out from Malpe?", bad)
        assert out["reply"] == template, bad


def test_model_unavailable_falls_back_to_the_template(monkeypatch):
    def broken(messages, tools):
        if not tools:
            raise llm.LLMUnavailable("down")
        return trip(place="malpe"), "fake (test)"
    monkeypatch.setattr(llm, "complete", broken)
    out = chat.chat([{"role": "user", "content": "Can I go out from Malpe?"}], "en", KA, KA_REPLAY)
    assert out["reply"] == explain.t("en", "chat.ask_both", name="Malpe")


def test_switch_off_uses_only_templates(monkeypatch):
    monkeypatch.setitem(load_app(), "model_questions", False)
    out, seen = run(monkeypatch, "Can I go out from Malpe?", "When are you heading out?")
    assert out["reply"] == explain.t("en", "chat.ask_both", name="Malpe") and len(seen) == 1


def test_said_back_lines_in_every_language():
    for lang in ("en", "kn", "ar"):
        for key in ("chat.got_both", "chat.got_time", "chat.got_length", "chat.got_from"):
            assert explain.t(lang, key) != key
