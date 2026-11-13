"""Turns a service result into text in one language, using only translations/*.json.
Every word a user reads about a verdict comes from here, never from the language model."""
import hashlib
import re
from datetime import datetime, timedelta

from app.assessment import _check, _near, LEVELS, CAUTION
from app.config import load_app, load_thresholds, load_translations, region as get_region

DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
# Waves keep 2 decimals so a value never rounds onto a line it has not reached (1.98 m must not read "2.0").
# Wind and gusts keep 1 decimal for the same reason (42.6 km/h must not read "43", the UNSAFE line).
DECIMALS = {"wave_height": 2, "wave_period": 0, "wind_speed": 1, "wind_gusts": 1, "visibility": 0}


def pick_lang(lang: str, region_id: str | None = None) -> str:
    """The language to answer in: the one asked for if it is switched on (for this region), else
    English if that is on, else the region's first language. A switched-off language is never served."""
    cfg = load_app()
    allowed = get_region(region_id)["languages"] if region_id else list(cfg["languages"])
    if lang in allowed:
        return lang
    return "en" if "en" in allowed else (allowed[0] if allowed else "en")


def t(lang: str, key: str, **kw) -> str:
    text = load_translations(lang).get(key) or load_translations("en").get(key) or key
    text = text.format(**kw) if kw else text
    return _ar_counts(text) if lang == "ar" else text


# Arabic counted nouns change with the number: 1 ساعة واحدة, 2 ساعتين, 3-10 ساعات, 11 and up ساعة.
# The templates write "{hours} ساعات"; this puts the right form after every whole number (reviewed rule, not a model).
_AR_FORMS = {"ساعات": ("ساعة واحدة", "ساعتين", "ساعات", "ساعة"), "ساعة": ("ساعة واحدة", "ساعتين", "ساعات", "ساعة"),
             "ثوانٍ": ("ثانية واحدة", "ثانيتين", "ثوانٍ", "ثانية"), "ثانية": ("ثانية واحدة", "ثانيتين", "ثوانٍ", "ثانية"),
             "دقائق": ("دقيقة واحدة", "دقيقتين", "دقائق", "دقيقة"), "دقيقة": ("دقيقة واحدة", "دقيقتين", "دقائق", "دقيقة")}
_AR_COUNT = re.compile(r"(?<![\d.])(\d+) (%s)(?![\w])" % "|".join(_AR_FORMS))


def _ar_counts(text: str) -> str:
    def fix(m):
        n, forms = int(m.group(1)), _AR_FORMS[m.group(2)]
        if n == 1:
            return forms[0]
        if n == 2:
            return forms[1]
        return f"{n} {forms[2] if 3 <= n <= 10 else forms[3]}"
    return _AR_COUNT.sub(fix, text)


SPOKEN_DECIMALS = {"wave_height": 1}     # everything else is said as a whole number


def say_num(field: str, value) -> str:
    """A value for the voice: waves to 0.1 m, the rest whole ("39 kilometres per hour", not "39.2").
    If the rounded value would get a different result from the verdict code (another side of a caution,
    unsafe or near line), the exact value is said instead, so the voice never contradicts the verdict.
    The card keeps the exact numbers."""
    if value is None:
        return "–"
    d = SPOKEN_DECIMALS.get(field, 0)
    r = round(value, d)
    th = load_thresholds()
    cfg = th["parameters"].get(field)
    if cfg and _check(cfg, value, th["near_line_margin"]) != _check(cfg, r, th["near_line_margin"]):
        return f"{value:g}"                    # unrounded: 35.96 stays 35.96, not "36"
    return f"{r:.{d}f}" if d else f"{int(r):d}"


def num(field: str, value) -> str:
    if value is None:
        return "–"
    d = DECIMALS.get(field, 0)
    return f"{value:.{d}f}" if d else f"{round(value):d}"


def when(lang: str, s: str | None) -> str:
    if not s:
        return "–"
    d = datetime.fromisoformat(s)
    return t(lang, "time.format", weekday=t(lang, f"weekday.{d.weekday()}"), day=d.day,
             month=t(lang, f"month.{d.month}"), hh=f"{d.hour:02d}", mm=f"{d.minute:02d}")


def on_date(lang: str, s: str) -> str:
    d = datetime.fromisoformat(s)
    return t(lang, "date.format", day=d.day, month=t(lang, f"month.{d.month}"), year=d.year)


def direction(lang: str, degrees) -> str:
    return "–" if degrees is None else t(lang, f"dir.{DIRS[round(degrees / 45) % 8]}")


def place_name(lang: str, place: dict) -> str:
    return t(lang, f"place.{place['id']}")


def reason_text(lang: str, r: dict, spoken: bool = False, day: str | None = None) -> str:
    """One reason line. spoken=True: units as words, and just the hour when it is on `day`."""
    cfg = load_app()
    at = (lambda ts: _short_when(lang, ts, day)) if spoken else (lambda ts: when(lang, ts))
    params = load_thresholds()["parameters"]
    kind = r["kind"]
    if kind == "stale":
        return t(lang, "reason.stale", hours=cfg["forecast"]["stale_after_hours"])
    if kind == "beyond_window":
        return t(lang, "reason.beyond_window", hours=cfg["forecast"]["window_hours"], time=at(r["time"]))
    if kind == "thunderstorm":
        return t(lang, "reason.thunderstorm", time=at(r["time"]))
    if kind == "missing":
        if not r["param"] or not r["time"]:
            return t(lang, "reason.missing_all")
        return t(lang, "reason.missing", param=t(lang, f"param.{r['param']}"), time=at(r["time"]))
    p = params[r["param"]]
    key = f"reason.{kind}" + ("_below" if p["direction"] == "below" and kind != "unsafe" else "")
    unit = t(lang, f"{'say.unit' if spoken else 'unit'}.{p['unit']}")   # spoken: "metres", not "m"
    return t(lang, key, param=t(lang, f"param.{r['param']}"), value=num(r["param"], r["value"]),
             threshold=f"{r['threshold']:g}", unit=unit, time=at(r["time"]))


