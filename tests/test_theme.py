"""Settings button and light/dark mode (owner, 13 Nov 2026). The settings button shows on laptops too; it
slides Region, Language and the new Dark/Light choice in. The page starts in the phone's own mode, the choice
is remembered, the switch is animated, and the logo's colours are inverted in light mode."""
import re
from pathlib import Path

import pytest

from app import explain
from app.config import ROOT

STATIC = Path(ROOT) / "static"
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


def block(selector):
    return CSS.split(selector + " {", 1)[1].split("\n}", 1)[0]


def test_every_colour_token_has_a_light_value():
    dark = set(re.findall(r"(--[a-z0-9-]+):", block(":root")))
    light = set(re.findall(r"(--[a-z0-9-]+):", block(':root[data-theme="light"]')))
    colour_tokens = {t for t in dark if not t.startswith(("--r-", "--ease", "--move", "--display", "--body", "--dir"))}
    assert colour_tokens - light == set()


def test_page_starts_in_the_phones_mode_and_remembers_the_choice():
    head = HTML.split("</head>", 1)[0]
    assert "prefers-color-scheme: light" in head and 'localStorage.getItem("theme")' in head
    assert "dataset.theme" in head
    assert 'store.set("theme"' in JS


def test_switch_is_animated_and_respects_reduced_motion():
    fn = JS.split("function setTheme(", 1)[1].split("\n}\n", 1)[0]
    assert "startViewTransition" in fn and "calm()" in fn


def test_logo_is_inverted_in_light_mode():
    assert re.search(r'\[data-theme="light"\][^{]*\.brand-logo[^{]*\{[^}]*filter: invert\(1\)', CSS)


def test_settings_button_shows_on_laptops_and_slides_the_choices_in():
    laptop = CSS.split("@media (min-width: 960px) {", 1)[1]
    assert ".settings-toggle, .tabs { display: none; }" not in laptop
    assert "body.show-settings .pickers" in laptop
    assert 'id="theme"' in HTML


def test_how_we_decide_stays_visible_next_to_the_button():
    header = HTML.split('<header class="top">', 1)[1].split("</header>", 1)[0]
    pickers = header.split('<div id="pickers"', 1)[1].split("\n    </div>", 1)[0]     # the sliding choices
    assert 'id="how-open"' not in pickers and 'id="how-open"' in header
    laptop = CSS.split("@media (min-width: 960px) {", 1)[1]
    assert ".settings-toggle { order: 2; }" in laptop and "#how-open { order: 3; }" in laptop   # the button, then How we decide


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_theme_words_in_every_language(lang):
    for key in ("ui.theme", "ui.theme_dark", "ui.theme_light"):
        assert explain.t(lang, key) != key
