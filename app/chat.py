"""Conversational chat. The model reads the question and calls the assessment tools;
the reply the user reads is the model's one short sentence (checked by a guard) followed
by the templated verdict, reasons and numbers from app/explain.py."""
import json
import logging
import re
from datetime import datetime

from app import explain, llm, service
from app.config import load_app, load_translations, region as get_region
from app.tools import (OUTSIDE, TIME_PATTERN, day_dates, resolve_day, resolve_range, return_is_next_day, schemas,
                       trip_from_return)

log = logging.getLogger("seasafe.chat")
MAX_TOOL_ROUNDS = 4


def _system_prompt(region: dict, lang: str, mode: str, map_point, context: dict | None, page: dict | None) -> str:
    cfg = load_app()
    clock = service.clock_info(region["id"], mode)
    now = datetime.fromisoformat(clock["now"])
    harbours = "\n".join(f"- {h['id']}: {explain.t('en', 'place.' + h['id'])} / {explain.t(lang, 'place.' + h['id'])}"
                         + (f" (also called: {', '.join(h['aliases'])})" if h.get("aliases") else "")
                         for h in region["harbours"])
    page = page or {}
    ids = {h["id"] for h in region["harbours"]}
    dep = page.get("departure") if page.get("departure", "") >= clock["now"] else clock["default_departure"]
    hours = page.get("trip_hours") or cfg["trip"]["default_hours"]
    given = bool(page.get("trip_length_given_by_user"))
    dates = day_dates(now)

    def as_day(ts):  # "2026-11-13T05:00" -> "day=tomorrow hour=5", the words the tools take
        if not ts:
            return "none"
        words = [w for w, d in dates.items() if d.isoformat() == ts[:10]]
        return f"day={words[-1] if words else 'out of range'} hour={int(ts[11:13])}"
    on_screen = (f"The harbour selected on screen is '{page['place']}'." if page.get("place") in ids
                 else "No harbour is selected on screen.")
    last = (f"The previous check was: place={context.get('place')}, departure {as_day(context.get('departure'))}, "
            f"trip_hours={context.get('trip_hours')}, trip_length_given_by_user={context.get('given')}."
            if context else "There is no previous check yet.")
    max_hours = cfg["trip"]["max_hours"]
    lc = cfg["languages"][lang]
    lang_name = f"{lc.get('english_name', lc['name'])} ({lc['name']})"
    replay = (f"\nTHIS IS A REPLAY of recorded weather on {clock['replay']['date']}. Treat that date as today."
              if clock["replay"] else "")
    # Small talk is shown (and spoken) only if it passes the word guard, so the model is told the words of THIS
    # language that the guard blocks; otherwise a friendly Kannada or Arabic reply would be replaced by a list.
    banned = ", ".join(dict.fromkeys(w.strip() for w in load_translations(lang).get("guard.words", "").split(",")
                                     if w.strip()))
    style = {"kn": "everyday spoken Kannada as people talk on the Karnataka coast (simple words, no formal or "
                   "bookish Kannada), e.g. \"ನಮಸ್ಕಾರ! ನಾನು ಚೆನ್ನಾಗಿದ್ದೇನೆ, ಧನ್ಯವಾದ. ಇವತ್ತು ಯಾವ ಬಂದರಿನಿಂದ, ಎಷ್ಟು "
                   "ಹೊತ್ತಿಗೆ ಹೊರಡುತ್ತೀರಿ, ಎಷ್ಟು ಗಂಟೆ ಸಮುದ್ರದಲ್ಲಿ ಇರುತ್ತೀರಿ?\"",
             "ar": "simple, warm Arabic that Gulf fishers understand (light Modern Standard Arabic, common Gulf "
                   "words are fine), e.g. \"وعليكم السلام! الحمد لله بخير. من أي ميناء بتطلع، ومتى، وكم ساعة؟\". "
                   "Answer \"السلام عليكم\" with \"وعليكم السلام\"",
             }.get(lang, "plain, friendly English")
    return f"""You help small-scale fishers decide whether to take a small boat to sea.
Region: {explain.t('en', 'region.' + region['id'])}. Local time now: {now:%A %Y-%m-%d %H:00}.{replay}
You can check departures from now until {clock['window_end']} (the next {cfg['forecast']['window_hours']} hours).
Harbours (id: English / local name):
{harbours}
{"The user has tapped a point on the map; use place 'map_point' when they mean that point." if map_point else "No map point is selected."}
{on_screen}
{f"On screen now: departure {as_day(dep)}, trip length {hours} hours (trip_length_given_by_user={str(given).lower()})." if page.get("departure") else "Nothing about the time or trip length is chosen on screen: only the user's words count."}
Day words (the app turns them into dates): today = {dates['today']:%a %d %b}, tomorrow = {dates['tomorrow']:%a %d %b},
day_after_tomorrow = {dates['day_after_tomorrow']:%a %d %b}. Just after midnight "tomorrow" still means the coming morning.
{last}

RULES
0. Conversation: greetings and small talk ("hi", "hello, how are you?", "hi I'm Vish, how are you?", "thanks",
   "ನಮಸ್ಕಾರ", "ಹೇಗಿದ್ದೀರಾ?", "ಧನ್ಯವಾದ", "السلام عليكم", "كيف حالك؟", "شكراً") get a reply WITHOUT a tool: warm,
   natural and short (at most 2 short sentences) in {lang_name}, written in {style}. Use their name if they give
   it. Then invite them to say where they will go out from, when they leave, and for how long. Never say anything
   about the sea, weather or whether to go without a tool; do not use the words safe, unsafe, caution, calm or
   rough (except in your name), and in {lang_name} never use any of these words, not even inside a longer word or a
   blessing: {banned}. Never write a number, a time or a date without a tool: for "when will I be back?" call
   assess_trip. If asked your name or who you are: you are "the Sea Safe assistant", here to help fishers
   check a trip before they go.
1. For ANY question about the sea, weather, safety, a time, or "why", call a tool. Never answer from your own knowledge.
   - "Can I go / is it safe / is it ok at <time>?" -> assess_trip at that time. In Kannada "ಹೋಗಬಹುದಾ?",
     "ಹೇಗಿದೆ?"; in Arabic "هل أقدر أطلع؟", "هل الخروج آمن؟" - these are ALWAYS assess_trip, also with "tomorrow night".
   - A new time ("what about the afternoon?") -> call assess_trip again with the new departure, same place.
   - "Why?" or "why is it unsafe?" -> call assess_trip again with exactly the previous arguments.
   - Doubt about an answer - "are you sure?", "really?", "can I trust this?", "ಖಚಿತವಾ?", "متأكد؟" ->
     explain_app(topic=accuracy). NOT assess_trip: the answer is already on screen.
   - "Which harbours are safe / where can I go / is any harbour safe at <time>?" -> check_all_harbours at that
     time. NEVER answer a question about several or all harbours by checking one harbour you picked yourself.
   - Weather details - rain, air or sea temperature, wind direction, where the waves come from, wave period,
     sunrise, sunset ("will it rain?", "how hot is it?", "ಮಳೆ ಬರುತ್ತಾ?", "هل بتمطر؟", "متى الغروب؟") ->
     weather_details, with the same place, day and hour rules as assess_trip, and detail = the one thing asked
     (sunset -> sun, rain -> rain, sea temperature -> sea_temperature), or all if they ask for the weather in general.
   - Tides, currents, where the fish are ("tides?", "ಉಬ್ಬರವಿಳಿತ ಹೇಗಿದೆ?", "المد والجزر؟") -> explain_app(topic=limits).
     The app has no tide data: never answer these with weather_details.
   - Questions about the app itself -> explain_app with the topic: what SAFE / CAUTION / UNSAFE mean = verdicts;
     how it decides or which numbers = how_decided; where the lines come from = sources; why caution when a value is
     only close = near_line; which boats = boats; how accurate, can I trust it = accuracy; where the data comes from =
     data_source; what if there is no data = missing_data; what it remembers = memory;
     tides, currents, fish or anything else it cannot check = limits.
   - Official warnings, emergencies, coast guard, who to call -> official_info.
   - ONLY when the user asks WHEN to go ("when is the safest / best time", "ಯಾವಾಗ", "متى") -> find_safest_time with
     day = the day the user means (today / tomorrow / day_after_tomorrow), or next_48_hours if they name no day.
   - A day before today (yesterday) -> day = past. A day after day_after_tomorrow (next week) -> day = later.
     Still call the tool; the app explains the limit.
   - A part of the day ("tonight", "tomorrow night", "ನಾಳೆ ರಾತ್ರಿ", "بكرة بالليل") is ONE departure time
     (night = 21), so it is assess_trip, never find_safest_time. Examples:
       "ನಾಳೆ ರಾತ್ರಿ ಕಾರವಾರದಿಂದ ಹೋಗಬಹುದಾ?" -> assess_trip(place=karwar, day=tomorrow, hour=21)
       "هل أقدر أطلع من دبا بكرة بالليل؟" -> assess_trip(place=dibba_al_hisn, day=tomorrow, hour=21)
       "can I go from Malpe tomorrow night?" -> assess_trip(place=malpe, day=tomorrow, hour=21)
       "ಇವತ್ತು ಹೋಗಲು ಒಳ್ಳೆಯ ಸಮಯ ಯಾವುದು?" / "متى أفضل وقت؟" / "when is the best time?" -> find_safest_time
   - Questions about how the day goes - "will it get worse today?", "will it stay safe?", "is it safe all day?",
     "how is the rest of the day?", "ಇವತ್ತು ಹವಾಮಾನ ಹದಗೆಡುತ್ತಾ?", "هل الجو بيسوء اليوم؟", "بيظل آمن طول اليوم؟" ->
     find_safest_time for that place and day (it shows every departure time of the day). NOT assess_trip.
       "would the conditions become worse today, or is it always safe?" -> find_safest_time(place=<previous>, day=today)
   - When they will be back ("what time do I come back by?", "when will I be back?", "ಯಾವಾಗ ವಾಪಸ್?", "متى أرجع؟")
     -> assess_trip for the trip being talked about (same place, departure and length). NOT weather_details,
     NOT find_safest_time.
2. Times: give the day as the word the user used (today / tomorrow / day_after_tomorrow) and the hour, 24-hour clock.
   Never work out a date yourself. morning = 5, afternoon = 14, evening = 17, night = 21 unless the user gives an hour.
   "5 tomorrow" with no am/pm means hour 5. If the user says only a time ("at 6"), the day is today if that hour is
   still ahead, else tomorrow.
   If the user gives NO departure time ("back by 9", "what about Mangalore?", "why?", "can I go from Malpe?"),
   send hour = -1 and day = "same": the app keeps the previous departure, or asks the user for it.
   Do not repeat an old time yourself, never guess a time, and do not ask for it yourself: call the tool.
3. Trip length: if the user says HOW LONG ("for 8 hours"), use that and set trip_length_given_by_user=true.
   If the user says when they will be BACK ("back by 9", "ನಾನು 9 ಗಂಟೆಗೆ ವಾಪಸ್", "برجع الساعة 9"), put that hour in
   back_by_hour and keep the previous departure; the app works out the length. Otherwise back_by_hour = -1,
   trip_length_given_by_user=false and trip_hours={hours}: the app keeps the previous length, or asks the user.
   Never guess a length and do not ask for it yourself: call the tool.
   If they say the DAY they will be back ("back tomorrow at 9"), put it in back_day. Give trip_hours exactly as
   said, even above {max_hours}; put departure minutes ("4:10") in minute and return minutes ("back by 6:30") in
   back_by_minute. Approximate answers are fine: "around 4:10, 2-3 hours, back by 6-6:30" -> hour 16, minute 10,
   trip_hours 3 (the longest), back_by_hour 18, back_by_minute 30 (the latest). The app checks every hour they cover.
4. Place: match names loosely - spelling mistakes, town names and the "also called" names above all count
   ("Kundapura" -> gangolli, "Mangalore" -> mangaluru). If the user names no place, use the previous check's place,
   else the harbour selected on screen. Only if there is still no place, reply without a tool (the app then asks
   which harbour).
   If the user DOES name a place but you cannot match it to a harbour above (a misheard or unknown name), NEVER
   use the previous place instead: reply without a tool, so the app asks which harbour.
5. After a tool result, write ONE short sentence (max 15 words) in {lang_name}, even if the user wrote in another language. It only
   introduces the result, e.g. "Here is the check for Malpe, tomorrow morning." The app adds the verdict, reasons and
   numbers itself. Do NOT write any number, any verdict word (safe/unsafe/caution), or any weather description.
6. Never say anything is safe. Never give advice of your own."""