def render(res: dict, lang: str) -> dict:
    """Structured, translated explanation of one assess_trip result (used by the card and the chat)."""
    region = get_region(res["region"])
    cfg = load_app()
    s = res["summary"]
    pname = place_name(lang, res["place"])
    if res["verdict"] == "SAFE":
        reasons = [t(lang, "reason.safe_summary", wave=num("wave_height", s.get("wave_height", {}).get("value")),
                     wind=num("wind_speed", s.get("wind_speed", {}).get("value")),
                     gust=num("wind_gusts", s.get("wind_gusts", {}).get("value")))]
        icons = ["summary"]
    else:
        missing_all = all(r["kind"] == "missing" for r in res["reasons"]) and res["data"]["fetched_at"] is None
        reasons = [t(lang, "reason.missing_all")] if missing_all else [reason_text(lang, r) for r in res["reasons"]]
        # what each reason is about, so the page can put a picture next to it (wave, wind, storm...)
        icons = ["missing"] if missing_all else [r["param"] or r["kind"] for r in res["reasons"]]
    data = res["data"]
    km = res["place"]["sea_cell_km"]
    fetched = when(lang, _local(data["fetched_at"], region["timezone"])) if data["fetched_at"] else "–"
    return {
        "verdict": res["verdict"],
        "verdict_word": t(lang, f"verdict.{res['verdict']}"),
        "advice": t(lang, f"advice.{res['verdict']}"),
        "headline": t(lang, "headline", place=pname, verdict=t(lang, f"verdict.{res['verdict']}")),
        "place": pname,
        "boat_class": t(lang, f"boat_class.{load_thresholds()['boat_class']}"),
        "reasons": reasons,
        "reason_icons": icons,
        "spoken": spoken(res, lang),       # the short version, shown in the conversation and read by the voice
        "trip": t(lang, "trip.line", departure=when(lang, res["departure"]), **{"return": when(lang, res["return"])}),
        "trip_length": t(lang, "trip.length_given" if res["trip_length_given_by_user"] else "trip.length_assumed",
                         hours=res["trip_hours"]),
        "sea_cell": None if km is None else t(lang, "data.sea_cell_far" if res["place"]["sea_cell_far"] else "data.sea_cell",
                                              km=f"{km:.1f}", from_place=t(lang, f"place_from.{res['place']['id']}")),
        "sea_cell_far": res["place"]["sea_cell_far"],
        "data_line": t(lang, "data.line", **{"from": when(lang, res["departure"])}, to=when(lang, res["return"]),
                       tz=t(lang, f"tz.{res['region']}"), fetched=fetched),
        "fetch_note": t(lang, "data.fetch_failed", age=data["age_minutes"]) if data["fetch_error"] and data["fetched_at"] else None,
        "model_line": t(lang, "data.model", marine=data["marine_model"], weather=data["weather_model"]),
        "attribution": t(lang, "data.attribution"),
        "sun": (lambda s: t(lang, "card.sun", rise=s[0], set=s[1]) if s else "")(sun_for(res)),
        "disclaimer": t(lang, "disclaimer"),
        "warnings": region["official_warnings"],
        "hours": [{"time": h["time"], "label": when(lang, h["time"]), "verdict": h["verdict"],
                   "verdict_word": t(lang, f"verdict.{h['verdict']}"), "values": _hour_values(lang, h["values"]),
                   "closeness": _closeness(h["values"])}
                  for h in res["hours"]],
        "gauges": _gauges(lang, res),
        "bars_note": t(lang, "card.bars_note"),
        "bullets": bullets(res, lang),       # the chat bubble for this answer (13 Nov 2026)
        # The trip exactly as it was checked, for "Trip understood", sharing and watching (page formats it).
        "trip_fields": {"place_id": res["place"]["id"], "departure": res["departure"], "return": res["return"],
                        "hours": res["trip_hours"], "given": res["trip_length_given_by_user"],
                        "live": res["mode"]["live"]},
    }


def _gauges(lang: str, res: dict) -> list:
    """One row per verdict parameter, for the picture on the card: the worst value of the trip, where
    the caution and unsafe lines sit, and the level the verdict code gives this parameter.
    A picture of numbers the verdict already used; nothing here decides anything."""
    th = load_thresholds()
    margin = th["near_line_margin"]
    out = []
    for name, cfg in th["parameters"].items():
        field = cfg.get("field", name)
        levels = [_check(cfg, h["values"].get(field), margin)[0] for h in res["hours"]]
        level = max(levels, key=LEVELS.index) if levels else CAUTION
        row = {"param": name, "label": t(lang, f"param.{name}"), "direction": cfg["direction"],
               "level": level, "level_word": t(lang, f"verdict.{level}"),
               "value": None, "text": "", "caution": None, "unsafe": None, "near": None}
        if cfg["direction"] != "codes":
            worst = res["summary"].get(field, {}).get("value")
            caution = cfg["caution"]["value"]
            unsafe = cfg.get("unsafe", {}).get("value")
            unit = t(lang, f"unit.{cfg['unit']}")
            row.update(value=worst, text="–" if worst is None else f"{num(field, worst)} {unit}",
                       caution=caution, unsafe=unsafe,
                       near=_near(caution, 1 - margin if cfg["direction"] == "above" else 1 + margin),
                       caution_text=f"{caution:g}", unsafe_text=None if unsafe is None else f"{unsafe:g}")
        out.append(row)
    return out


