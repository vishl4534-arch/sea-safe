"""The chat never scrolls sideways (owner, 13 Nov 2026): a long example question wraps and stays centred
instead of pushing the chat wider than its column."""
from pathlib import Path

from app.config import ROOT

CSS = (Path(ROOT) / "static" / "style.css").read_text(encoding="utf-8")


def test_example_questions_wrap_and_stay_centred():
    rule = CSS.split(".hello .quick .chip {", 1)[1].split("}", 1)[0]
    assert "white-space: normal" in rule and "text-align: center" in rule and "max-width: 100%" in rule


def test_chat_column_never_scrolls_sideways():
    rule = CSS.split("\n.scroll {", 1)[1].split("}", 1)[0]          # the main rule, not body.show-map's
    assert "overflow-x: hidden" in rule
