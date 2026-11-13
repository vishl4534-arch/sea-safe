"""Tool schemas for the language model (chat now, voice agent later).
Every parameter is required; nothing is optional or nullable; no extra properties.
That keeps tool calls identical on Gemini and Groq.

The model never writes a date. It says a day word ("today", "tomorrow", ...) and an hour; code turns that
into the exact date (see resolve_day), because models got "tomorrow" wrong just after midnight."""
from datetime import datetime, timedelta

DAYS = ["today", "tomorrow", "day_after_tomorrow"]
OUTSIDE = ["past", "later"]          # yesterday / next week: code answers "already passed" / "next 48 hours only"
RANGES = DAYS + ["next_48_hours"]
DETAILS = ["all", "rain", "air_temperature", "sea_temperature", "wind_direction", "waves", "sun"]
FAQ_TOPICS = ["verdicts", "how_decided", "sources", "near_line", "boats", "accuracy", "data_source",
              "missing_data", "memory", "limits"]

# Kept for the HTTP routes and their callers, which pass exact local times.
TIME_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:00(:00)?$"


def day_dates(now: datetime) -> dict:
    """What each day word means, decided by code. Between midnight and 04:00 people asking about
    'tomorrow' mean the coming morning, which is already today's date."""
    base = now.date() - timedelta(days=1) if now.hour < 4 else now.date()
    return {"today": now.date(), "tomorrow": base + timedelta(days=1), "day_after_tomorrow": base + timedelta(days=2)}


def resolve_day(day: str, hour: int, now: datetime) -> str:
    """'tomorrow', 5 -> '2026-11-14T05:00' (local)."""
    d = day_dates(now)[day]
    return f"{d.isoformat()}T{int(hour):02d}:00"


# A trip the model may report but the app cannot check: it is refused, never shortened (audit 13 Nov 2026).
REPORT_MAX_HOURS = 168


def return_is_next_day(departure: str, back_hour: int) -> bool:
    """True if 'back by <hour>' can only mean a later day than the departure day. The tools carry no
    return day, so 'leave 5 pm, back 9 am tomorrow' would otherwise read as back at 21:00 the same day.
    Such trips are refused (the fisher is asked for the trip length in hours instead)."""
    dep = datetime.fromisoformat(departure)
    back = dep.replace(hour=0) + timedelta(hours=dep.hour + trip_from_return(departure, back_hour))
    return back.date() != dep.date()