def _closeness(values: dict):
    """How close one hour comes to a caution line: its worst value divided by that value's caution
    line (1.0 = on the line). For visibility, where lower is worse, the line is divided by the value.
    Only sets the height of the hour bars on the card; None when the hour has no numbers."""
    best = None
    for name, cfg in load_thresholds()["parameters"].items():
        if cfg["direction"] == "codes":
            continue
        v = (values or {}).get(cfg.get("field", name))
        if v is None:
            continue
        line = cfg["caution"]["value"]
        ratio = v / line if cfg["direction"] == "above" else (line / v if v > 0 else 2.0)
        best = ratio if best is None else max(best, ratio)
    return None if best is None else round(min(best, 2.0), 3)


def _hour_values(lang: str, v: dict) -> dict:
    """Display strings for the details table, including the display-only fields."""
    if not v:
        return {}
    return {
        "wave_height": f"{num('wave_height', v.get('wave_height'))} {t(lang, 'unit.m')}",
        "wave_period": f"{num('wave_period', v.get('wave_period'))} {t(lang, 'unit.s')}",
        "wave_direction": direction(lang, v.get("wave_direction")),
        "wind_speed": f"{num('wind_speed', v.get('wind_speed'))} {t(lang, 'unit.km/h')}",
        "wind_gusts": f"{num('wind_gusts', v.get('wind_gusts'))} {t(lang, 'unit.km/h')}",
        "wind_direction": direction(lang, v.get("wind_direction")),
        "visibility": f"{num('visibility', v.get('visibility'))} {t(lang, 'unit.m')}",
        "weather_code": "–" if v.get("weather_code") is None else str(v["weather_code"]),
        "rain": "–" if v.get("rain") is None else f"{v['rain']:g}",
        "air_temperature": "–" if v.get("air_temperature") is None else f"{v['air_temperature']:.0f}",
        "sea_temperature": "–" if v.get("sea_temperature") is None else f"{v['sea_temperature']:.0f}",
    }


def _local(utc_iso: str, tz: str) -> str:
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(utc_iso).astimezone(ZoneInfo(tz)).replace(tzinfo=None).isoformat(timespec="minutes")


def text(res: dict, lang: str) -> str:
    """Plain text version for the chat (and later for speech)."""
    r = render(res, lang)
    lines = [r["headline"], r["advice"], r["boat_class"] + ".", *r["reasons"], r["trip"], r["trip_length"]]
    if r["sea_cell"]:
        lines.append(r["sea_cell"])
    if r["fetch_note"]:
        lines.append(r["fetch_note"])
    lines += [r["data_line"], r["model_line"], r["attribution"], r["disclaimer"]]
    return "\n".join(lines)


def _windows(lang: str, windows: list, style: str = "window", joiner: str = "list.joiner") -> str:
    """'Tue 20 May, 05:00 to 09:00', joined. The end shows only the hour when it is the same day.
    style "dont" gives the 'between 06:00 and 19:00' / 'at 22:00' forms used in 'Do not leave ...'."""
    parts = []
    for a, b in windows:
        if a == b:
            parts.append(when(lang, a) if style == "window" else t(lang, "safest.dont_single", time=when(lang, a)))
        else:
            end = (t(lang, "time.short", hh=b[11:13], mm=b[14:16]) if a[:10] == b[:10] else when(lang, b))
            parts.append(t(lang, f"safest.{style}", start=when(lang, a), end=end))
    return t(lang, joiner).join(parts)


def _short_when(lang: str, s: str | None, day: str | None) -> str:
    """'14:00' when the time is on the trip's departure day, else the full date and time."""
    if s and day and s[:10] == day:
        return t(lang, "time.short", hh=s[11:13], mm=s[14:16])
    return when(lang, s)


# ---- speech: times and dates the way people say them ("at 9 in the morning", not "09:00") ----------
def _period(hour: int) -> str:
    if hour == 0:
        return "midnight"
    if hour == 12:
        return "noon"
    if 1 <= hour <= 4:
        return "early"          # when many fishers leave: "4 in the early morning", not "4 at night"
    if 5 <= hour <= 11:
        return "morning"
    if 13 <= hour <= 15:
        return "afternoon"
    if 16 <= hour <= 19:
        return "evening"
    return "night"


def say_time(lang: str, ts: str, form: str = "at") -> str:
    """form: 'at' / 'from' / 'until'. Kannada needs whole joined forms (ಗಂಟೆಗೆ, ಗಂಟೆಯಿಂದ, ಗಂಟೆಯವರೆಗೆ)."""
    h = int(ts[11:13])
    return t(lang, f"say.{form}.{_period(h)}", h=(h % 12) or 12)


def _spoken_date(ts: str):
    """The day people name for a time. 00:00 on Friday is "Thursday at midnight": the end of Thursday."""
    d = datetime.fromisoformat(ts[:16])
    return (d - timedelta(days=1)).date() if d.hour == 0 else d.date()


