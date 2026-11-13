"""The pictures on the page (gauges, hour bars, the time slider, the wind streaks) only show numbers
and verdicts the verdict code already made. These tests hold that line. No network is needed:
the replay tests use the committed data in data/replay."""
from pathlib import Path

from app import explain, service, windfield
from app.config import ROOT
from tests.test_text import CALM, fake_result


def gauges(values, **kw):
    return {g["param"]: g for g in explain.render(fake_result(values, **kw), "en")["gauges"]}


def test_one_gauge_per_verdict_parameter_with_the_approved_lines():
    g = gauges([CALM])
    assert list(g) == ["wave_height", "wind_speed", "wind_gusts", "thunderstorm", "visibility"]
    assert (g["wave_height"]["caution"], g["wave_height"]["unsafe"], g["wave_height"]["near"]) == (1.25, 2.0, 1.125)
    assert (g["wind_speed"]["caution"], g["wind_speed"]["unsafe"], g["wind_speed"]["near"]) == (37, 43, 33.3)
    assert (g["wind_gusts"]["caution"], g["wind_gusts"]["unsafe"], g["wind_gusts"]["near"]) == (40, 63, 36.0)
    assert g["visibility"]["caution"] == 1852 and g["visibility"]["unsafe"] is None
    assert g["wave_height"]["text"] == "0.50 m" and all(x["level"] == "SAFE" for x in g.values())


def test_gauge_level_is_the_verdict_codes_level_for_that_parameter():
    assert gauges([{**CALM, "wave_height": 1.2}])["wave_height"]["level"] == "CAUTION"      # near the line
    assert gauges([{**CALM, "wave_height": 2.0}])["wave_height"]["level"] == "UNSAFE"       # at the limit
    assert gauges([{**CALM, "weather_code": 95}])["thunderstorm"]["level"] == "CAUTION"
    assert gauges([{**CALM, "visibility": 1900}])["visibility"]["level"] == "CAUTION"
    missing = gauges([{**CALM, "wind_speed": None}])["wind_speed"]
    assert missing["level"] == "CAUTION" and missing["text"] == "–" and missing["value"] is None


def test_gauge_shows_the_worst_hour_of_the_trip():
    g = gauges([CALM, {**CALM, "wind_gusts": 41.5}, CALM])
    assert g["wind_gusts"]["text"] == "41.5 km/h" and g["wind_gusts"]["level"] == "CAUTION"


def test_hour_bar_height_is_worst_value_over_its_caution_line():
    view = explain.render(fake_result([CALM, {**CALM, "wave_height": 1.25}, {**CALM, "visibility": 926}]), "en")
    assert [h["closeness"] for h in view["hours"]] == [0.4, 1.0, 2.0]      # 0.5/1.25; on the line; 1852/926
    assert explain._closeness({}) is None and explain._closeness({"weather_code": 95}) is None


def test_timeline_is_assess_region_asked_once_per_hour():
    tl = service.region_timeline("uae", 6, "uae_2025_02_25")
    assert tl["ok"] and len(tl["hours"]) == 48 and tl["hours"][0] == "2025-02-25T04:00"
    for i in (0, 6, 15, 30, 47):
        one = service.assess_region("uae", tl["hours"][i], 6, "uae_2025_02_25")
        assert {k: v["verdict"] for k, v in one["harbours"].items()} == {k: row[i] for k, row in tl["harbours"].items()}
    assert set(tl["sun"]) == {"2025-02-25", "2025-02-26", "2025-02-27"}
    assert service.region_timeline("uae", 99, "uae_2025_02_25") == {"ok": False, "error": "bad_trip_length"}


def test_wind_direction_is_where_the_wind_comes_from():
    assert windfield.to_uv(10, 0) == (-0.0, -10.0)            # from the north: the air moves south
    assert windfield.to_uv(10, 90) == (-10.0, -0.0)           # from the east: the air moves west
    assert windfield.to_uv(10, 180)[1] == 10.0                # from the south: the air moves north
    assert windfield.to_uv(None, 90) == (None, None)


def test_wind_grid_runs_south_to_north_and_west_to_east():
    pts, nx, ny = windfield.grid_points({"west": 71.5, "south": 11.5, "east": 76.5, "north": 16.5}, 0.5)
    assert (nx, ny, len(pts)) == (11, 11, 121)
    assert pts[0] == (11.5, 71.5) and pts[1] == (11.5, 72.0) and pts[11] == (12.0, 71.5) and pts[-1] == (16.5, 76.5)


def test_the_verdict_code_never_reads_the_wind_picture():
    source = (Path(ROOT) / "app" / "assessment.py").read_text(encoding="utf-8")
    assert "windfield" not in source and "wind_picture" not in source


def test_wind_streaks_change_colour_at_the_verdicts_wind_lines():
    from app.main import config
    assert config()["wind_picture"] == {"enabled": True, "near": 33.3, "caution": 37, "unsafe": 43}
