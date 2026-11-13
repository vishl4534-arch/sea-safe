"""Regression tests for problems found in the 12 Nov 2026 audit. No network: weather calls are stubbed."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import config, explain, service, weather
from app.assessment import assess
from app.config import load_thresholds

TH = load_thresholds()
CALM = {"wave_height": 0.5, "wind_speed": 10, "wind_gusts": 15, "weather_code": 1, "visibility": 20000}


def no_network(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network disabled in test")
    monkeypatch.setattr(weather, "fetch_points", boom)
    monkeypatch.setattr(weather, "elevation", lambda lat, lon: 0.0)


# ---- 1. the return hour is checked --------------------------------------------------
def test_trip_checks_every_record_from_departure_to_return_inclusive():
    # Gusts are the maximum of the PRECEDING hour, so the record at the return time covers
    # the last hour at sea. A 6-hour trip from 05:00 must read 05:00 ... 11:00 (7 records).
    hours = service._trip({"hours": {}}, datetime(2026, 11, 13, 5), 6, datetime(2026, 11, 15, 5))
    assert [h["time"] for h in hours] == [f"2026-11-13T{h:02d}:00" for h in range(5, 12)]


def test_ajman_replay_trip_now_sees_the_return_hour(monkeypatch):
    no_network(monkeypatch)   # replay data is committed; no fetch needed
    r = service.assess_trip("uae", "ajman", "2025-02-25T06:00", 6, False, "uae_2025_02_25")
    assert r["hours"][-1]["time"] == "2025-02-25T12:00" == r["return"]
    assert r["verdict"] == "CAUTION"    # gusts 42 km/h at 12:00 were missed before


def test_record_exactly_at_window_end_is_inside_the_window():
    end = datetime(2026, 11, 15, 5)
    hours = service._trip({"hours": {}}, end - timedelta(hours=6), 6, end)
    assert hours[-1]["time"] == "2026-11-15T05:00" and hours[-1]["beyond_window"] is False


# ---- 2. exact near-line values ------------------------------------------------------
@pytest.mark.parametrize("field,value", [("wind_speed", 33.3), ("wave_height", 1.125), ("wind_gusts", 36.0)])
def test_value_exactly_on_the_near_line_is_caution(field, value):
    r = assess([{"time": "2026-11-13T05:00", "values": {**CALM, field: value}, "beyond_window": False}], TH)
    assert r["verdict"] == "CAUTION"


def test_visibility_exactly_on_the_near_line_is_caution():
    r = assess([{"time": "2026-11-13T05:00", "values": {**CALM, "visibility": 2037.2}, "beyond_window": False}], TH)
    assert r["verdict"] == "CAUTION"


# ---- 5. switching a harbour off does not break replay --------------------------------
def test_replay_still_works_offline_with_a_harbour_switched_off(monkeypatch):
    no_network(monkeypatch)
    region = config.load_app()["regions"]["karnataka"]
    monkeypatch.setitem(region, "harbours", [h for h in region["harbours"] if h["id"] != "belekeri"])
    r = service.assess_trip("karnataka", "gangolli", "2025-05-20T11:00", 6, False, "karnataka_2025_05_20")
    assert r["verdict"] == "UNSAFE" and r["data"]["fetched_at"] is not None


# ---- 6. chat / voice text carries attribution and the model --------------------------
def test_plain_text_has_attribution_and_model(monkeypatch):
    no_network(monkeypatch)
    r = service.assess_trip("karnataka", "gangolli", "2025-05-20T11:00", 6, False, "karnataka_2025_05_20")
    for lang in ("en", "kn", "ar"):
        out = explain.text(r, lang)
        assert "Weather data by Open-Meteo.com" in out and "meteofrance_wave" in out


# ---- 7. numbers never round onto a line they have not reached -------------------------
def test_wind_is_not_rounded_onto_the_unsafe_line():
    r = assess([{"time": "2026-11-13T05:00", "values": {**CALM, "wind_speed": 42.6}, "beyond_window": False}], TH)
    line = explain.reason_text("en", r["reasons"][0])
    assert "42.6 km/h" in line and "above the caution line (37 km/h)" in line


# ---- 8/9/10. bad inputs get clean errors, never a 500 ----------------------------------
@pytest.fixture
def client(monkeypatch):
    no_network(monkeypatch)
    return TestClient(__import__("app.main", fromlist=["app"]).app, raise_server_exceptions=False)


def test_assess_region_refuses_bad_trip_length(client):
    for hours in (0, -3, 25, 10_000):
        r = client.post("/api/assess_region", json={"region": "uae", "departure_local": "2025-02-25T05:00",
                                                    "trip_hours": hours, "mode": "uae_2025_02_25"})
        assert r.status_code == 200 and r.json() == {"ok": False, "error": "bad_trip_length"}


def test_trip_length_error_is_about_trip_length(client):
    r = client.post("/api/assess", json={"region": "uae", "place": "ajman", "departure_local": "2025-02-25T05:00",
                                         "trip_hours": 0, "trip_length_given_by_user": True, "mode": "uae_2025_02_25"})
    assert r.json()["error"] == "bad_trip_length" and "1 and 24 hours" in r.json()["message"]


@pytest.mark.parametrize("point", [[13.0], [13.0, 74.0, 1.0], [95.0, 74.0], [13.0, 200.0]])
def test_bad_map_point_is_a_clean_error(client, point):
    r = client.post("/api/assess", json={"region": "karnataka", "place": "map_point", "departure_local": "2025-05-20T05:00",
                                         "trip_hours": 6, "trip_length_given_by_user": False,
                                         "mode": "karnataka_2025_05_20", "map_point": point})
    assert r.status_code in (200, 422) and r.status_code != 500
    if r.status_code == 200:
        assert r.json()["ok"] is False


@pytest.mark.parametrize("path", ["/api/how?lang=xx", "/api/how?lang=fr"])
def test_unknown_language_falls_back_not_500(client, path):
    r = client.get(path)
    assert r.status_code == 200 and r.json()["intro"].startswith("The colour")


def test_unknown_language_on_assess_falls_back_to_english(client):
    r = client.post("/api/assess", json={"region": "uae", "place": "ajman", "departure_local": "2025-02-25T05:00",
                                         "trip_hours": 6, "trip_length_given_by_user": False,
                                         "mode": "uae_2025_02_25", "lang": "xx"})
    assert r.status_code == 200 and r.json()["view"]["headline"].startswith("Ajman")


# ---- 11. a switched-off language is never served -------------------------------------
def test_disabled_language_is_not_served(client, monkeypatch):
    cfg = config.load_app()
    monkeypatch.setitem(cfg["regions"]["karnataka"], "languages", ["en"])
    monkeypatch.delitem(cfg["languages"], "kn")
    r = client.post("/api/assess", json={"region": "karnataka", "place": "malpe", "departure_local": "2025-05-20T05:00",
                                         "trip_hours": 6, "trip_length_given_by_user": False,
                                         "mode": "karnataka_2025_05_20", "lang": "kn"})
    assert r.json()["view"]["headline"].startswith("Malpe")      # English, not Kannada
    assert client.get("/api/how?lang=kn").json()["intro"].startswith("The colour")


# ---- the callable service is reachable over HTTP (for the voice agent) -----------------
def test_safest_endpoint(client):
    r = client.post("/api/safest", json={"region": "karnataka", "place": "gangolli",
                                         "search_from_local": "2025-05-20T04:00", "search_to_local": "2025-05-20T23:00",
                                         "trip_hours": 6, "trip_length_given_by_user": False,
                                         "mode": "karnataka_2025_05_20", "lang": "en"})
    body = r.json()
    assert body["ok"] and body["result"]["case"] == "caution_only"
    assert "do not leave" in body["line"] and body["view"]["verdict"] == "CAUTION"


# ---- stale cache at service level -------------------------------------------------------
def test_live_cache_older_than_six_hours_counts_as_missing(monkeypatch, tmp_path):
    no_network(monkeypatch)
    monkeypatch.setattr(weather, "CACHE_DIR", tmp_path)
    region = config.load_app()["regions"]["karnataka"]
    clock = service.clock_info("karnataka", "live")
    dep = clock["default_departure"]
    calm = {(datetime.fromisoformat(dep) + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M"): CALM for i in range(-2, 10)}
    old = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat(timespec="seconds")
    pts = service._batch_points(region)
    blob = {"fetched_at": old, "points": [{"cell": [p[0], p[1]], "hours": calm} for p in pts]}
    (tmp_path / f"live_{weather._key('live', pts)}.json").write_text(json.dumps(blob), encoding="utf-8")
    r = service.assess_trip("karnataka", "malpe", dep, 6, False, "live")
    assert r["verdict"] == "CAUTION" and [x["kind"] for x in r["reasons"]] == ["stale"]
    assert "more than 6 hours old" in explain.text(r, "en")
