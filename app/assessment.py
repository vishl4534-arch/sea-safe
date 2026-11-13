"""The verdict. Pure code: no network, no language model.

Input: one record per trip hour, {"time", "values": {field: number or None}, "beyond_window"}.
Rules (config/thresholds.yaml, docs/design.md section 3):
  * each parameter in each hour gets SAFE / CAUTION / UNSAFE against its lines;
  * within the near-line margin of a CAUTION line -> CAUTION, kind "near";
  * a missing value, an hour beyond the forecast window, or stale data -> CAUTION;
  * the worst parameter decides the hour, the worst hour decides the trip.
"""
import math

SAFE, CAUTION, UNSAFE = "SAFE", "CAUTION", "UNSAFE"
LEVELS = [SAFE, CAUTION, UNSAFE]

# Values no real forecast can have. Anything outside these is treated as missing data (CAUTION), never as
# a number: a NaN or a negative wave height once came out SAFE (audit 13 Nov 2026, item 4).
# These are sanity limits of our own, not safety thresholds; they sit far beyond every caution line.
PLAUSIBLE = {"wave_height": (0, 30), "wind_speed": (0, 400), "wind_gusts": (0, 500),
             "visibility": (0, 1_000_000), "weather_code": (0, 99)}


def usable(field: str, value):
    """The value if it is a real, possible measurement, else None (= missing)."""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    if field == "weather_code" and value != int(value):
        return None
    low, high = PLAUSIBLE.get(field, (-math.inf, math.inf))
    return value if low <= value <= high else None


def _near(line: float, factor: float) -> float:
    """The near-line value, rounded so floating point cannot move it: 37 * 0.9 is 33.300000000000004
    in binary, which would let a forecast of exactly 33.3 km/h through as SAFE."""
    return round(line * factor, 6)


def _check(cfg: dict, value, margin: float):
    """Return (level, kind, threshold) for one parameter value in one hour."""
    if value is None:
        return CAUTION, "missing", None
    direction = cfg["direction"]
    if direction == "codes":
        return (CAUTION, "thunderstorm", None) if value in cfg["codes"] else (SAFE, None, None)
    caution = cfg["caution"]["value"]
    unsafe = cfg.get("unsafe", {}).get("value")
    if direction == "above":
        if unsafe is not None and value >= unsafe:
            return UNSAFE, "unsafe", unsafe
        if value >= caution:
            return CAUTION, "caution", caution
        if value >= _near(caution, 1 - margin):
            return CAUTION, "near", caution
    else:  # "below": lower is worse (visibility)
        if unsafe is not None and value <= unsafe:
            return UNSAFE, "unsafe", unsafe
        if value <= caution:
            return CAUTION, "caution", caution
        if value <= _near(caution, 1 + margin):
            return CAUTION, "near", caution
    return SAFE, None, None


def _worse(cfg: dict, a, b) -> bool:
    """True if value a is worse than value b for this parameter."""
    if b is None:
        return a is not None
    if a is None:
        return False
    return a < b if cfg["direction"] == "below" else a > b


def assess(trip_hours: list, thresholds: dict, stale: bool = False) -> dict:
    params = thresholds["parameters"]
    margin = thresholds["near_line_margin"]
    hours_out, found, summary = [], [], {}

    for hour in trip_hours:
        values = {} if stale else {k: usable(k, v) for k, v in (hour.get("values") or {}).items()}
        if hour.get("beyond_window"):
            hours_out.append({"time": hour["time"], "verdict": CAUTION, "values": {}})
            found.append((CAUTION, {"param": None, "kind": "beyond_window", "value": None,
                                    "threshold": None, "time": hour["time"]}))
            continue
        hour_level = SAFE
        for name, cfg in params.items():
            field = cfg.get("field", name)
            value = values.get(field)
            level, kind, threshold = _check(cfg, value, margin)
            if value is not None and _worse(cfg, value, summary.get(field, {}).get("value")):
                summary[field] = {"value": value, "time": hour["time"]}
            if level != SAFE:
                hour_level = max(hour_level, level, key=LEVELS.index)
                found.append((level, {"param": name, "kind": "stale" if stale else kind, "value": value,
                                      "threshold": threshold, "time": hour["time"]}))
        hours_out.append({"time": hour["time"], "verdict": hour_level, "values": values})

    if not hours_out:
        verdict = CAUTION
        found.append((CAUTION, {"param": None, "kind": "missing", "value": None, "threshold": None, "time": None}))
    else:
        verdict = max((h["verdict"] for h in hours_out), key=LEVELS.index)

    return {"verdict": verdict, "reasons": _drivers(found, verdict, params, stale),
            "hours": hours_out, "summary": summary}


def _drivers(found: list, verdict: str, params: dict, stale: bool) -> list:
    """One reason per parameter: every parameter that was not SAFE in some trip hour, shown by its
    worst value, the hour of that value, and the line that value reached. UNSAFE lines come first.
    (verdict is unused: lower-level parameters are listed too, so the card shows the full picture.)"""
    if stale:
        return [{"param": None, "kind": "stale", "value": None, "threshold": None, "time": None}]
    best = {}  # key -> (level, reason)
    for level, r in found:
        key = r["param"] or r["kind"]          # beyond_window / missing-all have no parameter
        if key not in best:
            best[key] = (level, r)
            continue
        old_level, old = best[key]
        if LEVELS.index(level) != LEVELS.index(old_level):
            if LEVELS.index(level) > LEVELS.index(old_level):
                best[key] = (level, r)
        elif old["kind"] == "missing" and r["value"] is not None:
            best[key] = (level, r)             # a real value says more than "no data"
        elif r["param"] and r["value"] is not None and _worse(params[r["param"]], r["value"], old["value"]):
            best[key] = (level, r)             # same level: keep the worse value (earliest on a tie)
    order = list(params)
    ranked = sorted(best.values(), key=lambda lr: (-LEVELS.index(lr[0]),
                                                   order.index(lr[1]["param"]) if lr[1]["param"] else len(order)))
    return [r for _, r in ranked]


def departure_windows(options: list) -> dict:
    """options: [{"departure", "verdict"}] for consecutive departure hours, in time order. The verdict
    is the whole-trip verdict from that hour, so a departure is SAFE only if its whole trip is SAFE.
    Returns the case and runs of consecutive departures per verdict, e.g. SAFE: [["05:00", "09:00"]]."""
    windows = {SAFE: [], CAUTION: [], UNSAFE: []}
    prev = None
    for o in options:
        if prev is not None and prev == o["verdict"]:
            windows[o["verdict"]][-1][1] = o["departure"]
        else:
            windows[o["verdict"]].append([o["departure"], o["departure"]])
        prev = o["verdict"]
    if not options:
        case = "no_options"
    elif all(o["verdict"] == SAFE for o in options):
        case = "all_safe"
    elif windows[SAFE]:
        case = "some_safe"
    elif windows[CAUTION]:
        case = "caution_only"
    else:
        case = "all_unsafe"
    return {"case": case, "windows": windows}
