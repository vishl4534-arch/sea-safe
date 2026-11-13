"""Watch this trip (owner, 13 Nov 2026). The first version only rechecked while the page stayed open, so it was
removed: a fisher at sea could think they were watched when they were not. It is back as a server watch with phone
notifications (tests/test_watch_server.py). This file keeps the page-open version from coming back."""
from pathlib import Path

from app.config import ROOT

JS = (Path(ROOT) / "static" / "app.js").read_text(encoding="utf-8")


def test_no_rechecks_from_an_open_page():
    for gone in ("watchTick", "WATCH_EVERY", "setInterval(watch"):
        assert gone not in JS, gone


def test_watch_runs_on_the_server_and_share_stays():
    assert "/api/watch" in JS and "pushManager.subscribe" in JS
    assert 'data-act="share"' in JS and "function shareTrip" in JS
