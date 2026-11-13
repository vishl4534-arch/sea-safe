"""Sunrise and sunset, worked out by code (NOAA's general solar position formulas, accurate to a minute or two).
No data source is needed, so it works for live and replay days alike, and offline."""
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def sun_times(lat: float, lon: float, day: date, tz: str) -> tuple[str, str] | None:
    """('06:05', '18:52') local time, or None if the sun does not rise or set that day."""
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    phi = math.radians(lat)
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(phi) * math.cos(decl)) - math.tan(phi) * math.tan(decl)
    if not -1 <= cos_ha <= 1:
        return None
    ha = math.degrees(math.acos(cos_ha))
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)

    def local(minutes_utc: float) -> str:
        t = (midnight + timedelta(minutes=minutes_utc)).astimezone(ZoneInfo(tz))
        t += timedelta(seconds=30)                     # round to the nearest minute
        return t.strftime("%H:%M")

    return local(720 - 4 * (lon + ha) - eqtime), local(720 - 4 * (lon - ha) - eqtime)
