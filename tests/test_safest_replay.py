"""'When is the safest time' on recorded replay days: one real example of each case.
Uses the committed data in data/replay, so no network is needed."""
import pytest

from app import explain, service


def safest(region, place, replay, day):
    return service.find_safest_time(region, place, f"{day}T04:00", f"{day}T23:00", 6, False, replay)


def test_all_safe_dibba_25_feb_2025():
    s = safest("uae", "dibba_al_hisn", "uae_2025_02_25", "2025-02-25")
    assert s["case"] == "all_safe"
    assert s["safe_windows"] == [["2025-02-25T04:00", "2025-02-25T23:00"]]
    line = explain.safest_line(s, "en")
    assert line.startswith("SAFE for the whole period: every departure time from Tue 25 Feb, 04:00 to Tue 25 Feb, 23:00")
    assert s["unsafe_windows"] == [] and "do not leave" not in line


def test_mixed_khor_fakkan_25_feb_2025_lists_both_safe_windows():
    s = safest("uae", "khor_fakkan", "uae_2025_02_25", "2025-02-25")
    assert s["case"] == "some_safe"
    assert s["safe_windows"] == [["2025-02-25T04:00", "2025-02-25T06:00"], ["2025-02-25T19:00", "2025-02-25T23:00"]]
    assert s["shown"]["verdict"] == "SAFE" and s["shown"]["departure"] == "2025-02-25T04:00"
    line = explain.safest_line(s, "en")
    assert "Tue 25 Feb, 04:00 to 06:00; Tue 25 Feb, 19:00 to 23:00" in line
    assert "only if the whole trip is SAFE" in line
    assert s["unsafe_windows"] == [] and "do not leave" not in line   # its other hours are CAUTION, not UNSAFE


def test_no_safe_gangolli_20_may_2025_gives_caution_window_not_a_safest_hour():
    s = safest("karnataka", "gangolli", "karnataka_2025_05_20", "2025-05-20")
    assert s["case"] == "caution_only" and s["safe_windows"] == []
    assert s["caution_windows"] == [["2025-05-20T04:00", "2025-05-20T04:00"], ["2025-05-20T20:00", "2025-05-20T23:00"]]
    line = explain.safest_line(s, "en")
    assert line.startswith("There is no SAFE departure time")
    assert "Departure times with CAUTION: Tue 20 May, 04:00; Tue 20 May, 20:00 to 23:00" in line
    assert "best" not in line.lower() and "safest" not in line.lower()
    assert s["unsafe_windows"] == [["2025-05-20T05:00", "2025-05-20T19:00"]]
    assert line.endswith("UNSAFE: do not leave between Tue 20 May, 05:00 and 19:00.")


@pytest.mark.parametrize("place", ["mangaluru", "malpe", "karwar"])
def test_all_unsafe_tauktae_15_may_2021(place):
    s = safest("karnataka", place, "karnataka_tauktae_2021_05_15", "2021-05-15")
    assert s["case"] == "all_unsafe" and s["safe_windows"] == [] and s["caution_windows"] == []
    assert s["shown"]["verdict"] == "UNSAFE"
    assert s["unsafe_windows"] == [["2021-05-15T04:00", "2021-05-15T23:00"]]
    assert explain.safest_line(s, "en").endswith(
        "Every departure time is UNSAFE. UNSAFE: do not leave between Sat 15 May, 04:00 and 23:00.")


@pytest.mark.parametrize("lang", ["kn", "ar"])
def test_every_case_renders_in_other_languages(lang):
    for args in [("uae", "dibba_al_hisn", "uae_2025_02_25", "2025-02-25"),
                 ("uae", "khor_fakkan", "uae_2025_02_25", "2025-02-25"),
                 ("karnataka", "gangolli", "karnataka_2025_05_20", "2025-05-20"),
                 ("karnataka", "malpe", "karnataka_tauktae_2021_05_15", "2021-05-15")]:
        line = explain.safest_line(safest(*args), lang)
        assert line and "{" not in line


def test_mixed_with_unsafe_states_every_unsafe_window():
    sres = {"case": "some_safe", "trip_hours": 6, "search_from": "2026-11-13T04:00", "search_to": "2026-11-13T20:00",
            "safe_windows": [["2026-11-13T04:00", "2026-11-13T05:00"]],
            "caution_windows": [["2026-11-13T06:00", "2026-11-13T07:00"]],
            "unsafe_windows": [["2026-11-13T08:00", "2026-11-13T16:00"], ["2026-11-13T20:00", "2026-11-13T20:00"]]}
    line = explain.safest_line(sres, "en")
    assert line.startswith("SAFE departure times for a 6-hour trip: Fri 13 Nov, 04:00 to 05:00.")
    assert line.endswith("UNSAFE: do not leave between Fri 13 Nov, 08:00 and 16:00, or at Fri 13 Nov, 20:00.")
    for lang in ("kn", "ar"):
        assert "{" not in explain.safest_line(sres, lang)
