"""Translation files are complete, templates render in every enabled language,
and near-the-line reasons say 'close to', not 'crossed'."""
import json

import pytest

from app import explain
from app.assessment import assess
from app.config import ROOT, load_app, load_thresholds

EN = json.loads((ROOT / "translations" / "en.json").read_text(encoding="utf-8"))
LANGS = list(load_app()["languages"])


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_every_key_exists_in_every_language(lang):
    other = json.loads((ROOT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
    keys = {k for k in EN if not k.startswith("_")}
    assert keys - set(other) == set(), f"{lang} is missing keys"
    assert {k for k in other if not k.startswith("_")} - keys == set(), f"{lang} has extra keys"


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_placeholders_match_english(lang):
    import re
    other = json.loads((ROOT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
    ph = re.compile(r"\{(\w+)\}")
    for k, v in EN.items():
        if not k.startswith("_"):
            assert set(ph.findall(v)) == set(ph.findall(other[k])), f"{lang}:{k}"


def fake_result(trip_values, region="karnataka", stale=False):
    hours = [{"time": f"2026-11-13T{5 + i:02d}:00", "values": v, "beyond_window": False}
             for i, v in enumerate(trip_values)]
    a = assess(hours, load_thresholds(), stale=stale)
    return {"region": region, "place": {"id": "malpe", "kind": "harbour", "lat": 13.3, "lon": 74.7,
                                        "sea_cell": [13.3, 74.7], "sea_cell_km": 6.2, "sea_cell_far": True},
            "departure": "2026-11-13T05:00", "return": "2026-11-13T11:00", "trip_hours": 6,
            "trip_length_given_by_user": False, **a,
            "data": {"fetched_at": "2026-11-12T10:00:00+00:00", "age_minutes": 5, "from_cache": False,
                     "stale": stale, "fetch_error": False, "marine_model": "ecmwf_wam", "weather_model": "best_match"},
            "mode": {"live": True, "replay_id": None, "replay_date": None, "coarse": False}}


CALM = {"wave_height": 0.5, "wind_speed": 10, "wind_gusts": 15, "weather_code": 1, "visibility": 20000}


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("values", [
    [CALM], [{**CALM, "wave_height": 1.15}], [{**CALM, "wave_height": 2.4}], [{**CALM, "weather_code": 95}],
    [{**CALM, "visibility": 1900}], [{**CALM, "wind_speed": None}],
])
def test_renders_in_every_language(lang, values):
    out = explain.text(fake_result(values), lang)
    assert out and "{" not in out


def test_near_line_says_close_not_crossed():
    out = explain.text(fake_result([{**CALM, "wave_height": 1.2}]), "en")
    assert "Waves up to 1.20 m" in out and "close to the caution line (1.25 m)" in out
    assert "above the caution line" not in out


def test_every_answer_shows_trip_length_and_assumption():
    out = explain.text(fake_result([CALM]), "en")
    assert "Trip length: 6 hours (we assumed this" in out


def test_every_answer_has_disclaimer_and_boat_class():
    out = explain.text(fake_result([CALM]), "en")
    assert "forecast, not a guarantee" in out and "small open boats under 10 m" in out


@pytest.mark.parametrize("lang", ["en", "kn", "ar"])
def test_no_template_glues_a_suffix_onto_a_place_name(lang):
    """Place names only appear as whole stored forms ({place} or {from_place}), never followed by a
    case suffix like ' ನಿಂದ', so reviewers check whole words."""
    import re
    tr = json.loads((ROOT / "translations" / f"{lang}.json").read_text(encoding="utf-8"))
    for k, v in tr.items():
        if not k.startswith("_"):
            assert not re.search(r"\{place\}\s*\S*(ನಿಂದ|ಇಂದ|ಗೆ|ಕ್ಕೆ|ದ)\b", v), f"{lang}:{k}"
            # Bare names only where the name stands alone after a colon or at the start ("Malpe, leaving ..."):
            # "Malpe: SAFE", "...: Malpe, 4-hour trip."
            # chat.b.safest.*: "Khor Fakkan, 4-hour trip: ..." (13 Nov 2026), the same bare form as chat.b.trip.
            assert "{place}" not in v or k in ("headline", "ui.usual", "chat.b.trip") \
                or k.startswith("chat.b.safest.") or k in ("push.title", "email.start.subject", "email.start.body"), f"{lang}:{k} should use a stored form"   # push.title: "Khor Fakkan: now CAUTION"
    for pid in [k[6:] for k in tr if k.startswith("place.")]:
        assert f"place_from.{pid}" in tr


def test_map_point_uses_fixed_phrase():
    assert explain.t("en", "place_from.map_point") == "from this point"
    assert explain.t("kn", "place_from.map_point") == "ಈ ಜಾಗದಿಂದ"


def test_far_sea_cell_is_flagged():
    assert "out to sea" in explain.text(fake_result([CALM]), "en")


def test_stale_reason_rendered():
    out = explain.text(fake_result([CALM], stale=True), "en")
    assert "more than 6 hours old" in out and "CAUTION" in out


def test_how_we_decide_lists_every_source_and_own_rules():
    h = explain.how_we_decide("en")
    assert len(h["rows"]) == len(load_thresholds()["parameters"])
    for row in h["rows"]:
        assert row["sources"] and all(s["url"].startswith("http") and s["where"] for s in row["sources"])
    assert any("10%" in r and "ours" in r for r in h["rules"])
