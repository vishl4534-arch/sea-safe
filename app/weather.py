"""Open-Meteo data: fetch, cache, replay files.

For a list of points we make two calls:
  1. Marine API (waves) at the points. It answers from the nearest SEA cell of the wave
     model and tells us where that cell is.
  2. Forecast API (wind, gusts, weather code, visibility) at those sea cells.
Both are merged into one record per local hour, keyed by our field names.
"""
import hashlib
import json
import logging
import math
import os
import threading
from datetime import date, datetime, timedelta, timezone

from app import net
from app.config import ROOT, load_app

log = logging.getLogger("seasafe.weather")

MARINE_VARS = {"wave_height": "wave_height", "wave_period": "wave_period", "wave_direction": "wave_direction"}
WEATHER_VARS = {"wind_speed_10m": "wind_speed", "wind_gusts_10m": "wind_gusts",
                "wind_direction_10m": "wind_direction", "weather_code": "weather_code", "visibility": "visibility",
                # details only, never used for the verdict:
                "temperature_2m": "air_temperature", "precipitation": "rain"}
# Sea temperature is only in Open-Meteo's default marine model, not in the wave models: one extra call.
SEA_TEMP_VARS = {"sea_surface_temperature": "sea_temperature"}

CACHE_DIR = ROOT / "data" / "cache"
REPLAY_DIR = ROOT / "data" / "replay"


def distance_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance, good enough for 'how far is the sea cell'."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _get(url: str, params: dict) -> list:
    r = net.CLIENT.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else [data]


def _time_params(timezone_name: str, replay_date: str | None) -> dict:
    p = {"timezone": timezone_name}
    if replay_date:
        d = date.fromisoformat(replay_date)
        p.update(start_date=d.isoformat(), end_date=(d + timedelta(days=2)).isoformat())
    else:
        p["forecast_days"] = 4  # covers "now + 48 h" whatever the time of day
    return p


def fetch_points(points: list, models: dict, timezone_name: str, replay_date: str | None = None) -> list:
    """points: [(lat, lon)]. Returns one dict per point:
    {"cell": [lat, lon], "hours": {"2026-11-13T05:00": {field: value}}}"""
    tp = _time_params(timezone_name, replay_date)
    marine = _get(models["marine_api"], {
        "latitude": ",".join(f"{p[0]:.4f}" for p in points), "longitude": ",".join(f"{p[1]:.4f}" for p in points),
        "hourly": ",".join(MARINE_VARS), "models": models["marine_model"], **tp})
    cells = [(m["latitude"], m["longitude"]) for m in marine]
    wparams = {"latitude": ",".join(f"{c[0]:.4f}" for c in cells), "longitude": ",".join(f"{c[1]:.4f}" for c in cells),
               "hourly": ",".join(WEATHER_VARS), "wind_speed_unit": "kmh", **tp}
    if models.get("weather_model") and models["weather_model"] != "best_match":
        wparams["models"] = models["weather_model"]
    weather = _get(models["weather_api"], wparams)
    sea = _sea_temperature(models["marine_api"], cells, tp)

    out = []
    for m, w, st, cell in zip(marine, weather, sea, cells):
        hours = {}
        for src, names in ((m, MARINE_VARS), (w, WEATHER_VARS), (st, SEA_TEMP_VARS)):
            h = src.get("hourly", {})
            for i, t in enumerate(h.get("time", [])):
                rec = hours.setdefault(t, {})
                for api_name, field in names.items():
                    vals = h.get(api_name)
                    rec[field] = vals[i] if vals and i < len(vals) else None
        out.append({"cell": [cell[0], cell[1]], "hours": hours})
    return out


def _sea_temperature(api: str, cells: list, tp: dict) -> list:
    """Sea temperature at the wave cells. A detail only: if it fails, the check goes on without it."""
    try:
        return _get(api, {"latitude": ",".join(f"{c[0]:.4f}" for c in cells),
                          "longitude": ",".join(f"{c[1]:.4f}" for c in cells),
                          "hourly": ",".join(SEA_TEMP_VARS), **tp})
    except Exception as e:                                  # noqa: BLE001
        log.warning("sea temperature not available: %s", e)
        return [{} for _ in cells]


def _key(kind: str, points: list) -> str:
    # 3 decimals (about 100 m): two map taps share data only if they are practically the same point
    raw = kind + "|" + ";".join(f"{p[0]:.3f},{p[1]:.3f}" for p in points)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


_locks: dict = {}
_locks_guard = threading.Lock()


def _lock_for(path) -> threading.Lock:
    """One lock per data file, so two requests for the same data (e.g. pins and card on page load)
    make one fetch, not two that write the same file at once."""
    with _locks_guard:
        return _locks.setdefault(str(path), threading.Lock())


def _read(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _write(path, blob) -> None:
    """Write to a temporary file, then rename: a reader never sees a half-written file."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(blob), encoding="utf-8")
    os.replace(tmp, path)


def get_data(points: list, timezone_name: str, mode: str, replay: dict | None = None, permanent_dir=None) -> dict:
    """Returns {"points": [...] or None, "fetched_at": iso or None, "age_minutes", "from_cache", "error"}.
    Live: reuse cache younger than live_cache_minutes; on fetch failure fall back to any cache.
    Replay: archived data never changes, so a saved file is used for ever (works offline)."""
    cfg = load_app()
    models = cfg["models"][replay["models"]] if replay else cfg["models"]["live"]
    folder = permanent_dir if (replay and permanent_dir) else CACHE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{mode}_{_key(mode, points)}.json"
    with _lock_for(path):
        return _get_data_locked(path, points, models, timezone_name, mode, replay, cfg)


def _get_data_locked(path, points, models, timezone_name, mode, replay, cfg) -> dict:
    now = datetime.now(timezone.utc)
    cached = _read(path)

    def result(blob, from_cache, error=None):
        if not blob:
            return {"points": None, "fetched_at": None, "age_minutes": None, "from_cache": False, "error": error}
        age = (now - datetime.fromisoformat(blob["fetched_at"])).total_seconds() / 60
        return {"points": blob["points"], "fetched_at": blob["fetched_at"], "age_minutes": round(age),
                "from_cache": from_cache, "error": error}

    if cached and (replay or result(cached, True)["age_minutes"] < cfg["forecast"]["live_cache_minutes"]):
        return result(cached, True)
    try:
        pts = fetch_points(points, models, timezone_name, replay["date"] if replay else None)
        blob = {"fetched_at": now.isoformat(timespec="seconds"), "points": pts}
        _write(path, blob)
        log.info("fetched %d point(s) for %s", len(points), mode)
        return result(blob, False)
    except Exception as e:  # network down, API error: fall back to whatever we have
        log.warning("fetch failed for %s: %s", mode, e)
        return result(cached, True, error=str(e))


def elevation(lat: float, lon: float):
    """Metres above sea level at a map click, or None if the check is unavailable."""
    try:
        return _get(load_app()["models"]["elevation_api"], {"latitude": lat, "longitude": lon})[0]["elevation"][0]
    except Exception as e:
        log.warning("elevation check failed: %s", e)
        return None
