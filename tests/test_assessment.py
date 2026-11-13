"""Proves every threshold in config/thresholds.yaml actually fires, including
missing and stale data. Uses the real config file, so a changed value is tested."""
import pytest

from app.assessment import assess, departure_windows, SAFE, CAUTION, UNSAFE
from app.config import load_thresholds

TH = load_thresholds()
P = TH["parameters"]
M = TH["near_line_margin"]

CALM = {"wave_height": 0.5, "wind_speed": 10, "wind_gusts": 15, "weather_code": 1, "visibility": 20000}


def hours(*overrides, start=5):
    """One trip hour per override dict, starting at 05:00."""
    return [{"time": f"2026-11-13T{start + i:02d}:00", "values": {**CALM, **o}, "beyond_window": False}
            for i, o in enumerate(overrides)]


def one(**override):
    return assess(hours(override), TH)


def kinds(result):
    return {(r["param"], r["kind"]) for r in result["reasons"]}


def test_calm_is_safe():
    r = assess(hours({}, {}, {}), TH)
    assert r["verdict"] == SAFE
    assert r["reasons"] == []


# ---- "above" parameters: wave height, wind speed, wind gusts -------------------
ABOVE = ["wave_height", "wind_speed", "wind_gusts"]


@pytest.mark.parametrize("param", ABOVE)
def test_just_below_near_line_is_safe(param):
    c = P[param]["caution"]["value"]
    r = one(**{param: round(c * (1 - M), 6) - 0.01})
    assert r["verdict"] == SAFE


@pytest.mark.parametrize("param", ABOVE)
def test_within_margin_is_caution_marked_near(param):
    c = P[param]["caution"]["value"]
    r = one(**{param: round(c * (1 - M), 6)})
    assert r["verdict"] == CAUTION
    assert (param, "near") in kinds(r)
    assert (param, "caution") not in kinds(r)   # close to the line, not crossed


@pytest.mark.parametrize("param", ABOVE)
def test_at_caution_line_is_caution(param):
    c = P[param]["caution"]["value"]
    r = one(**{param: c})
    assert r["verdict"] == CAUTION
    assert (param, "caution") in kinds(r)


@pytest.mark.parametrize("param", ABOVE)
def test_just_below_unsafe_line_is_caution(param):
    u = P[param]["unsafe"]["value"]
    r = one(**{param: u - 0.01})
    assert r["verdict"] == CAUTION


@pytest.mark.parametrize("param", ABOVE)
def test_at_unsafe_line_is_unsafe(param):
    u = P[param]["unsafe"]["value"]
    r = one(**{param: u})
    assert r["verdict"] == UNSAFE
    reason = [x for x in r["reasons"] if x["param"] == param][0]
    assert reason["kind"] == "unsafe" and reason["threshold"] == u and reason["value"] == u


def test_approved_values_are_the_ones_tested():
    # Guards against someone editing the config without noticing the tests.
    assert P["wave_height"]["caution"]["value"] == 1.25 and P["wave_height"]["unsafe"]["value"] == 2.0
    assert P["wind_speed"]["caution"]["value"] == 37 and P["wind_speed"]["unsafe"]["value"] == 43
    assert P["wind_gusts"]["caution"]["value"] == 40 and P["wind_gusts"]["unsafe"]["value"] == 63
    assert P["visibility"]["caution"]["value"] == 1852
    assert P["thunderstorm"]["codes"] == [95, 96, 99]
    assert M == 0.10


# ---- thunderstorm (codes) ------------------------------------------------------
@pytest.mark.parametrize("code", [95, 96, 99])
def test_thunderstorm_codes_give_caution_only(code):
    r = one(weather_code=code)
    assert r["verdict"] == CAUTION
    assert ("thunderstorm", "thunderstorm") in kinds(r)


@pytest.mark.parametrize("code", [0, 3, 61, 80, 94])
def test_other_weather_codes_do_not_trigger(code):
    assert one(weather_code=code)["verdict"] == SAFE


# ---- visibility ("below": lower is worse) --------------------------------------
def test_visibility_at_line_is_caution():
    r = one(visibility=1852)
    assert r["verdict"] == CAUTION and ("visibility", "caution") in kinds(r)


def test_visibility_within_margin_is_near():
    r = one(visibility=round(1852 * (1 + M), 6))
    assert r["verdict"] == CAUTION and ("visibility", "near") in kinds(r)


def test_visibility_just_outside_margin_is_safe():
    assert one(visibility=round(1852 * (1 + M), 6) + 1)["verdict"] == SAFE


def test_visibility_never_unsafe_alone():
    assert one(visibility=10)["verdict"] == CAUTION


# ---- missing, beyond window, stale ---------------------------------------------
@pytest.mark.parametrize("field", ["wave_height", "wind_speed", "wind_gusts", "weather_code", "visibility"])
def test_missing_value_gives_caution_never_safe(field):
    r = assess(hours({}, {field: None}, {}), TH)
    assert r["verdict"] == CAUTION
    missing = [x for x in r["reasons"] if x["kind"] == "missing"]
    assert missing and missing[0]["time"] == "2026-11-13T06:00"