def say_day(lang: str, ts: str) -> str:
    """'on Tuesday': the weekday alone. Answers cover the next 48 hours, so it is never ambiguous."""
    return t(lang, "say.on_weekday", weekday=t(lang, f"say.weekday.{_spoken_date(ts).weekday()}"))


def say_full_date(lang: str, ts: str) -> str:
    d = datetime.fromisoformat(ts[:10])
    return t(lang, "say.full_date", day=d.day, month=t(lang, f"say.month.{d.month}"), year=d.year)


def say_at(lang: str, ts: str, day: str, form: str = "at") -> str:
    """The time alone if it is on the departure day, else the day and the time."""
    same = ts[:10] == day or _spoken_date(ts).isoformat() == day      # midnight closing the departure day
    return say_time(lang, ts, form) if same else f"{say_day(lang, ts)} {say_time(lang, ts, form)}"


def spoken_reason(lang: str, r: dict, day: str, lead: str = "") -> str:
    """One reason, for the voice: units as words, times spoken, no symbols. lead joins the reasons
    the way people talk ("Watch out for", "Also", "And")."""
    kind = r["kind"]
    if kind == "stale":
        return t(lang, "reason.stale", hours=load_app()["forecast"]["stale_after_hours"])
    if kind == "beyond_window":
        return t(lang, "say.reason.beyond_window")
    if kind == "missing" and (not r["param"] or not r["time"]):
        return t(lang, "reason.missing_all")
    at = say_at(lang, r["time"], day, "around")
    if kind == "thunderstorm":
        return t(lang, "say.reason.thunderstorm", at=at)
    param = t(lang, f"say.param.{r['param']}")
    if kind == "missing":
        return t(lang, "say.reason.missing", param=param, at=at)
    p = load_thresholds()["parameters"][r["param"]]
    key = f"say.reason.{kind}" + ("_below" if p["direction"] == "below" and kind != "unsafe" else "")
    value = say_num(r["param"], r["value"])
    # {amount}: the value with its unit in the order the language says it (Kannada "ಗಂಟೆಗೆ 40 ಕಿಲೋಮೀಟರ್").
    return t(lang, key, lead=lead, param=param, value=value, amount=t(lang, f"say.amount.{p['unit']}", value=value),
             threshold=f"{r['threshold']:g}", unit=t(lang, f"say.unit.{p['unit']}"), at=at)


def _when_words(lang: str, res: dict) -> dict:
    """{day, time} for the departure said back. "now" when the fisher is leaving in the current hour of the
    live forecast: at 00:40 on Friday, "right now" must not come back as "Thursday at midnight"."""
    if res.get("leaving_now"):
        return {"day": "", "time": t(lang, "say.now")}
    return {"day": say_day(lang, res["departure"]), "time": say_time(lang, res["departure"])}


OPENERS = 3        # say.opener.0 .. 2 ("Okay" / "Alright" / "Right")


def spoken(res: dict, lang: str) -> str:
    """What the voice reads aloud, in a conversational style (approved 13 Nov 2026). Built only from
    translation templates, like the card; no model writes it:
    replay label; the question said back with the verdict ("Okay, leaving from Malpe on Tuesday at 5 in
    the morning: that's a caution."); short advice; one reason per parameter (value, time, which line); when
    they would be back; the trip length only if we assumed it; the disclaimer and "Stay safe".
    The opener is chosen by code from the place and time, so the same question always sounds the same.
    The card keeps the exact values, thresholds, data line, fetch time, model and Open-Meteo credit."""
    day = res["departure"][:10]
    sm = res["summary"]
    parts = []
    pick = int(hashlib.sha1(f"{res['place']['id']}|{res['departure']}".encode()).hexdigest(), 16) % OPENERS
    parts.append(" ".join(t(lang, f"say.verdict_line.{res['verdict']}", opener=t(lang, f"say.opener.{pick}"),
                            place_from=t(lang, f"place_from.{res['place']['id']}"), **_when_words(lang, res)).split()))
    if res["verdict"] != "CAUTION":                    # "Be careful out there." dropped (owner, 13 Nov 2026)
        parts.append(t(lang, f"say.advice.{res['verdict']}"))
    if res["verdict"] == "SAFE":
        parts.append(t(lang, "say.safe_summary",
                       **{k: say_num(f, sm.get(f, {}).get("value"))
                          for k, f in (("wave", "wave_height"), ("wind", "wind_speed"), ("gust", "wind_gusts"))}))
    else:
        rs = res["reasons"]
        if all(x["kind"] == "missing" for x in rs) and res["data"]["fetched_at"] is None:
            parts.append(t(lang, "reason.missing_all"))
        else:
            for i, r in enumerate(rs):
                lead = t(lang, "say.lead." + ("first" if i == 0 else "last" if i == len(rs) - 1 else "middle"))
                parts.append(spoken_reason(lang, r, day, lead))
    parts.append(t(lang, "say.back", time=say_at(lang, res["return"], day, "around")))
    if not res["trip_length_given_by_user"]:           # a length the user gave is not read back to them
        parts.append(t(lang, "say.trip_assumed", hours=res["trip_hours"]))
    parts.append(t(lang, "say.disclaimer"))
    return " ".join(parts)


def _short_time(lang: str, ts: str | None, day: str) -> str:
    """'16:00' on the departure day, else the full 'Sat 14 Nov, 02:00'."""
    if not ts:
        return "–"
    return ts[11:16] if ts[:10] == day else when(lang, ts)


