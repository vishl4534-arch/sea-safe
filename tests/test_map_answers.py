"""A tap on the map answers on the map (owner, 13 Nov 2026): the harbour's full answer opens in the sheet for
the time on the slider; nothing is posted in the chat, which stays the fisher's own conversation."""
from pathlib import Path

from app.config import ROOT

JS = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")


def body(name):
    return JS.split(f"function {name}(", 1)[1].split("\n}\n", 1)[0]


def test_map_taps_open_the_sheet_and_post_nothing():
    for fn in ("selectHarbour", "selectPoint"):
        b = body(fn)
        assert "answerOnMap()" in b and "startTrip" not in b and 'setTab("answer")' not in b
    a = body("answerOnMap")
    assert "openSheet(" in a and "addMsg" not in a and "postAnswer" not in a and "showError" not in a


def test_an_assumed_trip_length_never_becomes_the_chats_trip():
    # a map answer may use the standard trip length; the chat still asks the fisher for theirs
    assert "S.context = f.given ?" in body("selectView")
