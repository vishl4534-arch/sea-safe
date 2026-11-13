"""Server side of the features added on 13 Nov 2026: Trip understood (1), safer departure times (2),
offline helper (6). The page parts were checked in the browser. No network: saved replay data."""
import pytest
from fastapi.testclient import TestClient

from app import explain, service
from app.main import app

client = TestClient(app)
UAE, UAE_REPLAY = "uae", "uae_2025_02_25"          # replay clock: now 2025-02-25T04:00, window to 2025-02-27T04:00


def test_card_carries_the_trip_exactly_as_checked():
    res = service.assess_trip(UAE, "dubai_al_hamriya", "2025-02-25T11:00", 6, False, UAE_REPLAY)
    f = explain.render(res, "en")["trip_fields"]
    assert f == {"place_id": "dubai_al_hamriya", "departure": "2025-02-25T11:00", "return": "2025-02-25T17:00",
                 "hours": 6, "given": False, "live": False}


@pytest.mark.parametrize("lang", ["en", "ar"])
def test_safer_times_from_the_card_keep_place_and_length_and_say_when_none_is_safe(lang):
    # The page asks from "now" to one hour before the end of the window, for the card's place and length.
    body = {"region": UAE, "place": "dubai_al_hamriya", "search_from_local": "2025-02-25T04:00",
            "search_to_local": "2025-02-27T03:00", "trip_hours": 6, "trip_length_given_by_user": False,
            "mode": UAE_REPLAY, "lang": lang}
    out = client.post("/api/safest", json=body).json()
    assert out["ok"]
    r = out["result"]
    assert r["trip_hours"] == 6 and r["shown"]["place"]["id"] == "dubai_al_hamriya"
    assert r["search_from"] == "2025-02-25T04:00" and r["search_to"] == "2025-02-26T22:00"   # last departure that fits
    if not r["safe_windows"]:
        assert out["line"].startswith(explain.t(lang, "safest.all_unsafe").split("{")[0][:12])
    if r["unsafe_windows"]:
        assert explain.t(lang, "safest.dont_leave").split("{")[0].strip() in out["line"]


def test_offline_helper_is_served_from_the_root_and_never_keeps_answers():
    r = client.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert r.headers.get("cache-control") == "no-cache"
    js = r.text
    assert 'req.method !== "GET"' in js          # weather checks, chat and voice are POST: never kept
    assert "/api/assess" not in js and "/api/chat" not in js


def test_page_learns_the_stale_limit_for_saved_answers():
    assert client.get("/api/config").json()["forecast"]["stale_after_hours"] == 6
