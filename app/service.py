"""The one callable assessment service. The map page, the chat and (later) the voice
agent all call these functions; none of them computes a verdict any other way.

mode is "live" or a replay id from config/app.yaml (e.g. "uae_2025_02_25").
The language model never chooses the mode: the page does.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app import sun, weather, windfield
from app.assessment import assess, departure_windows, SAFE, CAUTION, UNSAFE
from app.config import load_app, load_thresholds, region as get_region

FMT = "%Y-%m-%dT%H:%M"


def _clock(region: dict, mode: str):
    """(now_local, window_end, replay_cfg). Times are naive local datetimes on whole hours."""
    cfg = load_app()
    if mode == "live":
        now = datetime.now(ZoneInfo(region["timezone"])).replace(tzinfo=None, minute=0, second=0, microsecond=0)
        replay = None
    else:
        if mode not in region["replay"]:
            raise ValueError(f"replay {mode} is not enabled for {region['id']}")
        replay = cfg["replays"][mode]
        now = datetime.fromisoformat(replay["date"]).replace(hour=cfg["replay_clock"]["start_hour"])
    return now, now + timedelta(hours=cfg["forecast"]["window_hours"]), replay


def clock_info(region_id: str, mode: str) -> dict:
    region = get_region(region_id)
    now, end, replay = _clock(region, mode)
    cfg = load_app()
    default_dep = now + timedelta(hours=1)
    if replay:
        default_dep = now.replace(hour=cfg["replay_clock"]["default_departure_hour"])
    return {"now": now.strftime(FMT), "window_end": end.strftime(FMT), "default_departure": default_dep.strftime(FMT),
            "replay": ({"id": mode, "date": replay["date"], "coarse": replay["coarse"]} if replay else None)}


def _places(region: dict, place: str, map_point):
    """Resolve the place to (id, kind, lat, lon) or an error code."""
    if place == "map_point":
        if not map_point:
            return None, "no_point_selected"
        try:
            lat, lon = (float(x) for x in map_point)
        except (TypeError, ValueError):
            return None, "bad_point"
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None, "bad_point"
        return {"id": "map_point", "kind": "map_point", "lat": lat, "lon": lon}, None
    for h in region["harbours"]:
        if h["id"] == place:
            return {"id": h["id"], "kind": "harbour", "lat": h["lat"], "lon": h["lon"]}, None
    return None, "unknown_place"


def _batch_points(region: dict) -> list:
    """Every harbour in config, switched on or off, so the batch (and its saved file) never changes
    when a harbour is switched off."""
    return [(h["lat"], h["lon"]) for h in region.get("all_harbours", region["harbours"])]


def _load(region: dict, mode: str, replay, places: list) -> dict:
    """Fetch data for places. Harbour batches in replay mode are saved under data/replay (committed)."""
    pts = [(p["lat"], p["lon"]) for p in places]
    all_harbours = places[0]["kind"] == "harbour"
    if all_harbours:  # always fetch the whole region's harbours together: one cache entry, one request pair
        pts = _batch_points(region)
    data = weather.get_data(pts, region["timezone"], mode, replay,
                            permanent_dir=weather.REPLAY_DIR if all_harbours else None)
    stale_after = load_app()["forecast"]["stale_after_hours"] * 60
    stale = bool(replay is None and data["age_minutes"] is not None and data["age_minutes"] > stale_after)
    by_place = {}
    for p in places:
        idx = pts.index((p["lat"], p["lon"]))
        by_place[p["id"]] = data["points"][idx] if data["points"] else None
    return {"by_place": by_place, "meta": data, "stale": stale}


def _trip(point_data, departure: datetime, trip_hours: int, window_end: datetime) -> list:
    """Every hourly record from departure to return, BOTH included: a 6-hour trip from 05:00 reads
    05:00 ... 11:00. Gusts (and the weather code) are reported for the hour BEFORE each time stamp,
    so the 11:00 record covers the last hour at sea; the 05:00 record adds the hour before leaving,
    which can only make the answer more careful."""
    out = []
    for i in range(trip_hours + 1):
        t = departure + timedelta(hours=i)
        key = t.strftime(FMT)
        beyond = t > window_end
        values = {} if beyond or not point_data else point_data["hours"].get(key, {})
        out.append({"time": key, "values": values, "beyond_window": beyond})
    return out


def _result(region, place, mode, replay, loaded, departure, trip_hours, given, window_end) -> dict:
    pdata = loaded["by_place"][place["id"]]
    meta = loaded["meta"]
    result = assess(_trip(pdata, departure, trip_hours, window_end), load_thresholds(), stale=loaded["stale"])
    cfg = load_app()
    cell = pdata["cell"] if pdata else None
    dist = round(weather.distance_km(place["lat"], place["lon"], *cell), 1) if cell else None
    models = cfg["models"][replay["models"]] if replay else cfg["models"]["live"]
    return {
        "ok": True,
        "region": region["id"],
        "place": {**place, "sea_cell": cell, "sea_cell_km": dist,
                  "sea_cell_far": dist is not None and dist > cfg["forecast"]["big_sea_cell_distance_km"]},
        "departure": departure.strftime(FMT),
        "return": (departure + timedelta(hours=trip_hours)).strftime(FMT),
        "trip_hours": trip_hours,
        "trip_length_given_by_user": given,
        "verdict": result["verdict"],
        "reasons": result["reasons"],
        "hours": result["hours"],
        "summary": result["summary"],
        "data": {"fetched_at": meta["fetched_at"], "age_minutes": meta["age_minutes"], "from_cache": meta["from_cache"],
                 "stale": loaded["stale"], "fetch_error": bool(meta["error"]),
                 "marine_model": models["marine_model"], "weather_model": models["weather_model"]},
        "mode": {"live": replay is None, "replay_id": None if replay is None else mode,
                 "replay_date": replay["date"] if replay else None, "coarse": bool(replay and replay["coarse"])},
    }


def _parse_time(s: str):
    """A local whole-hour time ("2026-11-13T05:00", seconds optional). A time with minutes is refused
    (None), never cut to the hour: the checks read whole hourly records only (audit 13 Nov 2026)."""
    try:
        if not isinstance(s, str) or len(s) not in (16, 19):
            return None
        t = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S" if len(s) == 19 else "%Y-%m-%dT%H:%M")
        return t if t.minute == 0 and t.second == 0 else None
    except (ValueError, TypeError):
        return None


def _check_point(place: dict):
    """Refuse clicks on land. None if fine, else an error code. If the elevation service cannot be
    reached the click is accepted; the sea-cell distance check below still applies."""
    elev = weather.elevation(place["lat"], place["lon"])
    return "on_land" if elev is not None and elev > 0 else None


def _too_far(res: dict):
    """A map point whose nearest wave-model sea cell is too far away is refused."""
    km = res["place"]["sea_cell_km"]
    if res["place"]["kind"] == "map_point" and km is not None and km > load_app()["forecast"]["max_sea_cell_distance_km"]:
        return {"ok": False, "error": "too_far_from_sea_data", "sea_cell_km": km}
    return None


def _trip_length_ok(trip_hours) -> bool:
    try:
        return 1 <= int(trip_hours) <= load_app()["trip"]["max_hours"]
    except (TypeError, ValueError):
        return False


def assess_trip(region_id: str, place: str, departure_local: str, trip_hours: int,
                trip_length_given_by_user: bool, mode: str = "live", map_point=None) -> dict:
    region = get_region(region_id)
    now, window_end, replay = _clock(region, mode)
    p, err = _places(region, place, map_point)
    if err:
        return {"ok": False, "error": err}
    dep = _parse_time(departure_local)
    if dep is None:
        return {"ok": False, "error": "bad_time"}
    if not _trip_length_ok(trip_hours):
        return {"ok": False, "error": "bad_trip_length"}
    if dep < now:
        return {"ok": False, "error": "past_time", "now": now.strftime(FMT)}
    if dep >= window_end:
        return {"ok": False, "error": "outside_window", "window_end": window_end.strftime(FMT)}
    if p["kind"] == "map_point":
        err = _check_point(p)
        if err:
            return {"ok": False, "error": err}
    loaded = _load(region, mode, replay, [p])
    res = _result(region, p, mode, replay, loaded, dep, int(trip_hours), bool(trip_length_given_by_user), window_end)
    return _too_far(res) or res


def assess_region(region_id: str, departure_local: str, trip_hours: int, mode: str = "live") -> dict:
    """Verdict for every harbour at one departure (for the map pins)."""
    region = get_region(region_id)
    now, window_end, replay = _clock(region, mode)
    dep = _parse_time(departure_local)
    if dep is None or dep < now or dep >= window_end:
        return {"ok": False, "error": "outside_window"}
    if not _trip_length_ok(trip_hours):
        return {"ok": False, "error": "bad_trip_length"}
    places = [{"id": h["id"], "kind": "harbour", "lat": h["lat"], "lon": h["lon"]} for h in region["harbours"]]
    if not places:
        return {"ok": True, "harbours": {}}
    loaded = _load(region, mode, replay, places)
    return {"ok": True, "harbours": {p["id"]: _result(region, p, mode, replay, loaded, dep, int(trip_hours), True,
                                                      window_end) for p in places}}


def region_timeline(region_id: str, trip_hours: int, mode: str = "live") -> dict:
    """The trip verdict for every harbour at every whole departure hour of the window, for the time
    slider on the map. It is assess_region asked once per hour: the same data, the same rules.
    Also the sunrise and sunset of each day at the middle of the map, to shade night and day."""
    region = get_region(region_id)
    now, window_end, replay = _clock(region, mode)
    if not _trip_length_ok(trip_hours):
        return {"ok": False, "error": "bad_trip_length"}
    departures = []
    t = now
    while t < window_end:
        departures.append(t)
        t += timedelta(hours=1)
    places = [{"id": h["id"], "kind": "harbour", "lat": h["lat"], "lon": h["lon"]} for h in region["harbours"]]
    harbours = {}
    if places:
        loaded = _load(region, mode, replay, places)
        harbours = {p["id"]: [_result(region, p, mode, replay, loaded, dep, int(trip_hours), True, window_end)["verdict"]
                              for dep in departures] for p in places}
    lat, lon = region["map"]["center"]
    days = sorted({d.date() for d in departures} | {window_end.date()})
    sun_by_day = {d.isoformat(): sun.sun_times(lat, lon, d, region["timezone"]) for d in days}
    return {"ok": True, "hours": [d.strftime(FMT) for d in departures], "window_end": window_end.strftime(FMT),
            "trip_hours": int(trip_hours), "harbours": harbours, "sun": sun_by_day}


def wind_picture(region_id: str, mode: str = "live") -> dict:
    """Wind on a grid for the moving streaks on the map. Display only; see app/windfield.py."""
    region = get_region(region_id)
    now, window_end, replay = _clock(region, mode)
    return windfield.wind_field(region, mode, replay, now, window_end)


def safe_hours(sres: dict) -> int:
    """How many whole departure hours of a safest-time answer are SAFE (0 when none)."""
    if not sres.get("ok"):
        return 0
    return sum(int((datetime.fromisoformat(b[:16]) - datetime.fromisoformat(a[:16])).total_seconds() // 3600) + 1
               for a, b in sres.get("safe_windows", []))


def find_safest_time(region_id: str, place: str, search_from_local: str, search_to_local: str, trip_hours: int,
                     trip_length_given_by_user: bool, mode: str = "live", map_point=None) -> dict:
    """Check every whole departure hour in the range whose trip fits in the window, and answer with
    windows of departures, never a single 'best' hour. A departure is SAFE only if its whole trip is SAFE.
    Cases: all_safe, some_safe (SAFE windows), caution_only (no SAFE; CAUTION windows), all_unsafe."""
    region = get_region(region_id)
    now, window_end, replay = _clock(region, mode)
    p, err = _places(region, place, map_point)
    if err:
        return {"ok": False, "error": err}
    start, end = _parse_time(search_from_local), _parse_time(search_to_local)
    if start is None or end is None:
        return {"ok": False, "error": "bad_time"}
    if not _trip_length_ok(trip_hours):
        return {"ok": False, "error": "bad_trip_length"}
    start = max(start, now)
    last_dep = min(end, window_end - timedelta(hours=int(trip_hours)))
    if last_dep < start:
        return {"ok": False, "error": "no_options_in_window", "window_end": window_end.strftime(FMT)}
    if p["kind"] == "map_point":
        err = _check_point(p)
        if err:
            return {"ok": False, "error": err}
    loaded = _load(region, mode, replay, [p])
    far = _too_far(_result(region, p, mode, replay, loaded, start, int(trip_hours), True, window_end))
    if far:
        return far
    results, t = [], start
    while t <= last_dep:
        results.append(_result(region, p, mode, replay, loaded, t, int(trip_hours),
                               bool(trip_length_given_by_user), window_end))
        t += timedelta(hours=1)
    ans = departure_windows([{"departure": r["departure"], "verdict": r["verdict"]} for r in results])
    # The card shows one example trip so the reasons are visible: the first SAFE departure if there is
    # one, else the first CAUTION departure, else the first departure. It is never called "safest".
    first = {v: next((r for r in results if r["verdict"] == v), None) for v in (SAFE, CAUTION)}
    shown = first[SAFE] or first[CAUTION] or results[0]
    return {"ok": True, "case": ans["case"], "safe_windows": ans["windows"][SAFE],
            "caution_windows": ans["windows"][CAUTION], "unsafe_windows": ans["windows"][UNSAFE],
            "shown": shown, "trip_hours": int(trip_hours),
            "options_checked": len(results), "search_from": start.strftime(FMT), "search_to": last_dep.strftime(FMT)}
