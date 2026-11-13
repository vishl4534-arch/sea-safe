"""The assistant offers to watch the trip (owner, 13 Nov 2026): after a live CAUTION or UNSAFE answer it asks
"Want me to watch this trip and email you if the forecast changes?", once per trip. The fisher's yes or no is
read by code; a yes makes it ask which email (offering the one this phone remembers); with the email the server
starts watching, sends the confirmation email, and only then confirms. Any change of verdict is emailed (owner's
choice). No network, no model."""
import pytest

from app import chat, explain, llm, mailer
from app.config import region as get_region

KA = "karnataka"
TRIP = {"place_id": "malpe", "departure": "2026-11-13T17:00", "hours": 3, "given": True, "live": True,
        "key": "malpe|2026-11-13T17:00|3"}


def answer(verdict="CAUTION", live=True, place="malpe"):
    f = {"place_id": place, "departure": "2026-11-13T17:00", "return": "2026-11-13T20:00", "hours": 3,
         "given": True, "live": live}
    return {"reply": "Right, leaving ...", "spoken": "Right, leaving ...", "chat_text": None, "no_badge": False,
            "region": None, "cards": [{"result": {"verdict": verdict}, "view": {"trip_fields": f}}]}


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_caution_or_unsafe_answer_ends_with_the_offer(lang):
    for verdict in ("CAUTION", "UNSAFE"):
        out = answer(verdict)
        chat._offer_watch(out, lang, "live", {})
        line = explain.t(lang, "chat.watch_offer")
        assert out["reply"].endswith(line) and out["spoken"].endswith(line)
        assert out["watch_offer"]["key"] == "malpe|2026-11-13T17:00|3"


@pytest.mark.parametrize("out,mode,page", [
    (answer("SAFE"), "live", {}),                                          # already safe: nothing to wait for
    (answer(), "karnataka_2025_05_20", {}),                                # a replay day cannot be watched
    (answer(live=False), "live", {}),
    (answer(), "live", {"watch_skip": ["malpe|2026-11-13T17:00|3"]}),       # offered once per trip
])
def test_no_offer(out, mode, page):
    chat._offer_watch(out, "en", mode, page)
    assert "watch_offer" not in out and "watch" not in out["reply"]


@pytest.mark.parametrize("text,want", [
    ("yes", "yes"), ("yes please", "yes"), ("sure, go ahead", "yes"), ("ok", "yes"), ("ಹೌದು", "yes"), ("ಸರಿ ಮಾಡಿ", "yes"),
    ("نعم", "yes"), ("ايوه راقب", "yes"), ("me@example.com", "yes"),
    ("no", "no"), ("no thanks", "no"), ("ಬೇಡ", "no"), ("لا شكراً", "no"),
    ("what about tomorrow at 5?", None), ("ok and Gangolli?", None), ("why is it caution though, tell me more please", None),
])
def test_yes_and_no_in_every_language(text, want):
    assert chat.watch_answer(text, get_region(KA)) == want


def no_model(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a: (_ for _ in ()).throw(AssertionError("no model call for yes/no")))
    monkeypatch.setattr(mailer, "available", lambda: True)


@pytest.fixture
def fake_watch(monkeypatch, tmp_path):
    """The real watch store in a temporary folder, a live check that answers CAUTION, and emails recorded."""
    from app import service, watch
    monkeypatch.setattr(watch, "DIR", tmp_path)
    monkeypatch.setattr(service, "assess_trip", lambda *a, **k: {"ok": True, "verdict": "CAUTION", "place": {"id": a[1]},
                                                                 "departure": a[2], "trip_hours": a[3]})
    sent = []
    monkeypatch.setattr(watch, "confirm", lambda email, trip, res: (sent.append((email, trip)), True)[1])
    return {"sent": sent, "watch": watch}


def test_yes_asks_which_email_offering_the_remembered_one(monkeypatch):
    no_model(monkeypatch)
    out = chat.chat([{"role": "user", "content": "yes please"}], "en", KA, "live",
                    page={"watch_offer": TRIP, "watch_email": "fisher@example.com"})
    assert out["reply"] == explain.t("en", "chat.watch_ask_known", email="fisher@example.com")
    assert out["spoken"] == explain.t("en", "say.watch_ask_known")       # the address is not read aloud
    assert out["watch_offer"]["stage"] == "email" and "watching" not in out


def test_yes_without_an_email_asks_for_one_and_keeps_the_offer(monkeypatch):
    no_model(monkeypatch)
    out = chat.chat([{"role": "user", "content": "ಹೌದು"}], "kn", KA, "live", page={"watch_offer": TRIP})
    assert out["reply"] == explain.t("kn", "chat.watch_ask_email") and out["watch_offer"]["key"] == TRIP["key"]
    assert "watching" not in out


def test_yes_to_the_remembered_email_starts_watching_and_confirms(monkeypatch, fake_watch):
    no_model(monkeypatch)
    out = chat.chat([{"role": "user", "content": "yes"}], "en", KA, "live",
                    page={"watch_offer": {**TRIP, "stage": "email"}, "watch_email": "fisher@example.com"})
    assert out["reply"] == explain.t("en", "chat.watch_on", email="fisher@example.com")
    assert out["spoken"] == explain.t("en", "say.watch_on")
    assert out["watching"]["email"] == "fisher@example.com" and out["watching"]["key"] == TRIP["key"]
    stored = fake_watch["watch"].all_watches()
    assert len(stored) == 1 and stored[0]["email"] == "fisher@example.com" and stored[0]["verdict"] == "CAUTION"
    assert stored[0]["trip"]["place"] == "malpe" and stored[0]["subscription"] is None
    assert fake_watch["sent"][0][0] == "fisher@example.com"             # the confirmation email went out


