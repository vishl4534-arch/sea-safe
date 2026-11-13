"""The wind picture on the map: wind speed and direction on a grid of points, hour by hour.

DISPLAY ONLY. Nothing here is read by app/assessment.py; a verdict never depends on it.
The page draws moving streaks from it so a fisher (or a judge) can see where the wind is blowing.

One Open-Meteo Forecast call per region covers the whole grid. Live data is cached like the
harbour data (config: forecast.live_cache_minutes). A replay day is saved under data/replay
and then used for ever, so replay keeps working offline.
"""
import logging
import math
from datetime import datetime, timedelta, timezone

from app import weather
from app.config import load_app

log = logging.getLogger("seasafe.wind")
FMT = "%Y-%m-%dT%H:%M"


def grid_points(area: dict, step: float) -> tuple[list, int, int]:
    """Points row by row from south to north, each row from west to east. Returns (points, nx, ny)."""
    nx = int(round((area["east"] - area["west"]) / step)) + 1
    ny = int(round((area["north"] - area["south"]) / step)) + 1
    pts = [(round(area["south"] + j * step, 4), round(area["west"] + i * step, 4))
           for j in range(ny) for i in range(nx)]
    return pts, nx, ny


def to_uv(speed, direction):
    """Wind as east (u) and north (v) parts in km/h. `direction` is where the wind comes FROM,
    in degrees clockwise from north (the weather convention), so the air moves the opposite way."""
    if speed is None or direction is None:
        return None, None
    rad = math.radians(direction)
    return round(-speed * math.sin(rad), 1), round(-speed * math.cos(rad), 1)


def _fetch(points: list, models: dict, timezone_name: str, replay_date: str | None) -> dict:
    params = {"latitude": ",".join(f"{p[0]:.2f}" for p in points),
              "longitude": ",".join(f"{p[1]:.2f}" for p in points),
              "hourly": "wind_speed_10m,wind_direction_10m", "wind_speed_unit": "kmh",
              **weather._time_params(timezone_name, replay_date)}
    if models.get("weather_model") and models["weather_model"] != "best_match":
        params["models"] = models["weather_model"]
    rows = weather._get(models["weather_api"], params)
    times = rows[0]["hourly"]["time"]
    return {"times": times,
            "speed": [r["hourly"]["wind_speed_10m"] for r in rows],
            "direction": [r["hourly"]["wind_direction_10m"] for r in rows]}


def wind_field(region: dict, mode: str, replay: dict | None, start: datetime, end: datetime) -> dict:
    """The grid for every whole hour from `start` to `end` (local time, both included).
    Returns {"ok": False} when the picture is switched off or there is no data: the page then
    simply shows no streaks."""
    cfg = load_app()
    pic = cfg.get("wind_picture") or {}
    area = (pic.get("areas") or {}).get(region["id"])
    if not pic.get("enabled") or not area:
        return {"ok": False, "error": "wind_picture_off"}
    points, nx, ny = grid_points(area, pic["step_degrees"])
    models = cfg["models"][replay["models"]] if replay else cfg["models"]["live"]
    folder = weather.REPLAY_DIR if replay else weather.CACHE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"wind_{mode}_{weather._key('wind' + mode, points)}.json"

    with weather._lock_for(path):
        now = datetime.now(timezone.utc)
        blob = weather._read(path)
        fresh = blob and (replay or (now - datetime.fromisoformat(blob["fetched_at"])).total_seconds() / 60
                          < cfg["forecast"]["live_cache_minutes"])
        if not fresh:
            try:
                blob = {"fetched_at": now.isoformat(timespec="seconds"),
                        **_fetch(points, models, region["timezone"], replay["date"] if replay else None)}
                weather._write(path, blob)
                log.info("fetched wind picture for %s (%d points)", mode, len(points))
            except Exception as e:                       # noqa: BLE001  (a picture, never an error for the user)
                log.warning("wind picture not available for %s: %s", mode, e)
    if not blob:
        return {"ok": False, "error": "no_data"}

    index = {t: i for i, t in enumerate(blob["times"])}
    hours, u_all, v_all = [], [], []
    t = start
    while t <= end:
        key = t.strftime(FMT)
        i = index.get(key)
        if i is not None:
            uv = [to_uv(s[i] if i < len(s) else None, d[i] if i < len(d) else None)
                  for s, d in zip(blob["speed"], blob["direction"])]
            hours.append(key)
            u_all.append([a for a, _ in uv])
            v_all.append([b for _, b in uv])
        t += timedelta(hours=1)
    if not hours:
        return {"ok": False, "error": "no_data"}
    return {"ok": True, **area, "nx": nx, "ny": ny, "hours": hours, "u": u_all, "v": v_all,
            "fetched_at": blob["fetched_at"]}