def bullets(res: dict, lang: str) -> str:
    """The chat answer for one trip: short, direct bullet points (owner request, 13 Nov 2026). Built only
    from templates and the verdict code's own numbers, like the card: the trip, then one line per reason
    (or the all-clear line), the UNSAFE advice, the replay label and the disclaimer. The voice reads
    spoken() instead, because bullet points do not work aloud."""
    day = res["departure"][:10]
    pname = place_name(lang, res["place"])
    tag = t(lang, "trip.said_tag" if res["trip_length_given_by_user"] else "trip.assumed_tag")
    lines = [t(lang, "chat.b.trip", place=pname, departure=when(lang, res["departure"]),
               back=_short_time(lang, res["return"], day), hours=res["trip_hours"], tag=tag)]
    if res["verdict"] == "SAFE":
        sm = res["summary"]
        lines.append(t(lang, "chat.b.safe", wave=num("wave_height", sm.get("wave_height", {}).get("value")),
                       wind=num("wind_speed", sm.get("wind_speed", {}).get("value")),
                       gust=num("wind_gusts", sm.get("wind_gusts", {}).get("value"))))
    elif all(r["kind"] == "missing" for r in res["reasons"]) and res["data"]["fetched_at"] is None:
        lines.append(t(lang, "reason.missing_all"))
    else:
        params = load_thresholds()["parameters"]
        for r in res["reasons"]:
            kind, at = r["kind"], _short_time(lang, r.get("time"), day)
            if kind == "stale":
                lines.append(t(lang, "reason.stale", hours=load_app()["forecast"]["stale_after_hours"]))
            elif kind == "beyond_window":
                lines.append(t(lang, "reason.beyond_window", hours=load_app()["forecast"]["window_hours"], time=at))
            elif kind == "thunderstorm":
                lines.append(t(lang, "chat.b.thunderstorm", time=at))
            elif kind == "missing":
                lines.append(t(lang, "chat.b.missing", param=t(lang, f"param.{r['param']}") if r["param"] else "–", time=at))
            else:
                p = params[r["param"]]
                key = f"chat.b.{kind}" + ("_below" if p["direction"] == "below" and kind != "unsafe" else "")
                lines.append(t(lang, key, param=t(lang, f"param.{r['param']}"), value=num(r["param"], r["value"]),
                               unit=t(lang, f"unit.{p['unit']}"), time=at, threshold=f"{r['threshold']:g}"))
    if res["verdict"] == "UNSAFE":
        lines.append(t(lang, "chat.b.advice_unsafe"))
    lines.append(t(lang, "chat.b.disclaimer"))
    return "\n".join("• " + x for x in lines)


# ---- "which harbours are safe at 1 pm?": every harbour at one departure ----------------------------
VERDICT_ORDER = ("SAFE", "CAUTION", "UNSAFE")


def _by_verdict(res: dict, lang: str) -> dict:
    out = {v: [] for v in VERDICT_ORDER}
    for r in res["harbours"].values():
        out[r["verdict"]].append(place_name(lang, r["place"]))
    return out


def _say_list(lang: str, names: list) -> str:
    """'A, B and C' (Arabic joins 'and' to the next word)."""
    if len(names) < 2:
        return "".join(names)
    return t(lang, "list.joiner_names").join(names[:-1]) + t(lang, "say.list_and") + names[-1]


def region_spoken(res: dict, lang: str) -> str:
    """The spoken answer for every harbour at one time, short (13 Nov 2026: listing every CAUTION harbour was too
    long). It names the SAFE harbours, names any UNSAFE ones (never left out), and sums up the rest as a caution.
    The card on screen lists every harbour. Templates only."""
    first = next(iter(res["harbours"].values()))
    g = _by_verdict(res, lang)
    n = len(res["harbours"])
    pick = int(hashlib.sha1(f"all|{res['departure']}".encode()).hexdigest(), 16) % OPENERS
    parts = [" ".join(t(lang, "say.region.intro", opener=t(lang, f"say.opener.{pick}"), hours=res["trip_hours"],
                        **_when_words(lang, res)).split())]
    if len(g["SAFE"]) == n:
        parts.append(t(lang, "say.region.all_safe"))
    elif len(g["UNSAFE"]) == n:
        parts.append(t(lang, "say.region.all_unsafe"))
    elif len(g["CAUTION"]) == n:
        parts.append(t(lang, "say.region.all_caution"))
    else:
        parts.append(t(lang, "say.region.safe_" + ("one" if len(g["SAFE"]) == 1 else "many"),
                       places=_say_list(lang, g["SAFE"])) if g["SAFE"] else t(lang, "say.region.none_safe"))
        if g["UNSAFE"]:
            parts.append(t(lang, "say.region.unsafe_" + ("one" if len(g["UNSAFE"]) == 1 else "many"),
                           places=_say_list(lang, g["UNSAFE"])))
        if g["CAUTION"]:
            parts.append(t(lang, "say.region.rest_caution"))
    parts.append(t(lang, "say.disclaimer"))
    return " ".join(x for x in parts if x)


# ---- weather details (rain, temperature, directions, sun): reviewed templates, numbers from data ----------
def say_clock(lang: str, hhmm: str) -> str:
    """'06:05' -> 'at 6:05 in the morning' (any minute, for sunrise and sunset)."""
    h, m = int(hhmm[:2]), hhmm[3:5]
    period = _period(h) if h not in (0, 12) else ("night" if h == 0 else "afternoon")
    return t(lang, f"say.at.{period}", h=f"{(h % 12) or 12}:{m}")


