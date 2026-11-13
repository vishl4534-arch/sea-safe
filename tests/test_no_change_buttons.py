"""The card's Change buttons are gone (owner, 13 Nov 2026): the trip is changed by tapping another harbour,
moving the time slider, or saying it in the chat. The "Trip understood" box itself stays."""
from pathlib import Path

from app.config import ROOT

JS = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")
CSS = (Path(ROOT) / "static" / "style.css").read_text(encoding="utf-8")


def test_no_change_buttons_on_the_card():
    assert 'class="link change"' not in JS and 't("ui.change")' not in JS
    for gone in ("function changePlace", "function changeDeparture", "function editTrip", "function askFor"):
        assert gone not in JS
    assert ".change {" not in CSS


def test_trip_understood_box_stays():
    trip = JS.split("function tripHtml(", 1)[1].split("\n}\n", 1)[0]
    for key in ("trip.harbour", "trip.leaves", "trip.back", "trip.length", "trip.said_tag", "trip.assumed_tag"):
        assert key in trip