def _forbidden_words() -> list[str]:
    words = []
    for lang in load_app()["languages"]:
        tr = load_translations(lang)
        words += [w.strip() for w in tr.get("guard.words", "").split(",") if w.strip()]
        words += [tr[f"verdict.{v}"] for v in ("SAFE", "CAUTION", "UNSAFE")]
    return words


def _contains_word(text: str, word: str) -> bool:
    if word.isascii():
        return re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is not None
    return word in text  # Kannada and Arabic: plain substring


def guard(text: str | None, after_tool: bool) -> str | None:
    """Return the model's text if it is allowed, else None (a templated sentence is used instead).
    After a tool call: no digits and no verdict/weather words, so numbers and verdicts only come from code.
    (\\d also matches Arabic-Indic and Kannada digits.)"""
    text = (text or "").strip()
    if not text or len(text) > (200 if after_tool else 300):
        return None
    if after_tool and re.search(r"\d", text):
        return None
    plain = re.sub(r"sea\s*safe", " ", text, flags=re.IGNORECASE)    # the app's own name is not a verdict
    if any(_contains_word(plain, w) for w in _forbidden_words()):
        return None
    return text


def _place_terms(region: dict) -> dict:
    """Every name a harbour is called by (all languages, aliases) -> harbour id. Names shared by several
    harbours ("Dubai", "ميناء") and very short ones are left out, so a match is never ambiguous."""
    seen = {}
    for h in region["harbours"]:
        names = [explain.t(lang, f"place.{h['id']}") for lang in load_app()["languages"]] + h.get("aliases", [])
        for name in names:
            for part in name.replace("–", ",").split(","):
                part = part.strip().lower()
                if len(part) >= 3:
                    seen.setdefault(part, set()).add(h["id"])
    return {term: ids.pop() for term, ids in seen.items() if len(ids) == 1}