def sun_for(res: dict) -> tuple[str, str] | None:
    from app.sun import sun_times
    p, region = res["place"], get_region(res["region"])
    return sun_times(p["lat"], p["lon"], datetime.fromisoformat(res["departure"][:10]).date(), region["timezone"])


def _trip_values(res: dict, field: str) -> list:
    return [(h["time"], h["values"].get(field)) for h in res["hours"] if h["values"].get(field) is not None]


def details_spoken(res: dict, lang: str, detail: str = "all") -> str:
    """The spoken answer to 'will it rain / how hot / where is the wind from / when is sunset': the detail asked
    about (or all of them) over the trip, then that trip's safety verdict, then the disclaimer.
    Every number comes from the data or from code."""
    want = lambda d: detail in ("all", d)                  # noqa: E731
    day = res["departure"][:10]
    pick = int(hashlib.sha1(f"d|{res['place']['id']}|{res['departure']}".encode()).hexdigest(), 16) % OPENERS
    parts = [" ".join(t(lang, "say.details.intro", opener=t(lang, f"say.opener.{pick}"),
                        place_from=t(lang, f"place_from.{res['place']['id']}"), **_when_words(lang, res)).split())]
    found = 0
    air = [v for _, v in _trip_values(res, "air_temperature")] if want("air_temperature") else []
    if air:
        lo, hi = round(min(air)), round(max(air))
        parts.append(t(lang, "say.details.air_one", t=lo) if lo == hi else t(lang, "say.details.air_range", min=lo, max=hi))
        found += 1
    sea = [v for _, v in _trip_values(res, "sea_temperature")] if want("sea_temperature") else []
    if sea:
        parts.append(t(lang, "say.details.sea", t=round(sum(sea) / len(sea))))
        found += 1
    rain = _trip_values(res, "rain") if want("rain") else []
    if rain:
        at, mm = max(rain, key=lambda x: x[1])
        parts.append(t(lang, "say.details.no_rain") if mm < 0.1 else
                     t(lang, "say.details.rain", mm=f"{mm:.1f}".rstrip("0").rstrip("."), at=say_at(lang, at, day, "around")))
        found += 1
    first = res["hours"][0]["values"] if res["hours"] else {}
    if want("wind_direction") and first.get("wind_direction") is not None:
        parts.append(t(lang, "say.details.wind_dir", dir=direction(lang, first["wind_direction"])))
        found += 1
    if want("waves") and first.get("wave_direction") is not None and first.get("wave_period") is not None:
        parts.append(t(lang, "say.details.waves", dir=direction(lang, first["wave_direction"]), s=round(first["wave_period"])))
        found += 1
    sun = sun_for(res) if want("sun") else None
    if sun:
        parts.append(t(lang, "say.details.sun", rise=say_clock(lang, sun[0]), set=say_clock(lang, sun[1])))
        found += 1
    if not found:
        parts.append(t(lang, "say.details.none"))
    if detail != "sun":                                    # sunrise and sunset need no safety verdict
        parts.append(t(lang, f"say.details.verdict.{res['verdict']}"))
    parts.append(t(lang, "say.disclaimer"))
    return " ".join(x for x in parts if x)


def details_text(res: dict, lang: str, detail: str = "all") -> str:
    """Written version: the spoken details, then the data line and credit of the card."""
    v = render(res, lang)
    return "\n".join([details_spoken(res, lang, detail), v["data_line"], v["attribution"]])


# ---- explaining the app: reviewed answers, every number from config ------------------------------------
def _faq_numbers(lang: str, region_id: str) -> dict:
    th, cfg = load_thresholds()["parameters"], load_app()
    live = cfg["models"]["live"]
    return {"wave_c": f"{th['wave_height']['caution']['value']:g}", "wave_u": f"{th['wave_height']['unsafe']['value']:g}",
            "wind_c": th["wind_speed"]["caution"]["value"], "wind_u": th["wind_speed"]["unsafe"]["value"],
            "gust_c": th["wind_gusts"]["caution"]["value"], "gust_u": th["wind_gusts"]["unsafe"]["value"],
            "vis_c": th["visibility"]["caution"]["value"], "pct": round(load_thresholds()["near_line_margin"] * 100),
            "window": cfg["forecast"]["window_hours"], "stale": cfg["forecast"]["stale_after_hours"],
            "cache": cfg["forecast"]["live_cache_minutes"], "marine": live["marine_model"], "weather": live["weather_model"],
            "how": t(lang, "ui.how_we_decide")}


def faq_spoken(topic: str, lang: str, region_id: str) -> str:
    return t(lang, f"faq.{topic}", **_faq_numbers(lang, region_id))


def faq_text(topic: str, lang: str, region_id: str) -> str:
    """Written version; for the sources, the full title of every source document too."""
    text = faq_spoken(topic, lang, region_id)
    if topic in ("sources", "how_decided"):
        th = load_thresholds()
        used = dict.fromkeys(x["source"] for p in th["parameters"].values() for x in (p.get("caution"), p.get("unsafe")) if x)
        text += "\n" + "\n".join(f"- {th['sources'][s]['title']}" for s in used)
    return text


# ---- official warnings and emergency contacts (from config; numbers only after the owner approves them) ----
def _contacts(region: dict, lang: str) -> list:
    """Spoken: the number digit by digit ("1 5 5 4"), so the voice never reads it as a year or an amount."""
    return [t(lang, "say.official.contact", name=t(lang, c["name_key"]), number=" ".join(c["number"]))
            for c in region.get("emergency_contacts", [])]


