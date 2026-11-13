"""The way into the full answer (13 Nov 2026, owner's pick): instead of "See the full answer", a strip with one
small bar per trip hour (coloured by that hour's verdict), the trip's times and "Why CAUTION? ›"."""
from pathlib import Path

import pytest

from app import explain
from app.config import ROOT


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_why_label_in_every_language(lang):
    text = explain.t(lang, "chat.why")
    assert "{verdict}" in text and text != "chat.why"


def test_english_why_label():
    assert explain.t("en", "chat.why").format(verdict="CAUTION") == "Why CAUTION?"


def test_chat_and_voice_mode_use_the_strip():
    app_js = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")
    vm_js = (Path(ROOT) / "static" / "voicemode.js").read_text(encoding="utf-8")
    assert "function answerLink(view, verdict)" in app_js
    assert "answerLink(view, verdict)" in app_js.split("function addMsg", 1)[1]
    assert "answerLink(view, verdict)" in vm_js