def mentioned_harbours(text: str, region: dict) -> set:
    """Harbours named in the user's own words. Substring match, so joined forms count: Arabic "ودبا"
    (and Dibba), Kannada "ಮಲ್ಪೆಯಿಂದ" (from Malpe). Latin names must match whole words."""
    text = (text or "").lower()
    found = set()
    for term, hid in _place_terms(region).items():
        hit = re.search(rf"\b{re.escape(term)}\b", text) if term.isascii() else term in text
        if hit:
            found.add(hid)
    return found


# ---- a trip length the user said, read by code ("a six-hour trip" once came back as "we assumed") ----
_EN_NUM = {w: i for i, w in enumerate("one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                      "fifteen sixteen seventeen eighteen nineteen twenty".split(), 1)}
_KN_NUM = {"ಒಂದು": 1, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5, "ಆರು": 6, "ಏಳು": 7, "ಎಂಟು": 8, "ಒಂಬತ್ತು": 9,
           "ಹತ್ತು": 10, "ಹನ್ನೊಂದು": 11, "ಹನ್ನೆರಡು": 12}
# Arabic counts, written and spoken (Gulf "تلات", "اثنعش"). A trailing ة ("خمسة ساعات") is allowed by the pattern.
_AR_NUM = {"إحدى عشرة": 11, "احدى عشرة": 11, "احدعش": 11, "حداش": 11, "اثنتي عشرة": 12, "اثنا عشر": 12,
           "اثنعش": 12, "اطنعش": 12, "ثلاث": 3, "تلات": 3, "تلاث": 3, "أربع": 4, "اربع": 4, "خمس": 5, "ست": 6,
           "سبع": 7, "ثماني": 8, "ثمان": 8, "تسع": 9, "عشر": 10}
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩೦೧೨೩೪೫೬೭೮೯", "01234567890123456789")
_N = r"(\d{1,2}|%s)"
_DURATION = [
    # English: "6 hours", "six-hour trip", "for 8 hrs". A clock time ("at 6") has no "hour" after it.
    # It must start a word, so "twenty-four hours" is not read as 4 (that one is left to the model).
    (re.compile(r"(?<![\w-])" + _N % "|".join(_EN_NUM) + r"[\s-]*(?:hours?|hrs?)\b", re.I), _EN_NUM),
    # Kannada: "6 ಗಂಟೆಗಳ", "ಆರು ಗಂಟೆಯ ಪ್ರಯಾಣ", "6 ಗಂಟೆ ಕಾಲ", "6 ಗಂಟೆ ಸಮುದ್ರದಲ್ಲಿ ಇರುತ್ತೇನೆ" (the answer to
    # chat.ask_length), "6 ಗಂಟೆ ಹೊತ್ತು", and the coastal word "ತಾಸು" ("6 ತಾಸು"). Not "6 ಗಂಟೆಗೆ" (at 6 o'clock).
    (re.compile(_N % "|".join(_KN_NUM) + r"\s*(?:[ಗಘ]ಂಟೆ(?:ಗಳು|ಗಳ|ಯ\s*ಪ್ರಯಾಣ|\s*ಪ್ರಯಾಣ|\s*ಕಾಲ|\s*ಹೊತ್ತು|\s*ಸಮುದ್ರದಲ್ಲಿ)"
                r"|ತಾಸು|ತಾಸಿನ|ತಾಸ್)"), _KN_NUM),
    # Arabic: "6 ساعات", "ست ساعات", "خمسة ساعات", "لمدة 8 ساعة". A clock time is "الساعة 6": the number comes after.
    (re.compile(_N % "|".join(_AR_NUM) + r"ة?\s*ساع(?:ات|ة)"), _AR_NUM),
]
_AR_TWO = re.compile(r"ساعتين|ساعتان")
_AR_ONE = re.compile(r"ساعة\s*(?:واحدة|وحدة)")


def stated_trip_hours(text: str) -> int | None:
    """The trip length in the user's own words, or None. Only clear durations count; clock times do not."""
    text = (text or "").translate(_DIGITS)
    for pattern, words in _DURATION:
        m = pattern.search(text)
        if m:
            n = m.group(1).lower()
            return int(n) if n.isdigit() else words.get(n)
    return 2 if _AR_TWO.search(text) else 1 if _AR_ONE.search(text) else None


# A part of the day the user said, read by code when the model sends no hour (Groq once answered
# "will it rain at Khor Fakkan this afternoon?" for now). Same hours as the prompt: morning 5, afternoon 14,
# evening 17, night 21. Greetings ("good morning", "صباح الخير", "مساء الخير") do not count.
_GREETINGS = re.compile(r"good (morning|afternoon|evening|night)|صباح الخير|صباح النور|مساء الخير|مساء النور"
                        r"|ಶುಭ\s*ರಾತ್ರಿ|ಶುಭೋದಯ|ಶುಭ\s*ಸಂಜೆ|ಶುಭ\s*ಮಧ್ಯಾಹ್ನ", re.I)
# Midnight is not "night" (21:00): Kannada ಮಧ್ಯರಾತ್ರಿ and Arabic منتصف الليل contain the night word, so they are
# taken out first and the hour is left to the model, as for English "midnight".
_MIDNIGHT = re.compile(r"ಮಧ್ಯ\s*ರಾತ್ರಿ|منتصف\s*الليل|نص\s*الليل")
_PARTS = [
    (re.compile(r"\b(morning|dawn)\b|ಬೆಳಿಗ್ಗೆ|ಬೆಳಗ್ಗೆ|ಬೆಳಗಿನ ಜಾವ|ಮುಂಜಾನೆ|ನಸುಕಿನ|الصبح|صباح|الفجر|فجر", re.I), 5),
    (re.compile(r"\b(afternoon|noon)\b|ಮಧ್ಯಾಹ್ನ|ಮದ್ಯಾಹ್ನ|الظهر|ظهرا|ظهراً|العصر", re.I), 14),
    (re.compile(r"\bevening\b|ಸಂಜೆ|ಸಾಯಂಕಾಲ|المسا|مساء|المغرب|العشية", re.I), 17),
    (re.compile(r"\b(tonight|night)\b|ರಾತ್ರಿ|الليل|بالليل|الليلة|ليلا|ليلاً|ليل\b", re.I), 21),
]


def stated_part_of_day(text: str) -> int | None:
    text = _MIDNIGHT.sub(" ", _GREETINGS.sub(" ", text or ""))
    hits = {hour for pattern, hour in _PARTS if pattern.search(text)}
    return hits.pop() if len(hits) == 1 else None          # "morning or evening?" is left to the model


# A clock time with minutes that are not :00, read by code as well as by the model (the tools take whole
# hours only). "5:30", "05:45", "5.30 pm", "half past", "quarter to", Arabic "ونص" / "وربع" / "إلا ربع",
# Kannada "ಐದೂವರೆ" (five and a half), "ಮುಕ್ಕಾಲು" (three quarters). A plain decimal ("1.25 m") does not count.
_MINUTES = re.compile(r"\b\d{1,2}:(?!00\b)\d{2}\b|\b\d{1,2}\.(?!00\b)\d{2}\s*(?:am|pm|a\.m|p\.m)"
                      r"|\b(?:half|quarter)\s+(?:past|to)\b|و\s?نص|و\s?ربع|والنصف|والربع|و\s?ثلث|[إا]لا\s?(?:ربع|ثلث)"
                      r"|ೂವರೆ|(?<!ಮುಂದ)ುವರೆ|ಮುಕ್ಕಾಲು", re.I)    # Kannada "ಐದೂವರೆ" and the common "ಐದುವರೆ"


def stated_minutes(text: str) -> bool:
    """True if the user's words give a time that is not on the hour."""
    return bool(_MINUTES.search((text or "").translate(_DIGITS)))


# Arabic المد / الجزر as whole words only: "كم المدة؟" (how long?) and "المدينة" (the city) are not tides.
_TIDES = re.compile(r"\btides?\b|\btidal\b|high tide|low tide|ಉಬ್ಬರ|ಇಳಿತ|\bالمد\b|\bالجزر\b|مد\s*و\s*جزر", re.I)


# Doubt about the answer just given ("are u sure?", "really?", "ಖಚಿತವಾ?", "متأكد؟"). Only a short question with
# no time and no harbour in it counts: "are you sure it's safe at 5 from Malpe?" is a new check.
_SURE = re.compile(r"\b(are\s+(you|u)\s+sure|(you|u)\s+sure|sure\s*\?|really\s*\?|for\s+real|can\s+i\s+trust|"
                   r"how\s+sure|how\s+accurate|is\s+(that|this|it)\s+(right|correct|true))|ಖಚಿತ|ನಿಜವಾ|ನಿಜಾನಾ|"
                   r"ಪಕ್ಕಾ|ಗ್ಯಾರಂಟಿ|ಖಾತ್ರಿ|ಸರಿಯಾಗಿದೆಯಾ|"
                   r"متأكد|متاكد|أكيد|اكيد|صدق\b|صحيح\s*؟|بجد|عن\s*جد|جد\s*؟|يقين", re.I)


def asks_if_sure(text: str, region: dict | None = None) -> bool:
    text = (text or "").strip()
    if not _SURE.search(text) or re.search(r"\d", text.translate(_DIGITS)) or len(text.split()) > 8:
        return False
    return not (region and mentioned_harbours(text, region))


def asks_about_tides(text: str) -> bool:
    """Tides are something the app cannot check (no tide data). Matched in code, in all three languages."""
    return bool(_TIDES.search(text or ""))


def _departure(args: dict, now: datetime, context: dict, page: dict, clock: dict) -> str:
    """The exact departure. 'same' day / hour -1 mean "not said": code keeps the previous check's departure,
    else the one on screen, so the model never has to remember an earlier time."""
    base = context.get("departure") or ((page or {}).get("departure") if (page or {}).get("departure", "") >= clock["now"]
                                        else None) or clock["default_departure"]
    hour = int(args.get("hour", -1))
    if args.get("day", "same") == "same":
        return base if hour < 0 else f"{base[:10]}T{hour:02d}:00"
    return resolve_day(args["day"], hour if hour >= 0 else int(base[11:13]), now)


def _trip_length(args: dict, stated: int | None, context: dict, page: dict | None = None) -> tuple[int, bool]:
    """(hours, given by the user). The user's own words win ("a six-hour trip"). A length the user chose
    earlier stays theirs: if the model sends it again, or falls back to the default (it once answered a
    "when" question for 6 hours right after the fisher said "a four-hour trip"). The same goes for a length chosen
    on screen, or remembered on the fisher's phone."""
    hours, given = int(args["trip_hours"]), bool(args["trip_length_given_by_user"])
    if stated:
        return stated, True
    default = load_app()["trip"]["default_hours"]
    for chosen in (context, page or {}):
        if chosen.get("given") and hours in (chosen.get("trip_hours"), default):
            return int(chosen["trip_hours"]), True
    return hours, given


def _unsupported_trip(name: str, args: dict, stated: int | None, user_text: str, dep: str | None,
                      now: datetime | None = None) -> str | None:
    """A trip the app cannot check exactly. It is refused with a templated message: never rounded to the
    hour, cut short or capped, which would answer for a different trip (audit 13 Nov 2026, items 1-2)."""
    if name not in ("assess_trip", "weather_details", "check_all_harbours", "find_safest_time"):
        return None
    max_hours = load_app()["trip"]["max_hours"]
    if (stated and stated > max_hours) or int(args.get("trip_hours", 1)) > max_hours:
        return "bad_trip_length"
    back_day = args.get("back_day", "same")
    if dep and back_day not in (None, "same"):            # "back tomorrow at 9": a return on a later day
        if back_day == "later" or (now and day_dates(now)[back_day].isoformat() > dep[:10]):
            return "trip_overnight"
    if dep and int(args.get("back_by_hour", -1)) >= 0 and return_is_next_day(dep, int(args["back_by_hour"])):
        return "trip_overnight"
    return None


def _missing(name: str, args: dict, stated: int | None, context: dict, page: dict | None) -> list[str]:
    """Which trip details the user has not given yet: "time" (departure) and "length". Nothing is assumed:
    a detail counts only if the user said it now, or it is known from the previous turns of this
    conversation (or chosen on screen by an older page). The app then asks for it (a reviewed template)."""
    if name not in ("assess_trip", "weather_details", "check_all_harbours", "find_safest_time"):
        return []
    page = page or {}
    need = []
    if name != "find_safest_time":
        if not (int(args.get("hour", -1)) >= 0 or context.get("departure") or page.get("departure")):
            need.append("time")
    said_length = (stated is not None or bool(args.get("trip_length_given_by_user"))
                   or int(args.get("back_by_hour", -1)) >= 0 or bool(context.get("given") and context.get("trip_hours"))
                   or bool(page.get("trip_length_given_by_user")))
    if not said_length:
        need.append("length")
    return need


# What each missing detail is, for the model that words the question (code decides what is missing).
_ASK_FOR = {"time": "what time they will leave", "length": "how many hours they will be at sea, or what time they will be back"}


def worded_question(res: dict, lang: str, user_text: str) -> str | None:
    """The follow-up question in the model's own words (owner, 13 Nov 2026), or None for the reviewed template.
    Code has already decided what is missing; the model only phrases one short question for exactly that, in the
    fisher's language, and may use their name. Its words pass the guard (no digits, no verdict or safety words)
    and must be a single question of at most 140 characters. Any problem (no model, odd answer): None."""
    need = [n for n in ("time", "length") if n in (res.get("need") or [])]
    if not need or not load_app().get("model_questions", True):
        return None
    language = load_app()["languages"][lang]["english_name"]
    system = (f"You are the Sea Safe assistant, talking with a small-boat fisher. Write ONE short, friendly question in "
              f"{language} that asks ONLY for: {' and '.join(_ASK_FOR[n] for n in need)}. At most 18 words. No numbers or "
              "digits, no times, no harbour names, nothing about weather or safety. If the fisher gave their name, you may "
              "use it. Reply with the question only.")
    try:
        message, _ = llm.complete([{"role": "system", "content": system},
                                   {"role": "user", "content": (user_text or "")[:300]}], [])
    except Exception as e:                          # no model, a timeout, anything: the template is used
        log.info("question wording skipped: %s", e)
        return None
    text = ((message or {}).get("content") or "").strip().strip('"“”')
    if not text or "\n" in text or len(text) > 140 or text[-1] not in "?؟":
        return None
    return guard(text, after_tool=True)


def need_text(res: dict, lang: str, spoken: bool = False, worded: str | None = None) -> str:
    """The question for the missing details. It first says back what was understood ("Umm Al Quwain, leaving
    17:00, got it."), so the fisher can see it was heard right; then the question: the model's wording when
    worded_question() gave one, else the reviewed template. spoken=True: the voice says the departure the way
    people talk ("on Tuesday at 5 in the evening")."""
    if worded:
        return f"{_said_back(res, lang, spoken)} {worded}".strip()
    need = set(res.get("need") or [])
    key = "both" if need == {"time", "length"} else ("time" if "time" in need else "length")
    pid = res.get("place")
    if pid and key == "length" and not res.get("departure"):
        # "When is the best time?" has no departure to say back (it searches the whole day): ask for the length only.
        return explain.t(lang, "chat.need_length", from_place=explain.t(lang, f"place_from.{pid}"))
    if pid:
        name = explain.t(lang, f"place.{pid}")
        dep = res.get("departure")
        if spoken and key == "length" and dep:
            return explain.t(lang, "say.ask_length", name=name,
                             departure=f"{explain.say_day(lang, dep)} {explain.say_time(lang, dep)}")
        return explain.t(lang, f"chat.ask_{key}", name=name,
                         departure=explain.when(lang, dep) if dep else "", hours=res.get("trip_hours") or "")
    return explain.t(lang, f"chat.need_{key}_any")


def _said_back(res: dict, lang: str, spoken: bool) -> str:
    """What code understood, before the model's question: the same say-back as the templates, without their question."""
    need = set(res.get("need") or [])
    key = "both" if need == {"time", "length"} else ("time" if "time" in need else "length")
    pid = res.get("place")
    if not pid:
        return ""
    dep = res.get("departure")
    if key == "length" and not dep:
        return explain.t(lang, "chat.got_from", from_place=explain.t(lang, f"place_from.{pid}"))
    name = explain.t(lang, f"place.{pid}")
    if key == "length":
        when = f"{explain.say_day(lang, dep)} {explain.say_time(lang, dep)}" if spoken else explain.when(lang, dep)
        return explain.t(lang, "say.got_length" if spoken else "chat.got_length", name=name, departure=when)
    return explain.t(lang, f"chat.got_{key}", name=name, hours=res.get("trip_hours") or "")


# Words that say which half of the day a clock time is in. Without one, "at 5" is ambiguous.
_AMPM = re.compile(r"\b(am|pm|a\.m|p\.m|morning|afternoon|evening|night|tonight|noon|midnight|dawn)\b|\d\s*(am|pm)\b|"
                   r"ಬೆಳಿಗ್ಗೆ|ಬೆಳಗ್ಗೆ|ಬೆಳಗಿನ|ಮುಂಜಾನೆ|ಮಧ್ಯಾಹ್ನ|ಸಂಜೆ|ಸಾಯಂಕಾಲ|ರಾತ್ರಿ|صباح|الصبح|الفجر|فجرا|الظهر|ظهرا|"
                   r"العصر|مساء|المسا|المغرب|الليل|بالليل|ليلا|ليلاً|منتصف", re.I)


def _evening_if_morning_passed(args: dict, user_text: str, now: datetime, context: dict, page, clock) -> None:
    """"Leaving at 5" at 09:35 means 17:00, not 05:00 that has already gone. Only when the user gave a clock
    hour from 1 to 11 with no am/pm word, for today, and that hour has passed while the evening one has not."""
    hour = int(args.get("hour", -1))
    if not (1 <= hour <= 11) or _AMPM.search(user_text or "") or not re.search(r"\d", (user_text or "").translate(_DIGITS)):
        return
    if args.get("day") not in ("same", "today"):
        return
    dep = _departure(args, now, context, page, clock)
    if dep < clock["now"] <= f"{dep[:11]}{hour + 12:02d}:00":
        log.warning("no am/pm and %02d:00 has passed: read as %02d:00", hour, hour + 12)
        args["hour"] = hour + 12


def _covered_hours(args: dict, dep: str, hours: int, user_text: str) -> tuple[int, bool]:
    """Approximate times, covered the careful way (audit 13 Nov 2026 allows this instead of refusing): the
    check reads whole hourly records, so a departure at 16:10 starts at the 16:00 record (it also covers the
    hour before) and a return at 18:30 ends at the 19:00 record. Every hour the trip could touch is checked,
    which can only make the answer more careful. Returns (hours, covered) - covered: say so to the user."""
    dmin = int(args.get("minute", 0) or 0)
    back = int(args.get("back_by_hour", -1))
    bmin = int(args.get("back_by_minute", 0) or 0)
    if back >= 0:
        hours = trip_from_return(dep, back) + (1 if bmin > 0 else 0)
    elif dmin > 0:
        hours += 1                          # 16:10 for 3 hours ends 19:10: read up to the 20:00 record
    covered = dmin > 0 or (back >= 0 and bmin > 0)
    if not covered and stated_minutes(user_text):
        hours, covered = hours + 1, True    # minutes in the words, not reported by the model: one more hour
    return hours, covered


def _run_tool(call: dict, region_id: str, mode: str, map_point, context: dict | None = None,
              user_text: str = "", page: dict | None = None) -> dict:
    """Run a tool call. The model gives day words and hours; code turns them into exact times and trip lengths."""
    name = call["function"]["name"]
    try:
        args = json.loads(call["function"]["arguments"] or "{}")
    except (TypeError, ValueError):
        args = None
    if not isinstance(args, dict):           # the model check in app/llm.py should already have refused this
        log.warning("tool call %s with arguments that are not an object", name)
        return {"tool": name, "args": {}, "result": {"ok": False, "error": "generic"}}
    clock = service.clock_info(region_id, mode)
    now, window_end = datetime.fromisoformat(clock["now"]), datetime.fromisoformat(clock["window_end"])
    context = context or {}
    # Code checks the place: if the user's own words name exactly one harbour, that harbour is used.
    # (A model once kept the previous harbour when asked "طيب ودبا؟" - "and Dibba?".)
    named = mentioned_harbours(user_text, get_region(region_id))
    if "place" in args and len(named) == 1 and args["place"] not in named and args["place"] != "map_point":
        log.warning("place corrected from %s to %s (named in the question)", args.get("place"), next(iter(named)))
        args["place"] = next(iter(named))
    page_given = {"given": bool((page or {}).get("trip_length_given_by_user")), "trip_hours": (page or {}).get("trip_hours")}
    try:
        part = stated_part_of_day(user_text)
        if "hour" in args and int(args.get("hour", -1)) < 0 and part is not None and not re.search(r"\d", user_text or ""):
            log.warning("hour set from the user's words: %s -> %02d:00", args.get("day"), part)
            args["hour"] = part
        stated = stated_trip_hours(user_text)
        if stated is not None and stated < 1:
            stated = None
        if name in ("assess_trip", "weather_details", "check_all_harbours") and args.get("day") not in OUTSIDE:
            _evening_if_morning_passed(args, user_text, now, context, page, clock)
        dep = None
        if name in ("assess_trip", "weather_details") and args.get("day") not in OUTSIDE:
            dep = _departure(args, now, context, page, clock)
        problem = _unsupported_trip(name, args, stated, user_text, dep, now)
        if not problem and dep and int(args.get("hour", -1)) >= 0 and dep < clock["now"]:
            problem = "past_time_at"             # caught before asking for anything else
        need = [] if problem or args.get("day") in OUTSIDE else _missing(name, args, stated, context, page)
        if problem:
            log.warning("trip refused (%s): %s %s", problem, name, args)
            res = {"ok": False, "error": problem, "place": args.get("place"), "departure": dep}
        elif need:
            # Something is missing: ask, and keep what is known so the next answer completes the trip.
            known_hours = None if "length" in need else _trip_length(args, stated, context, page_given)[0]
            if "length" not in need and int(args.get("back_by_hour", -1)) >= 0 and dep:
                known_hours = trip_from_return(dep, int(args["back_by_hour"]))
            res = {"ok": False, "error": "need_details", "need": need, "place": args.get("place"),
                   "departure": None if "time" in need else dep, "trip_hours": known_hours}
        elif args.get("day") in OUTSIDE:           # yesterday / next week: a clear, templated limit
            res = {"ok": False, "error": "past_time" if args["day"] == "past" else "outside_window"}
        elif name == "explain_app":
            res = {"ok": True, "topic": args["topic"], "region": region_id}
        elif name == "official_info":
            res = {"ok": True, "topic": args["topic"], "region": region_id}
        elif name in ("assess_trip", "weather_details"):
            hours, given = _trip_length(args, stated, context, page_given)
            if int(args.get("back_by_hour", -1)) >= 0:   # "back by 9": code works out the length
                given = True
            hours, covered = _covered_hours(args, dep, hours, user_text)
            res = service.assess_trip(region_id, args["place"], dep, hours, given, mode, map_point)
            if res.get("ok") and covered:
                res["covered"] = True            # the reply says which whole hours were checked
            if res.get("ok") and mode == "live" and dep == clock["now"]:
                res["leaving_now"] = True        # said as "now", not "Thursday at midnight"
        elif name == "check_all_harbours":
            dep = _departure(args, now, context, page, clock)
            hours, given = _trip_length(args, stated, context, page_given)
            hours, _ = _covered_hours(args, dep, hours, user_text)
            res = service.assess_region(region_id, dep, hours, mode)
            if res.get("ok"):
                for r in res["harbours"].values():
                    r["trip_length_given_by_user"] = given
                res.update(departure=dep, trip_hours=hours, trip_length_given_by_user=given,
                           leaving_now=mode == "live" and dep == clock["now"])
        elif name == "find_safest_time":
            day = args["day"] if args["day"] != "same" else next(
                (w for w, d in day_dates(now).items() if d.isoformat() == _departure(args, now, context, page, clock)[:10]), "today")
            start, end = resolve_range(day, now, window_end)
            hours, given = _trip_length(args, stated, context, page_given)
            res = service.find_safest_time(region_id, args["place"], start, end, hours, given, mode, map_point)
            # Today has one SAFE hour or none: also look at tomorrow, and say it when tomorrow has more SAFE
            # times (owner, 13 Nov 2026). The same trip, the same checks; the code decides, not the model.
            if day == "today" and res.get("ok") and service.safe_hours(res) <= 1:
                try:
                    t0, t1 = resolve_range("tomorrow", now, window_end)
                    nxt = service.find_safest_time(region_id, args["place"], t0, t1, hours, given, mode, map_point)
                    if service.safe_hours(nxt) > service.safe_hours(res):
                        res["tomorrow"] = nxt
                except (KeyError, ValueError):
                    pass                                # tomorrow is outside the forecast window: say nothing
        else:
            res = {"ok": False, "error": "generic"}
    except (KeyError, ValueError, TypeError) as e:
        log.warning("bad tool call %s %s: %s", name, args, e)
        res = {"ok": False, "error": "bad_time"}
    return {"tool": name, "args": args, "result": res}


def _for_model(run: dict) -> str:
    """What the model sees from a tool: enough to introduce it, nothing to explain it with."""
    res = run["result"]
    if not res.get("ok"):
        return json.dumps({"ok": False, "error": res.get("error"),
                           "note": "The app tells the user about this problem. Write one short neutral sentence."})
    if run["tool"] in ("explain_app", "official_info"):
        return json.dumps({"ok": True, "note": "The app shows a reviewed answer. Write one short neutral sentence."})
    if run["tool"] == "check_all_harbours":
        return json.dumps({"ok": True, "departure": res["departure"], "trip_hours": res["trip_hours"],
                           "note": "The app lists every harbour with its verdict. Write one short neutral sentence "
                                   "introducing it, without numbers or verdict words."})
    shown = res.get("shown", res)
    return json.dumps({"ok": True, "place": shown["place"]["id"], "departure": shown["departure"],
                       "trip_hours": shown["trip_hours"],
                       "note": "The app shows the verdict, reasons and numbers. Write one short neutral sentence "
                               "introducing it, without numbers or verdict words. Never call any time "
                               "'safest' or 'best'; say e.g. 'Here are the departure times for Gangolli today.'"})


def _clean_page(page) -> dict:
    """What the page says is on screen, checked: a departure that is not a whole-hour time and a trip length
    outside 1..max hours are dropped (the defaults are used instead), so a bad value can never crash the chat."""
    page = dict(page) if isinstance(page, dict) else {}
    if not (isinstance(page.get("departure"), str) and re.match(TIME_PATTERN, page["departure"])):
        page.pop("departure", None)
    hours = page.get("trip_hours")
    if not (isinstance(hours, int) and not isinstance(hours, bool) and 1 <= hours <= load_app()["trip"]["max_hours"]):
        page.pop("trip_hours", None)
        page["trip_length_given_by_user"] = False
    return page


def chat(history: list[dict], lang: str, region_id: str, mode: str = "live", map_point=None,
         context: dict | None = None, page: dict | None = None) -> dict:
    """page: what is selected on screen (place, departure, trip_hours, trip_length_given_by_user).
    It fills in whatever the user does not say, so the chat never has to ask for a time."""
    region = get_region(region_id)
    lang = explain.pick_lang(lang, region_id)
    page = _clean_page(page)
    place_ids = [h["id"] for h in region["harbours"]] + (["map_point"] if map_point else [])
    tools = schemas(place_ids, load_app()["trip"]["max_hours"])
    messages = [{"role": "system", "content": _system_prompt(region, lang, mode, map_point, context, page)}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history[-12:]
                 if m.get("role") in ("user", "assistant") and m.get("content")]
    question = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")

    # Per-language switch (config/app.yaml): if off, the model's own words are never shown in this
    # language, and we skip the second model call that would only have written the intro sentence.
    model_words = load_app()["languages"][lang].get("model_sentence", True)
    runs, providers, final_text = [], [], ""
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            message, provider = llm.complete(messages, tools)
            providers.append(provider)
            if not message.get("tool_calls"):
                final_text = message.get("content") or ""
                break
            messages.append({"role": "assistant", "content": message.get("content"),
                             "tool_calls": message["tool_calls"]})
            for call in message["tool_calls"]:
                run = _run_tool(call, region_id, mode, map_point, context, question, page)
                runs.append(run)
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": _for_model(run)})
            if not model_words:
                break
    except llm.LLMUnavailable as e:
        log.error("no language model available: %s", e)
        msg = explain.t(lang, "chat.llm_unavailable")
        return {"reply": msg, "spoken": msg, "cards": [], "provider": None, "context": context}

    if asks_if_sure(question, region) and not any(r["tool"] == "explain_app" for r in runs):
        # "Are you sure?": how far to trust a forecast (reviewed), not the same check again.
        log.warning("doubt answered with the accuracy answer (model chose %s)", [r["tool"] for r in runs] or "nothing")
        runs = [{"tool": "explain_app", "args": {"topic": "accuracy"},
                 "result": {"ok": True, "topic": "accuracy", "region": region_id}}]
    if asks_about_tides(question) and not any(r["tool"] == "explain_app" for r in runs):
        # No tide data in the app: say so, rather than "which harbour?" or a weather reading.
        log.warning("tide question answered with the limits answer (model chose %s)", [r["tool"] for r in runs] or "nothing")
        runs = [r for r in runs if r["tool"] not in ("weather_details",)]
        runs.insert(0, {"tool": "explain_app", "args": {"topic": "limits"},
                        "result": {"ok": True, "topic": "limits", "region": region_id}})
    named = mentioned_harbours(question, region)
    if not runs and len(named) == 1:
        # The model answered in words, but the user named a harbour ("didn't you say Khor Fakkan was safe?").
        # Asking "which harbour?" would be wrong: code checks it, with the previous time and trip length.
        log.warning("no tool call although %s was named: checking it", next(iter(named)))
        call = {"function": {"name": "assess_trip", "arguments": json.dumps({
            "place": next(iter(named)), "day": "same", "hour": -1, "minute": 0, "back_by_hour": -1,
            "back_by_minute": 0, "back_day": "same",
            "trip_hours": int((context or {}).get("trip_hours") or (page or {}).get("trip_hours")
                              or load_app()["trip"]["default_hours"]),
            "trip_length_given_by_user": bool((context or {}).get("given"))})}}
        runs.append(_run_tool(call, region_id, mode, map_point, context, question, page))
        final_text = ""
    elif not runs and asks_when_back(question) and (context or {}).get("place") and (context or {}).get("departure"):
        # "متى أرجع؟" once came back as the model's own "you'll be back at 19:00": a time written by the model.
        # The return time must come from code, so the trip being talked about is checked again.
        log.warning("return-time question answered without a tool: checking the previous trip")
        call = {"function": {"name": "assess_trip", "arguments": json.dumps({
            "place": context["place"], "day": "same", "hour": -1, "minute": 0, "back_by_hour": -1,
            "back_by_minute": 0, "back_day": "same",
            "trip_hours": int(context.get("trip_hours") or load_app()["trip"]["default_hours"]),
            "trip_length_given_by_user": bool(context.get("given"))})}}
        runs.append(_run_tool(call, region_id, mode, map_point, context, question, page))
        final_text = ""

    log.info("chat turn: %d model call(s), %d tool call(s), model sentence %s",
             len(providers), len(runs), "on" if model_words else "off")
    # Small talk with no check (a greeting, "thanks") is the model's own words, through the guard, in every
    # language: the owner asked for a conversational bot on 13 Nov 2026. Around a check, model_sentence still
    # decides, and it is off: there only reviewed templates are shown.
    question = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    return _compose(runs, final_text, lang, providers, context, region, model_words, question)


def ask_place(lang: str, region: dict) -> str:
    """The only question the app asks: which harbour, naming them (templated, so it can be reviewed)."""
    names = explain.t(lang, "list.joiner_names").join(explain.t(lang, f"place.{h['id']}") for h in region["harbours"])
    return explain.t(lang, "chat.ask_place", places=names)


def _compose(runs: list, final_text: str, lang: str, providers: list, context, region: dict,
             model_words: bool = True, question: str = "") -> dict:
    if not runs:
        text = guard(final_text, after_tool=False) or ask_place(lang, region)
        return {"reply": text, "spoken": text, "cards": [], "provider": providers[-1] if providers else None,
                "context": context}

    # "Here is the check." only when there is a check to show, not in front of an error message.
    checks = ("assess_trip", "weather_details", "find_safest_time", "check_all_harbours")
    parts = [(guard(final_text, after_tool=True) if model_words else None) or explain.t(lang, "chat.neutral_intro")] \
        if any(r["result"].get("ok") and r["tool"] in checks for r in runs) else []
    said = []          # what the voice reads: the same templates, in the short spoken form
    shown = []         # single-trip checks: the chat shows them as bullet points
    safest_chat = None  # "when should I leave?": bullets too, and no verdict badge (the trip shown is an example)
    details_trip = None  # a weather-details answer: its trip, for "what time do I come back by?"
    cards = []
    region_card = None
    for run in runs:
        res = run["result"]
        if res.get("error") == "need_details":
            worded = worded_question(res, lang, question)      # the model words it; code decided what to ask
            parts.append(need_text(res, lang, worded=worded))
            said.append(need_text(res, lang, spoken=True, worded=worded))
            partial = {"place": res.get("place") or (context or {}).get("place"), "departure": res.get("departure"),
                       "trip_hours": res.get("trip_hours"), "given": True if res.get("trip_hours") else None}
            context = {k: v for k, v in partial.items() if v is not None}
            continue
        if res.get("error") == "past_time_at" and res.get("departure"):
            msg = explain.t(lang, "error.past_time_at", time=explain.when(lang, res["departure"]),
                            hhmm=res["departure"][11:16])
            parts.append(msg)
            said.append(msg)
            if res.get("place"):                 # keep the harbour for the next answer
                context = {"place": res["place"]}
            continue
        if not res.get("ok"):
            parts.append(explain.error_text(res, lang))
            said.append(explain.error_text(res, lang))
            continue
        if run["tool"] == "explain_app":
            parts.append(explain.faq_text(res["topic"], lang, res["region"]))
            said.append(explain.faq_spoken(res["topic"], lang, res["region"]))
            continue
        if run["tool"] == "official_info":
            parts.append(explain.official_text(res["region"], lang))
            said.append(explain.official_spoken(res["region"], lang))
            continue
        if run["tool"] == "weather_details":
            detail = run["args"].get("detail", "all")
            parts.append(explain.details_text(res, lang, detail))
            said.append(explain.details_spoken(res, lang, detail))
            details_trip = res
            cards.append({"result": res, "view": explain.render(res, lang)})
            context = {"place": res["place"]["id"], "departure": res["departure"], "trip_hours": res["trip_hours"],
                       "given": res["trip_length_given_by_user"]}
            continue
        if run["tool"] == "check_all_harbours":
            parts.append(explain.region_text(res, lang))
            said.append(explain.region_spoken(res, lang))
            region_card = explain.region_view(res, lang)
            context = {**(context or {}), "departure": res["departure"], "trip_hours": res["trip_hours"],
                       "given": res["trip_length_given_by_user"]}
            continue
        if run["tool"] == "find_safest_time":
            # Speak only the windows; the example trip stays on the card.
            safest_chat = explain.safest_bullets(res, lang)
            parts.append(explain.safest_line(res, lang))
            said.append(" ".join(x for x in (explain.safest_spoken(res, lang),
                                             explain.t(lang, "say.disclaimer")) if x))
            res = res["shown"]
            parts.append(explain.text(res, lang))
            cards.append({"result": res, "view": explain.render(res, lang)})
            # a follow-up ("what about Mangalore?") keeps the user's own departure, not the example's
            context = {"place": res["place"]["id"], "departure": (context or {}).get("departure") or res["departure"],
                       "trip_hours": res["trip_hours"], "given": res["trip_length_given_by_user"]}
            continue
        shown.append(res)
        if res.get("covered"):                   # approximate times: say which whole hours were checked
            note = explain.t(lang, "chat.covered", **{"from": explain.when(lang, res["departure"]),
                                                       "to": explain.when(lang, res["return"])})
            parts.append(note)
            said.append(note)
        parts.append(explain.text(res, lang))
        said.append(explain.spoken(res, lang))
        cards.append({"result": res, "view": explain.render(res, lang)})
        context = {"place": res["place"]["id"], "departure": res["departure"], "trip_hours": res["trip_hours"],
                   "given": res["trip_length_given_by_user"]}
    # The chat bubble for a single trip: short bullet points (with the "which hours" note when times
    # were approximate). The voice still reads "spoken".
    chat_text = None
    if shown:
        last = shown[-1]
        pre = [explain.t(lang, "chat.covered", **{"from": explain.when(lang, last["departure"]),
                                                   "to": explain.when(lang, last["return"])})] if last.get("covered") else []
        # "What time do I come back by?": the return time is the first line written (13 Nov 2026). The spoken
        # answer already says "You'd be back around ...", so it is not said twice.
        if asks_when_back(question):
            pre.insert(0, explain.t(lang, "chat.b.back_by", back=explain._short_time(lang, last["return"],
                                                                                    last["departure"][:10])))
        chat_text = "\n".join(["• " + x for x in pre] + [explain.bullets(last, lang)])
    elif safest_chat:
        chat_text = safest_chat
    elif details_trip and asks_when_back(question):   # the model chose weather details: still say it first
        said.insert(0, explain.t(lang, "say.back_by", time=explain.say_time(lang, details_trip["return"])))
    return {"reply": "\n\n".join(parts), "spoken": " ".join(said), "chat_text": chat_text,
            "cards": cards, "region": region_card, "no_badge": bool(safest_chat) and not shown,
            "provider": providers[-1], "context": context}


# "What time do I come back by?" / "ಎಷ್ಟು ಗಂಟೆಗೆ ವಾಪಸ್?" / "متى أرجع؟": a question about the return time.
_WHEN = re.compile(r"\b(what time|when)\b|ಯಾವಾಗ|ಎಷ್ಟು ಗಂಟೆ|ಎಷ್ಟೊತ್ತಿಗೆ|ಎಷ್ಟು ಹೊತ್ತಿಗೆ|ಯಾವ ಸಮಯ|ಯಾವ ಹೊತ್ತಿಗೆ"
                   r"|متى|امتى|إمتى|ايمتى|إيمتى|أي ساعة|اي ساعة|أي وقت|اي وقت|الساعة كم|كم الساعة", re.I)
_BACK = re.compile(r"\b(come back|get back|be back|return|back)\b|ವಾಪಸ್|ವಾಪಾಸ್|ಹಿಂತಿರುಗ|ಹಿಂದಿರುಗ|ಮರಳ"
                   r"|رجع|رجوع|أعود|اعود|نعود|العودة|عودة", re.I)


def asks_when_back(text: str) -> bool:
    return bool(text and _WHEN.search(text) and _BACK.search(text))