def official_spoken(region_id: str, lang: str) -> str:
    region = get_region(region_id)
    names = _say_list(lang, [w["name"] for w in region["official_warnings"]])
    parts = [t(lang, "say.official.warnings", names=names)]
    contacts = _contacts(region, lang)
    parts.append(t(lang, "say.official.contacts", contacts=_say_list(lang, contacts)) if contacts
                 else t(lang, "say.official.no_contacts"))
    return " ".join(parts)


def official_text(region_id: str, lang: str) -> str:
    region = get_region(region_id)
    lines = [official_spoken(region_id, lang)]
    lines += [f"- {w['name']}: {w['url']}" for w in region["official_warnings"]]
    lines += [f"- {t(lang, c['name_key'])}: {c['number']} ({c['source']})" for c in region.get("emergency_contacts", [])]
    return "\n".join(lines)


def region_view(res: dict, lang: str) -> dict:
    """What the page shows for every harbour at one time: harbours grouped by verdict (each one tappable),
    with the same data line, credit, disclaimer and official warnings as a single-harbour card."""
    first = render(next(iter(res["harbours"].values())), lang)
    groups = {v: [] for v in VERDICT_ORDER}
    for hid, r in res["harbours"].items():
        groups[r["verdict"]].append({"id": hid, "name": place_name(lang, r["place"])})
    return {"heading": t(lang, "region.heading", when=when(lang, res["departure"]), hours=res["trip_hours"]),
            "groups": [{"verdict": v, "word": t(lang, f"verdict.{v}"), "places": groups[v]} for v in VERDICT_ORDER
                       if groups[v]],
            "departure": res["departure"], "trip_hours": res["trip_hours"],
            "trip_length_given_by_user": res["trip_length_given_by_user"],
            **{k: first[k] for k in ("data_line", "model_line", "attribution", "disclaimer",
                                     "warnings")}}


def region_text(res: dict, lang: str) -> str:
    """The written answer for every harbour at one time, with the data line, credit and disclaimer."""
    first = render(next(iter(res["harbours"].values())), lang)
    groups = _by_verdict(res, lang)
    lines = [t(lang, "region.heading", when=when(lang, res["departure"]), hours=res["trip_hours"])]
    lines += [t(lang, "region.line", verdict=t(lang, f"verdict.{v}"), places=t(lang, "list.joiner_names").join(groups[v]))
              for v in VERDICT_ORDER if groups[v]]
    lines += [first["data_line"], first["model_line"], first["attribution"], first["disclaimer"]]
    return "\n".join(lines)


def _say_windows(lang: str, windows: list, day: str, single_form: str = "at") -> str:
    out = []
    for a, b in windows:
        if a == b:
            out.append(say_at(lang, a, day, single_form))
        else:
            out.append(t(lang, "say.window", start=say_at(lang, a, day, "from"), end=say_at(lang, b, day, "until")))
    return t(lang, "say.or").join(out)


def safest_spoken(sres: dict, lang: str) -> str:
    """'When is the safest time', for the voice: the same windows as the written answer, times spoken."""
    day = sres["search_from"][:10]
    kw = {"hours": sres["trip_hours"]}
    case = sres["case"]
    d = datetime.fromisoformat(sres["search_from"][:10])
    lead = t(lang, "say.safest.day", place_from=t(lang, f"place_from.{sres['shown']['place']['id']}"),
             day=t(lang, "say.day", weekday=t(lang, f"say.weekday.{d.weekday()}"), day=d.day,
                   month=t(lang, f"say.month.{d.month}")))
    if case == "all_safe":
        line = t(lang, "say.safest.all_safe", **kw)
    elif case == "some_safe":
        wins = sres["safe_windows"]
        if len(wins) == 1:                           # one SAFE window: say when to leave and when to be back
            a, b = wins[0]                           # (owner, 13 Nov 2026; the chat says the same in safest_bullets)
            back = (datetime.fromisoformat(b[:16]) + timedelta(hours=sres["trip_hours"])).isoformat(timespec="minutes")
        if len(wins) == 1 and a == b:                # one SAFE hour: said once, not listed and then repeated
            line = t(lang, "say.safest.only_one", time=say_at(lang, a, day), back=say_at(lang, back, day), **kw)
        else:
            line = t(lang, "say.safest.safe_windows", windows=_say_windows(lang, wins, day), **kw)
            if len(wins) == 1:
                line += " " + t(lang, "say.safest.leave_by", time=say_at(lang, b, day), back=say_at(lang, back, day))
    elif case == "caution_only":
        line = t(lang, "say.safest.no_safe_caution", windows=_say_windows(lang, sres["caution_windows"], day), **kw)
    else:
        line = t(lang, "say.safest.all_unsafe", **kw)
    if sres.get("unsafe_windows"):
        line += " " + t(lang, "say.safest.dont_leave", windows=_say_windows(lang, sres["unsafe_windows"], day))
    if sres.get("tomorrow"):                        # today is tight: tomorrow's SAFE times (13 Nov 2026)
        nxt = sres["tomorrow"]
        line += " " + t(lang, "say.safest.tomorrow", windows=_say_windows(lang, nxt["safe_windows"], nxt["search_from"][:10]))
    return f"{lead} {line}"