def trip_from_return(departure: str, back_hour: int) -> int:
    """'Back by 9' after a 14:00 departure is 21:00 -> 7 hours. The return is the first matching clock time
    after departure (9 or 21 when no am/pm is clear); code does this arithmetic, not the model."""
    dep = datetime.fromisoformat(departure)
    options = [back_hour] if back_hour >= 12 else [back_hour, back_hour + 12]
    for day_offset in (0, 1):
        for h in sorted(options):
            t = dep.replace(hour=0) + timedelta(days=day_offset, hours=h)
            if t > dep:
                return int((t - dep).total_seconds() // 3600)
    return 0


def resolve_range(day: str, now: datetime, window_end: datetime) -> tuple[str, str]:
    """The departure range for 'when is the safest time': a whole day, or the whole forecast window."""
    if day == "next_48_hours":
        return now.strftime("%Y-%m-%dT%H:00"), window_end.strftime("%Y-%m-%dT%H:00")
    d = day_dates(now)[day].isoformat()
    return f"{d}T00:00", f"{d}T23:00"


def schemas(place_ids: list[str], max_hours: int) -> list[dict]:
    place = {"type": "string", "enum": place_ids,
             "description": "Harbour id, or 'map_point' for the point the user tapped on the map."}
    hours = {"type": "integer", "minimum": 1, "maximum": REPORT_MAX_HOURS,
             "description": "How many hours the boat will be out (departure to return), exactly as the user said "
                            f"it, even if it is more than {max_hours} (the app explains its limit). For a range "
                            "('2-3 hours') use the longest; round part hours up ('2 and a half' -> 3)."}
    back_day = {"type": "string", "enum": ["same"] + DAYS + ["later"],
                "description": "The day the user said they will be BACK, as a day word: 'leave today at 5 pm, back "
                               "tomorrow at 9' -> tomorrow; 'back the next morning' after leaving today -> tomorrow. "
                               "'same' if they come back on the day they leave, or said no return day."}
    minute = {"type": "integer", "minimum": 0, "maximum": 59,
              "description": "The minutes of the DEPARTURE time ('5:30' -> 30, 'quarter past 5' -> 15, 'around 4:10' "
                             "-> 10). 0 if it is on the hour or no time was said. For a range ('4 or 4:30') use the "
                             "earliest."}
    back_minute = {"type": "integer", "minimum": 0, "maximum": 59,
                   "description": "The minutes of the RETURN time ('back by 6:30' -> 30). 0 if on the hour or no "
                                  "return time. For a range ('back by 6-6:30') use the latest."}
    given = {"type": "boolean",
             "description": "true only if the user stated the trip length or return time; false if you used the default."}
    day = {"type": "string", "enum": ["same"] + DAYS + OUTSIDE,
           "description": "Which day the boat leaves, as the user said it. 'same' if the user did not say a day "
                          "(the app keeps the previous one). 'past' for any day before today (yesterday...), "
                          "'later' for any day after day_after_tomorrow (next week...)."}
    back = {"type": "integer", "minimum": -1, "maximum": 23,
            "description": "The hour the user said they will be BACK ('back by 9' -> 9, 'back by noon' -> 12), "
                           "or -1 if they did not say a return time. The app works out the trip length from it."}
    hour = {"type": "integer", "minimum": -1, "maximum": 23,
            "description": "Departure hour, 24-hour clock (5 = 05:00), or -1 if the user did not say a departure "
                           "time (the app keeps the previous one)."}
    return [
        {"type": "function", "function": {
            "name": "assess_trip",
            "description": "Check whether a trip from a place at a departure time is SAFE, CAUTION or UNSAFE. "
                           "Call this for every question about conditions, safety, a time of day, or 'why'.",
            "parameters": {"type": "object", "additionalProperties": False,
                           "required": ["place", "day", "hour", "minute", "back_by_hour", "back_by_minute", "back_day",
                                        "trip_hours", "trip_length_given_by_user"],
                           "properties": {"place": place, "day": day, "hour": hour, "minute": minute,
                                          "back_by_hour": back, "back_by_minute": back_minute, "back_day": back_day,
                                          "trip_hours": hours, "trip_length_given_by_user": given}}}},
        {"type": "function", "function": {
            "name": "weather_details",
            "description": "Weather details for a trip: rain, air and sea temperature, wind direction, wave direction "
                           "and period, sunrise and sunset, plus the trip's safety check. Use for questions about "
                           "these details. Same place, day and hour rules as assess_trip.",
            "parameters": {"type": "object", "additionalProperties": False,
                           "required": ["detail", "place", "day", "hour", "minute", "back_by_hour", "back_by_minute",
                                        "back_day", "trip_hours", "trip_length_given_by_user"],
                           "properties": {"detail": {"type": "string", "enum": DETAILS,
                                                     "description": "The one detail asked about ('sunset?' -> sun, "
                                                                    "'will it rain?' -> rain), or all."},
                                          "place": place, "day": day, "hour": hour, "minute": minute,
                                          "back_by_hour": back, "back_by_minute": back_minute, "back_day": back_day,
                                          "trip_hours": hours, "trip_length_given_by_user": given}}}},
        {"type": "function", "function": {
            "name": "explain_app",
            "description": "Reviewed answers about the app itself: what the verdicts mean, how it decides, where the "
                           "lines come from, the near-line rule, which boats, how far to trust a forecast, where the "
                           "data comes from, replay, missing data, what it remembers, and what it cannot check.",
            "parameters": {"type": "object", "additionalProperties": False, "required": ["topic"],
                           "properties": {"topic": {"type": "string", "enum": FAQ_TOPICS}}}}},
        {"type": "function", "function": {
            "name": "official_info",
            "description": "Where to find official weather warnings, and emergency contacts at sea.",
            "parameters": {"type": "object", "additionalProperties": False, "required": ["topic"],
                           "properties": {"topic": {"type": "string", "enum": ["warnings", "emergency"]}}}}},
        {"type": "function", "function": {
            "name": "check_all_harbours",
            "description": "Check EVERY harbour in the region at one departure time and list which are SAFE, CAUTION "
                           "and UNSAFE. Use for 'which harbours are safe', 'where can I go', 'is any harbour safe'.",
            "parameters": {"type": "object", "additionalProperties": False,
                           "required": ["day", "hour", "minute", "trip_hours", "trip_length_given_by_user"],
                           "properties": {"day": day, "hour": hour, "minute": minute, "trip_hours": hours,
                                          "trip_length_given_by_user": given}}}},
        {"type": "function", "function": {
            "name": "find_safest_time",
            "description": "Check every departure hour in a range and return the SAFE, CAUTION and UNSAFE "
                           "departure windows (code decides; never a single 'best' hour). "
                           "Use for 'when is the safest time', and for 'will it get worse / stay safe today?'.",
            "parameters": {"type": "object", "additionalProperties": False,
                           "required": ["place", "day", "trip_hours", "trip_length_given_by_user"],
                           "properties": {
                               "place": place,
                               "day": {"type": "string", "enum": RANGES + OUTSIDE,
                                       "description": "The day to search, or next_48_hours if no day was given; "
                                                      "'past' / 'later' for days outside the forecast."},
                               "trip_hours": hours, "trip_length_given_by_user": given}}}},
    ]
