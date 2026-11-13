"""The owner removed "Replay a past day" from the page (13 Nov 2026): a fisher would never use it. The page
always uses the live forecast. The replay days stay in config/app.yaml for the tests."""
from pathlib import Path

from app.config import ROOT


def test_page_has_no_replay_picker():
    html = (Path(ROOT) / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="mode"' not in html and "mode-label" not in html


def test_no_replay_labels_left():
    """Owner (13 Nov 2026): remove the remaining replay labels too."""
    from app import explain, service
    for lang in ("en", "kn", "ar"):
        for key in ("say.replay", "chat.b.replay", "data.line_replay", "ui.replay", "ui.mode"):
            assert explain.t(lang, key) == key
    res = service.assess_trip("uae", "dibba_al_hisn", "2025-02-25T06:00", 4, True, "uae_2025_02_25")
    assert "Replay" not in explain.bullets(res, "en") and "replay" not in explain.spoken(res, "en")
    assert explain.render(res, "en")["data_line"].startswith("Forecast for")
    assert not hasattr(explain, "say_replay")
    js = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")
    assert "ui.replay" not in js and 'menu($("mode")' not in js


def test_bot_no_longer_explains_replay():
    from app import chat, explain, tools
    assert "replay" not in tools.FAQ_TOPICS
    prompt = chat._system_prompt(chat.get_region("uae"), "en", "live", None, None, None)
    assert "what replay is" not in prompt
    for lang in ("en", "kn", "ar"):
        assert explain.t(lang, "faq.replay") == "faq.replay"          # the answer text is gone


def test_replay_banner_is_gone():
    from app import explain, service
    for lang in ("en", "kn", "ar"):
        for key in ("replay.banner", "replay.coarse", "replay.choose"):
            assert explain.t(lang, key) == key
    res = service.assess_trip("uae", "dibba_al_hisn", "2025-02-25T06:00", 4, True, "uae_2025_02_25")
    view = explain.render(res, "en")
    assert "replay_banner" not in view and "coarse_note" not in view
    page = "".join((Path(ROOT) / "static" / f).read_text(encoding="utf-8") for f in ("index.html", "app.js", "style.css"))
    assert "replay-tape" not in page and "replay_banner" not in page


def test_page_always_starts_live():
    js = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")
    assert 'S.mode = "live"' in js and 'store.set("mode"' not in js