def test_the_typed_email_starts_watching(monkeypatch, fake_watch):
    no_model(monkeypatch)
    out = chat.chat([{"role": "user", "content": "it's ravi.k@gmail.com"}], "en", KA, "live",
                    page={"watch_offer": {**TRIP, "stage": "email"}, "watch_email": "old@example.com"})
    assert out["watching"]["email"] == "ravi.k@gmail.com" and fake_watch["sent"][0][0] == "ravi.k@gmail.com"


def test_a_confirmation_that_cannot_be_sent_means_no_watch(monkeypatch, fake_watch):
    no_model(monkeypatch)
    monkeypatch.setattr(fake_watch["watch"], "confirm", lambda *a: False)
    out = chat.chat([{"role": "user", "content": "x@bad.example"}], "en", KA, "live", page={"watch_offer": TRIP})
    assert out["reply"] == explain.t("en", "chat.watch_mail_failed", email="x@bad.example")
    assert "watching" not in out and fake_watch["watch"].all_watches() == [] and out["watch_offer"]["stage"] == "email"


def test_no_means_no(monkeypatch):
    no_model(monkeypatch)
    out = chat.chat([{"role": "user", "content": "لا"}], "en", KA, "live", page={"watch_offer": TRIP})
    assert out["reply"] == explain.t("en", "chat.watch_no") and "watching" not in out


def test_without_email_on_the_server_it_says_so(monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda *a: (_ for _ in ()).throw(AssertionError("no model call")))
    monkeypatch.setattr(mailer, "available", lambda: False)
    out = chat.chat([{"role": "user", "content": "yes"}], "en", KA, "live",
                    page={"watch_offer": TRIP, "watch_email": "fisher@example.com"})
    assert out["reply"] == explain.t("en", "chat.watch_no_email") and "watching" not in out


def test_another_question_goes_to_the_chat_as_usual(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "complete", lambda m, t: (seen.append(1), ({"role": "assistant", "content": "Hi!"}, "fake"))[1])
    out = chat.chat([{"role": "user", "content": "what about tomorrow at 5?"}], "en", KA, "live", page={"watch_offer": TRIP})
    assert seen and "watching" not in out


@pytest.mark.parametrize("bad", [{"place_id": "nowhere", "departure": "2026-11-13T17:00", "hours": 3},
                                 {"place_id": "malpe", "departure": "soon", "hours": 3},
                                 {"place_id": "malpe", "departure": "2026-11-13T17:00", "hours": 99}, "junk"])
def test_a_bad_offer_from_the_page_is_ignored(bad):
    assert chat._offered_trip({"watch_offer": bad}, get_region(KA)) is None


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_watch_lines_exist_in_every_language(lang):
    for k in ("chat.watch_offer", "chat.watch_on", "say.watch_on", "chat.watch_ask_email", "chat.watch_ask_known",
              "say.watch_ask_known", "chat.watch_no", "chat.watch_no_email", "chat.watch_mail_failed", "say.watch_mail_failed"):
        assert explain.t(lang, k) != k and "{" not in explain.t(lang, k, email="a@b.co")


# ---- owner's test, 13 Nov 2026: a longer yes, and asking again after the offer lapsed -------------------------
@pytest.mark.parametrize("text", ["Yeah, please, uh, email me when the forecast changes.", "sure, watch it and mail me",
                                  "ಹೌದು, ಇಮೇಲ್ ಮಾಡಿ", "ايوه، ارسل لي ايميل إذا تغيّر الجو"])
def test_a_longer_yes_about_email_counts(text):
    assert chat.watch_answer(text, get_region(KA)) == "yes"


@pytest.mark.parametrize("text", ["do you keep my email?", "should I watch out for the wind tonight?",
                                  "is it a nice day, it looks beautiful", "no, don't email me"])
def test_not_a_request_to_be_emailed(text):
    assert chat.watch_answer(text, get_region(KA)) != "yes"


def test_asking_later_starts_the_watch_flow_for_the_trip_being_talked_about(monkeypatch):
    no_model(monkeypatch)
    ctx = {"place": "abu_dhabi_mina_zayed", "departure": "2026-11-13T14:00", "trip_hours": 4, "given": True}
    out = chat.chat([{"role": "user", "content": "Can you still send me the mail?"}], "en", "uae", "live", context=ctx)
    assert out["reply"] == explain.t("en", "chat.watch_ask_email")
    assert out["watch_offer"]["key"] == "abu_dhabi_mina_zayed|2026-11-13T14:00|4" and out["watch_offer"]["stage"] == "email"


def test_asking_with_no_trip_yet_goes_to_the_chat(monkeypatch):
    seen = []
    monkeypatch.setattr(llm, "complete", lambda m, t: (seen.append(1), ({"role": "assistant", "content": "Which harbour?"}, "f"))[1])
    chat.chat([{"role": "user", "content": "can you email me?"}], "en", KA, "live")
    assert seen


@pytest.mark.parametrize("text", ["that one", "same", "yes, that's right", "ಅದೇ", "نفسه"])
def test_choosing_the_remembered_email_in_other_words(text):
    assert chat.watch_answer(text, get_region(KA)) == "yes"


def test_the_remembered_email_question_reads_as_the_owner_asked():
    assert explain.t("en", "chat.watch_ask_known", email="a@b.co") == \
        "Sure. Which email should I send the updates to: a@b.co? If not, type another email below."