def safest_line(sres: dict, lang: str) -> str:
    """The departure-window answer for 'when is the safest time'. Never names a CAUTION or UNSAFE
    hour as the safest time."""
    kw = {"from": when(lang, sres["search_from"]), "to": when(lang, sres["search_to"]), "hours": sres["trip_hours"]}
    case = sres["case"]
    if case == "all_safe":
        return t(lang, "safest.all_safe", **kw)
    if case == "some_safe":
        line = t(lang, "safest.safe_windows", windows=_windows(lang, sres["safe_windows"]), **kw)
    elif case == "caution_only":
        line = t(lang, "safest.no_safe_caution", windows=_windows(lang, sres["caution_windows"]), **kw)
    else:
        line = t(lang, "safest.all_unsafe", **kw)
    # Always say plainly when NOT to leave: leaving the UNSAFE window out would be the wrong omission.
    if sres.get("unsafe_windows"):
        line += " " + t(lang, "safest.dont_leave",
                        windows=_windows(lang, sres["unsafe_windows"], style="dont", joiner="list.joiner_or"))
    if sres.get("tomorrow"):
        line += " " + t(lang, "chat.b.safest.tomorrow", safe=t(lang, "verdict.SAFE"),
                        windows=_windows(lang, sres["tomorrow"]["safe_windows"]))
    return line


def safest_bullets(sres: dict, lang: str) -> str:
    """'When should I leave?' for the chat: short bullets like a single trip (owner, 13 Nov 2026). The SAFE
    departure times; with one SAFE window, when to leave and when to be back; when NOT to leave; the replay
    label and the disclaimer. Same windows as safest_line(), so it never names a CAUTION or UNSAFE hour as
    the safest time."""
    shown = sres["shown"]
    kw = {"place": place_name(lang, shown["place"]), "hours": sres["trip_hours"],
          "from": when(lang, sres["search_from"]), "to": when(lang, sres["search_to"]),
          **{v.lower(): t(lang, f"verdict.{v}") for v in ("SAFE", "CAUTION", "UNSAFE")}}
    case = sres["case"]
    if case == "all_safe":
        lines = [t(lang, "chat.b.safest.all", **kw)]
    elif case == "some_safe":
        wins = sres["safe_windows"]
        if len(wins) == 1:                           # one window: say plainly when to leave and when to be back
            a, b = wins[0]
            back = (datetime.fromisoformat(b[:16]) + timedelta(hours=sres["trip_hours"])).isoformat(timespec="minutes")
        if len(wins) == 1 and a == b:                # one SAFE hour: one line, the time written once
            lines = [t(lang, "chat.b.safest.only_one", time=when(lang, a), back=_short_time(lang, back, a[:10]), **kw)]
        else:
            lines = [t(lang, "chat.b.safest.some", windows=_windows(lang, wins), **kw)]
            if len(wins) == 1:
                lines.append(t(lang, "chat.b.leave_by", time=_short_time(lang, b, a[:10]), back=_short_time(lang, back, a[:10])))
    elif case == "caution_only":
        lines = [t(lang, "chat.b.safest.caution", windows=_windows(lang, sres["caution_windows"]), **kw)]
    else:
        lines = [t(lang, "chat.b.safest.none", **kw)]
    if sres.get("unsafe_windows"):
        lines.append(t(lang, "safest.dont_leave",
                       windows=_windows(lang, sres["unsafe_windows"], style="dont", joiner="list.joiner_or")))
    if sres.get("tomorrow"):                        # today is tight: tomorrow's SAFE times (13 Nov 2026)
        lines.append(t(lang, "chat.b.safest.tomorrow", safe=kw["safe"], windows=_windows(lang, sres["tomorrow"]["safe_windows"])))
    lines.append(t(lang, "chat.b.disclaimer"))
    return "\n".join("• " + x for x in lines)


def error_text(err: dict, lang: str) -> str:
    cfg = load_app()
    key = f"error.{err.get('error', 'generic')}"
    if key not in load_translations("en"):
        key = "error.generic"
    return t(lang, key, hours=cfg["forecast"]["window_hours"], max=cfg["trip"]["max_hours"])


def how_we_decide(lang: str) -> dict:
    """Data for the 'How we decide' panel: every threshold with its source, plus our own rules."""
    th = load_thresholds()
    cfg = load_app()
    rows = []
    for name, p in th["parameters"].items():
        unit = t(lang, f"unit.{p['unit']}") if "unit" in p else ""
        caution, unsafe = p["caution"], p.get("unsafe")
        rows.append({
            "param": t(lang, f"param.{name}"),
            "caution": t(lang, "how.any") if p["direction"] == "codes" else
                       f"{'≤' if p['direction'] == 'below' else '≥'} {caution['value']} {unit}",
            "unsafe": f"≥ {unsafe['value']} {unit}" if unsafe else t(lang, "how.no_unsafe_line"),
            "sources": [{"level": lvl, "title": th["sources"][x["source"]]["title"],
                         "url": th["sources"][x["source"]]["url"], "where": x["where"], "note": x["note"]}
                        for lvl, x in (("caution", caution), ("unsafe", unsafe)) if x],
        })
    return {
        "intro": t(lang, "how.intro"), "boat": t(lang, "how.boat"), "rows": rows,
        "rules": [t(lang, "how.rule_worst"),
                  t(lang, "how.rule_margin", pct=round(th["near_line_margin"] * 100)),
                  t(lang, "how.rule_missing", hours=cfg["forecast"]["stale_after_hours"]),
                  t(lang, "how.rule_thunder"), t(lang, "how.rule_display")],
        "own_rules": [False, True, True, True, False],
    }