def test_missing_does_not_hide_unsafe():
    r = assess(hours({"wave_height": None}, {"wind_speed": 50}), TH)
    assert r["verdict"] == UNSAFE


def test_hour_beyond_window_gives_caution():
    h = hours({}, {})
    h.append({"time": "2026-11-13T07:00", "values": {}, "beyond_window": True})
    r = assess(h, TH)
    assert r["verdict"] == CAUTION
    assert any(x["kind"] == "beyond_window" for x in r["reasons"])


def test_stale_data_gives_caution_even_when_calm():
    r = assess(hours({}, {}), TH, stale=True)
    assert r["verdict"] == CAUTION
    assert [x["kind"] for x in r["reasons"]] == ["stale"]


def test_stale_data_values_are_not_used():
    r = assess(hours({"wind_speed": 80}), TH, stale=True)
    assert r["verdict"] == CAUTION          # stale values are treated as missing, not trusted


def test_empty_trip_is_caution():
    assert assess([], TH)["verdict"] == CAUTION


# ---- worst hour decides, drivers ------------------------------------------------
def test_worst_hour_decides_and_driver_names_it():
    r = assess(hours({}, {"wave_height": 1.5}, {"wave_height": 2.3}, {}), TH)
    assert r["verdict"] == UNSAFE
    assert r["reasons"] == [{"param": "wave_height", "kind": "unsafe", "value": 2.3,
                             "threshold": 2.0, "time": "2026-11-13T07:00"}]
    assert [h["verdict"] for h in r["hours"]] == [SAFE, CAUTION, UNSAFE, SAFE]


def test_one_reason_per_parameter_unsafe_first():
    r = assess(hours({"wind_speed": 38}, {"wave_height": 2.5}), TH)
    assert r["verdict"] == UNSAFE
    assert [(x["param"], x["kind"]) for x in r["reasons"]] == [("wave_height", "unsafe"), ("wind_speed", "caution")]


def test_near_then_crossed_gives_one_line_with_worst_value():
    # Gangolli case: 1.24 m (close to the line) at 06:00 and 1.74 m (above it) at 09:00 must not
    # read as two contradicting lines. One line: the worst value, its hour, the line it crossed.
    r = assess(hours({}, {"wave_height": 1.24}, {}, {}, {"wave_height": 1.74}), TH)
    waves = [x for x in r["reasons"] if x["param"] == "wave_height"]
    assert waves == [{"param": "wave_height", "kind": "caution", "value": 1.74, "threshold": 1.25,
                      "time": "2026-11-13T09:00"}]


def test_value_beats_missing_for_the_same_parameter():
    r = assess(hours({"wave_height": None}, {"wave_height": 1.5}), TH)
    assert [(x["param"], x["kind"]) for x in r["reasons"]] == [("wave_height", "caution")]


def test_several_caution_reasons_listed_with_worst_value():
    r = assess(hours({"wave_height": 1.3}, {"wave_height": 1.6, "weather_code": 95}), TH)
    assert r["verdict"] == CAUTION
    wave = [x for x in r["reasons"] if x["param"] == "wave_height"][0]
    assert wave["value"] == 1.6 and wave["time"] == "2026-11-13T06:00"
    assert ("thunderstorm", "thunderstorm") in kinds(r)


def test_summary_has_worst_value_per_parameter():
    r = assess(hours({"wind_gusts": 20}, {"wind_gusts": 30}), TH)
    assert r["summary"]["wind_gusts"] == {"value": 30, "time": "2026-11-13T06:00"}
    assert r["summary"]["visibility"]["value"] == 20000


# ---- safest time: departure windows --------------------------------------------
def deps(*verdicts):
    return [{"departure": f"2026-11-13T{4 + i:02d}:00", "verdict": v} for i, v in enumerate(verdicts)]


def test_windows_all_safe():
    w = departure_windows(deps(SAFE, SAFE, SAFE))
    assert w["case"] == "all_safe" and w["windows"][SAFE] == [["2026-11-13T04:00", "2026-11-13T06:00"]]


def test_windows_mixed_gives_every_safe_run():
    w = departure_windows(deps(SAFE, SAFE, CAUTION, UNSAFE, SAFE))
    assert w["case"] == "some_safe"
    assert w["windows"][SAFE] == [["2026-11-13T04:00", "2026-11-13T05:00"], ["2026-11-13T08:00", "2026-11-13T08:00"]]


def test_windows_no_safe_gives_caution_runs_only():
    w = departure_windows(deps(UNSAFE, CAUTION, CAUTION, UNSAFE))
    assert w["case"] == "caution_only" and w["windows"][SAFE] == []
    assert w["windows"][CAUTION] == [["2026-11-13T05:00", "2026-11-13T06:00"]]


def test_windows_all_unsafe():
    w = departure_windows(deps(UNSAFE, UNSAFE))
    assert w["case"] == "all_unsafe" and w["windows"][SAFE] == [] and w["windows"][CAUTION] == []


def test_departure_is_safe_only_if_whole_trip_is_safe():
    # The verdict per departure comes from assess() over the whole trip, so one bad hour late in the
    # trip makes that departure CAUTION even if it starts calm.
    trip = hours({}, {}, {"wave_height": 1.5})
    assert assess(trip, TH)["verdict"] == CAUTION
