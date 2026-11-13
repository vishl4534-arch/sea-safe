# Sea Safe: design

NOVA Hackathon, Track D (AI & Autonomous Systems). Date: 12 November 2026.

## 1. What it is and why

Small-scale fishers have to decide before dawn whether to take a small open boat out. Sea Safe answers one question: **is it safe to go out from this place at this time?** The answer is SAFE, CAUTION or UNSAFE, with the reasons, in the fisher's own language.

There are two ways to ask:

- **Map:** pick a harbour pin or click anywhere on the sea.
- **Chat:** type in plain language, for example "Is it safe to leave from Malpe at 5 tomorrow morning?"

**Who it is for.** The users are fishers with limited literacy and little experience of apps. So answers are short and plain, use no jargon, and lead with a colour and one word.

**Regions.**
- Karnataka coast, India, in English and Kannada (primary).
- UAE coast, in English and Arabic (second region; the finale is judged in Dubai).

**Judging deliverables and where each is met:**

| Deliverable | Where |
|---|---|
| Working web app with a conversational interface | Chat panel (section 8) |
| English plus at least one more language | English, Kannada, Arabic (section 9) |
| Public marine weather API | Open-Meteo Marine and Forecast APIs (section 5) |
| Interactive map with location selection | MapLibre map with harbour pins, click-on-sea and a 48-hour time slider (section 10 and [ui.md](ui.md)) |
| Clear safe / caution / unsafe indicators | Coloured pins, verdict card and an hour-by-hour strip |
| Explanation of each recommendation | Templated reasons on every answer, plus the "How we decide" panel |
| Working demo on at least one coastal location | Live data for every harbour, plus replay days (section 7) |

## 2. Goals, non-goals, anti-goals

**Goals**
- Live marine data, a deterministic verdict, an interactive map and a conversational chat. All of it works in every enabled language.
- The assessment is **one callable service**, so a later voice agent can use it as a tool (section 11).
- Every part is small enough to explain to judges.

**Non-goals (this session)**
- Voice input and output.
- User accounts, notifications, offline maps.
- Trawlers and dhows.
- Any paid API or model training.

**Anti-goals: a failure even if it "works"**
- The language model decides, or changes, a verdict or a number.
- The app says SAFE when data is missing, stale, or close to a line.
- An answer reads as a promise of safety, or hides where its numbers came from.
- A replay could be mistaken for a live forecast.
- Kannada or Arabic text reaches users without native-speaker review. Each language can be switched off in config.

## 3. Thresholds (approved 12 Nov 2026)

**Boat class:** small open boats under about 10 m. This is shown next to every verdict.

**Where they live:** all values sit in `config/thresholds.yaml`. Each one carries its source document, link and paragraph. The same information appears on the "How we decide" panel.

| Parameter | CAUTION from | UNSAFE from | Source |
|---|---|---|---|
| Significant wave height | 1.25 m | 2.0 m | CAUTION: WMO-No. 306, code table 3700 ("moderate" sea starts at 1.25 m; IMD uses the same scale). UNSAFE: FAO/ILO/IMO 2012, para 1.2.14.3 (design category C) |
| Sustained wind, 10 m | 37 km/h (20 kn) | 43 km/h (12 m/s) | CAUTION: IMD fishermen-warning criterion, "squally weather … maximum sustained wind speed of 20 knots or more". UNSAFE: FAO/ILO/IMO 2012, para 1.2.14.3 |
| Wind gusts | 40 km/h (22 kn) | 63 km/h (34 kn) | CAUTION: WMO-No. 306 squall criterion (22 kn). UNSAFE: WMO-No. 558, gale warning level (Beaufort 8, 34 kn) |
| Thunderstorm forecast (WMO weather code 95, 96 or 99) | any | none | WMO-No. 558 Part II 3.4.2(b); WMO-No. 471 2.5.7. Both are qualitative, so the level (CAUTION only) is our call |
| Visibility | 1,852 m (1 nautical mile) or less | none | WMO-No. 558 Part II 3.4.2(c) |

### 3.1 The exact FAO sentence, and where UNSAFE starts

FAO/ILO/IMO, *Safety Recommendations for Decked Fishing Vessels of Less than 12 metres in Length and Undecked Fishing Vessels* (2012), para 1.2.14.3, design category C:

> "Category of vessels considered suitable to operate in seas with significant wave heights up to 2 m and a typical steady wind force of Beaufort Force 6 (12 m/s) or less."

How to read it:
- **Wind.** "Or less" means 12 m/s (43.2 km/h) is still *inside* the envelope.
- **Waves.** "Up to 2 m" is ambiguous. For design category D, the same document says "up to and including 0.30 m". That suggests "up to" for category C also includes the limit.

**Choice: UNSAFE starts *at* the limit (value ≥ 2.0 m, wind ≥ 43 km/h), not above it.** Why:
1. A forecast exactly at a design limit leaves no safety margin. The forecast itself has error.
2. The project rule is "never promise safety". Rounding toward the safer verdict is the wrong direction.
3. Every numeric line then uses the same "at or above" comparison, which is simpler to explain and to test.

For wind, 12 m/s converts to 43.2 km/h. We round down to 43 km/h, which is also the conservative direction.

**What these categories are.** FAO design categories describe the conditions a boat is *designed* for. They are not a go/no-go rule. We present them to judges as the boat's design envelope.

**What each source contributes:**
- FAO is the only source written specifically for small fishing boats.
- IMD values are India's own fishermen-warning criteria. IMD warns above 45 km/h, which agrees with the FAO wind limit.
- The UAE's National Centre of Meteorology does not publish numeric warning criteria that we could find, so the UAE uses the same international values.

### 3.2 Our own rules (not from any source; shown as ours on the "How we decide" panel)

- **Near the line, 10% margin.**
  - A value within 10% below a CAUTION line gives CAUTION. The explanation says the value is *close to* the caution line, not that it crossed it.
  - Effective lines are waves 1.125 m, wind 33.3 km/h and gusts 36 km/h.
  - **Exact values.** The near-line value is rounded before comparing. In computer arithmetic 37 × 0.9 is 33.300000000000004, which would let a forecast of exactly 33.3 km/h through as SAFE. The 12 Nov 2026 audit found this, and a test now covers it.
  - For visibility, which is a "lower is worse" parameter, the rule works the other way: CAUTION up to 2,037 m.
- **Thunderstorms give CAUTION only.** Model thunderstorm forecasts are noisy.
- **Missing data gives CAUTION.** This covers any missing parameter in any trip hour, and trip hours that fall beyond the forecast window.
- **Stale data counts as missing.** Data fetched more than 6 hours ago is treated as missing, so it gives CAUTION and never SAFE.
- **The worst hour decides.** For each hour, the worst parameter decides that hour. For the trip, the worst hour decides.
- **One reason line per parameter** (decided 12 Nov 2026). The card lists every parameter that was not SAFE in some hour of the trip, UNSAFE ones first. Each line gives that parameter's **worst value** during the trip, the hour it occurs and the line it reached. So the card never shows two contradicting lines for the same parameter, such as "1.24 m close to the caution line" and "1.74 m above it".
  - A real value takes precedence over a missing hour for the same parameter. The verdict is unaffected, because missing data already gives CAUTION.

### 3.3 Known limitation: the wind CAUTION band is narrow

The wind CAUTION band runs from 37 to 43 km/h. That is only 6 km/h wide, and about 10 km/h counting the 10% margin (33.3 to 43 km/h). Both are **narrower than the usual error of a wind forecast**. So when wind alone drives the verdict, it will often jump straight from SAFE to UNSAFE between neighbouring hours or neighbouring days, with little or no CAUTION in between. This comes from the two published lines sitting close together; it is not a bug. We will say so to judges, and we will not widen the band without a source.

### 3.4 Kept out of the verdict

- **Wave period.** No source gives a numeric limit. It is still fetched, together with wave direction and wind direction, and shown in the details.
- **Swell on its own.** Significant wave height already includes swell.
- **IMD's "very rough" level (over 4 m).** It is far above the small-boat limit.

### 3.5 Sanity check on 2022 to 2025 data

The check: leave at 05:00 local time on a 6-hour trip, every day from 2022 to 2025.

- **Karnataka:** SAFE on 85 to 99% of days from November to April. Most monsoon days (June to August) are UNSAFE.
- **UAE:** SAFE on 76 to 96% of days.
- **Demo day:** live demo days in November will mostly be green. That is why replay exists (section 7).

## 4. The trip and the time

- **Trip length.** A trip is a departure hour plus a trip length. The verdict reads **every hourly record from departure to return, both included**: a 6-hour trip from 05:00 reads 05:00, 06:00 … 11:00, which is 7 records.
  - **Why the return hour counts:** Open-Meteo reports gusts (and the weather code) as the maximum over the hour *before* each time stamp, so the 11:00 record covers the last hour at sea. The 05:00 record also covers the hour before leaving, which can only make the answer more careful.
  - **Audit finding:** the 12 Nov 2026 audit found that the return hour was skipped. That made 18 replay trips SAFE that are really CAUTION.
- **Default trip length: 6 hours.** **This is an assumption**, not sourced and not measured. It lives in `config/app.yaml` (`trip.default_hours`).
  - On screen, the quick choices are 4, 6, 8 and 12 hours.
  - In chat the model picks the length up from what the user says ("back by noon" after a 5 am departure means 7 hours).
- **Every answer shows the trip length**, and says whether it is the assumed default or what the user said.
- **Forecast window: the next 48 hours** (`forecast.window_hours`).
  - A departure in the past, or outside the window, is refused with a plain message.
  - Trip hours that run past the end of the window count as missing data, which gives CAUTION.
- **Times are local:** Asia/Kolkata for Karnataka and Asia/Dubai for the UAE. Each region's time zone is set in config.

## 5. Data

| What | API | Model | Notes |
|---|---|---|---|
| Waves, live | Open-Meteo Marine | `ecmwf_wam` (ECMWF, about 9 km, hourly) | Chosen because its nearest sea cells are much closer to the UAE east-coast harbours (see section 6) |
| Wind, gusts, weather code and visibility, live | Open-Meteo Forecast | `best_match` | Requested at the wave model's sea cell, not on land |
| Waves, replay | Open-Meteo Marine (archive) | `meteofrance_wave` (MFWAM, about 8 km) | Archive starts October 2021. ECMWF WAM's archive only starts November 2025, after our replay days |
| Wind and the rest, replay | Open-Meteo Historical Forecast API | `best_match` | |
| Tauktae replay (optional, coarse) | Marine `era5_ocean` and Archive API (ERA5) | Reanalysis, about 50 km | May 2021 predates the 8 km archive. Labelled as coarse data |
| Land check for map clicks | Open-Meteo Elevation | 90 m terrain model | Elevation above 0 m means "pick a point at sea" |

**Sea cell.** Each harbour has a pin, which is the harbour itself. The marine API returns the nearest sea cell of the wave model, and the app shows where that cell is and how far it is from the pin. **Distances over 5 km are shown prominently** on the card.

**Cache.** Responses are stored as JSON under `data/cache/` with their fetch time.
- Live data younger than 30 minutes is reused. Otherwise it is fetched again.
- **One fetch at a time.** Only one request at a time fetches a given data file (a lock per file). Files are written to a temporary name and then renamed, so a reader never sees a half-written file.
- **Harbours are fetched together.** A region's harbours are always fetched as one batch, including the ones switched off. Switching a harbour off therefore never changes which file is used, and replay keeps working offline.
- If a fetch fails, the cached copy is used and its age is shown.
- If the cache is older than 6 hours, the data is treated as missing, which gives CAUTION.

**Replay data** is fetched once and saved under `data/replay/`, which is committed. Replay therefore works without internet.

**Every assessment shows:**
- the parameters that drove it
- the forecast hour each value applies to
- when the data was fetched
- the data model
- the sea-cell distance
- a visible link reading "Weather data by Open-Meteo.com"

## 6. Harbours (approved 12 Nov 2026, with changes)

**What a pin marks.** Each pin is the harbour or landing site, checked against OpenStreetMap. The distance column is from the pin to the live (ECMWF WAM) sea cell, as checked on 12 Nov 2026.

**Karnataka.** The basis is the MPEDA list of fishing harbours and Lok Sabha unstarred question 1250 (3 Dec 2024). Hejamady Kodi is dropped because it is still under construction.

| Harbour | Pin | Live sea cell distance |
|---|---|---|
| Mangaluru (Bunder) | 12.8598, 74.8326 | 4.2 km |
| Malpe | 13.3476, 74.6994 | 3.2 km |
| Gangolli | 13.6333, 74.6750 | 3.9 km |
| Bhatkal | 13.9668, 74.5353 | 3.8 km |
| Honnavar | 14.2762, 74.4406 | 4.5 km |
| Tadri | 14.5245, 74.3551 | 5.5 km |
| Belekeri | 14.7079, 74.2574 | 8.9 km |
| Karwar (Baithkol) | 14.8009, 74.1125 | 3.7 km |

**UAE.** Kalba is dropped because its only distinct sea cell is 26 km offshore, so it would not represent Kalba. Fujairah is dropped because its fishermen's port could not be confirmed (see the end of this section). That leaves 8 harbours, so the Jumeirah replacement is not needed; it stays in config, switched off.

| Harbour | Pin | Live sea cell distance |
|---|---|---|
| Abu Dhabi – Mina Zayed | 24.5143, 54.3759 | 5.1 km |
| Dubai – Umm Suqeim | 25.1724, 55.2135 | 3.4 km |
| Dubai – Al Hamriya | 25.3018, 55.3339 | 4.6 km |
| Ajman | 25.4005, 55.4535 | 7.0 km |
| Umm Al Quwain (Al Naqqa / Al Meydan port) | 25.5559, 55.5381 | 3.3 km |
| Ras Al Khaimah – Al Rams | 25.8826, 56.0278 | 3.4 km |
| Dibba Al-Hisn | 25.6197, 56.2749 | 7.3 km |
| Khor Fakkan | 25.3482, 56.3627 | 3.4 km |

**Nearer sea cells.** The user asked us to check Dibba, Khor Fakkan, Fujairah and Umm Suqeim for nearer sea cells. The archive model (MFWAM) has no nearer cell than 18, 10, 13 and 10 km. ECMWF WAM does have nearer cells, at 7.3, 3.4, 4.9 and 3.4 km, and it returns full 48-hour data. So the live forecast uses ECMWF WAM. Replay days have to use MFWAM, because they predate the ECMWF WAM archive. The replay card shows MFWAM's distances, which are larger.

**Place names.** Kannada and Arabic place names live in the translation files, not in config, so each language file is complete. `docs/place-names-for-review.md` lists every one for the reviewers. Descriptive Arabic names that are not official keep an asterisk until reviewed.

**Whole forms, never "name + suffix".** Kannada attaches case endings to the word (ಮಲ್ಪೆ → ಮಲ್ಪೆಯಿಂದ, "from Malpe"), so a template must never glue a suffix onto a name.
- Each harbour has a `place.<id>` name and a `place_from.<id>` phrase ("from Malpe", "ಮಲ್ಪೆಯಿಂದ", "من دبا الحصن"). Templates use whole stored forms only, so reviewers check complete words.
- A map click with no harbour name uses a fixed phrase: "from this point", "ಈ ಜಾಗದಿಂದ", "من هذه النقطة".
- Arabic does not have this problem in our templates: "from" (من) is a separate word, and no template uses an attached preposition with a place. It uses whole forms anyway, for consistency.
- A test fails if any template puts a suffix after `{place}`.

**The two rows that needed confirming:**

- **Umm Al Quwain: confirmed, at a new pin.**
  - The fishermen moved from the old Al Khor creek harbour to the new Al Naqqa / Al Meydan port on the western (Gulf) shore. Sources: The National, "UAQ fishermen have a boatful of complaints about new port" and "Dh30 million port in UAQ…"; Emarat Al Youm (2019), "ميناء مرسى الميدان".
  - The pin is inside the only breakwater-enclosed harbour basin on that shore (OSM way 302019612, Al Maidan).
  - The earlier candidate pin (25.5556, 55.5632) was the old creek harbour. Its nearest sea cell was inside the sheltered lagoon, which showed much lower waves than the open sea.
- **Fujairah: dropped.**
  - The first candidate pin is the Fujairah International Marine Club's marina, not the fishermen's port.
  - A likely site on Rugaylat Road (25.1017, 56.3595) has no source tying it to the fishermen's port.
  - It stays in config with `enabled: false`, and can be switched on once confirmed.

## 7. Replay mode

**Replay days:**
- **Karnataka: 20 May 2025.** Before the monsoon, waves build: harbours differ, and verdicts change during the day.
- **UAE: 25 February 2025.** A Shamal (the strong north-westerly wind over the Gulf) reaches the Gulf coast while the east coast stays calm.
- **Optional: Tauktae, 15 May 2021 (Karnataka).** This uses the coarse reanalysis data, so neighbouring harbours share the same numbers. Its label says "coarse data".

**How replay works:**
- **Exactly the same assessment code** runs. Only the data source and the clock change.
- The app's "now" becomes 04:00 on the replay date. The window is 48 hours, and the default departure is 05:00.
- The chat model is told the replay date as "today".
- **The model never chooses live or replay.** The page sends the mode; it is not a tool argument.

**Labels:**
- The page header carries a strong REPLAY banner whenever replay is on.
- Every card and every chat answer carries the REPLAY line with the date.
- Every pin label carries "Replay: <date>".
- Switching between live and replay clears the chat, so live and replay answers are never mixed on screen.
- The banner wording is "Replay: weather recorded on 20 May 2025. This is not the forecast as it was issued."

## 8. Chat

**What happens to each message:**
1. The page sends the message, the recent chat history, the language, the region, the mode (live or replay) and the selected map point.
2. The server builds a system prompt. It contains the local "now", the region's harbour ids and names, the last place, time and trip length used, and the rules.
3. The model must call a tool for **any** question about conditions, safety, timing or reasons. That includes follow-ups:
   - "what about the afternoon?" calls `assess_trip` again with a new departure
   - "why is it unsafe?" calls `assess_trip` again with the same arguments
   - "when is the safest time to go tomorrow?" calls `find_safest_time`
4. The server runs the tool, which is plain Python (section 11), and passes the result back to the model.
5. **By default the model writes nothing the user reads** (decided 12 Nov 2026). The reply opens with a templated line ("Here is the check."), followed by the templated result.
   - **Why:** a word blocklist cannot catch every way a model might imply safety ("good time to go", "ideal", "fine"), and a template says the same thing.
   - **The switch:** `model_sentence` in `config/app.yaml`, set per language, `false` for all three. With it off, each question makes **one** model call.
   - **If someone switches it on:** the model writes one short intro sentence, checked by the guard below. The switch and the guard stay in place for that case.
6. The reply is that sentence followed by the **templated** verdict, reasons, numbers, trip length, data line and disclaimer. All of this is rendered from the translation files by code.

**Tools.** Every parameter is required. There are no optional or nullable parameters, and no extra properties are allowed, so both providers behave the same.

`assess_trip`:
- `place`: one of the region's harbour ids, or `map_point`
- `day`: `same` (not said), `today`, `tomorrow`, `day_after_tomorrow`, `past` (yesterday...) or `later` (next week...)
- `hour`: departure hour 0-23, or -1 if the user did not say one
- `back_by_hour`: the hour the user said they will be back, or -1
- `trip_hours`: integer from 1 to 24
- `trip_length_given_by_user`: boolean

`find_safest_time`:
- `place`
- `day`: `same`, `today`, `tomorrow`, `day_after_tomorrow`, `next_48_hours`, `past` or `later`
- `trip_hours`
- `trip_length_given_by_user`

**Understanding questions (fixed 13 Nov 2026, after a live test kept answering "Which harbour?").**
- **The model never writes a date.** Its tools take a **day word** (`today` / `tomorrow` / `day_after_tomorrow`; for "safest time" also `next_48_hours`) and an **hour**. Code turns these into the exact date (`app/tools.py`, `resolve_day`).
  - **Our rule:** between 00:00 and 04:00, "tomorrow" means the coming morning, which is already today's date. The model got this wrong even when told the date.
- **Harbour aliases.** Each harbour has `aliases` in `config/app.yaml`: the local and town names people actually say. For example, Kundapura → Gangolli, Mangalore → Mangaluru, Udupi → Malpe, Dibba → Dibba Al-Hisn. Spelling slips also count ("Gangoli").
- **Defaults from the screen.** The page sends what is selected on screen: the harbour, the departure and the trip length. The chat uses these for anything the question leaves out. It **never asks for a time or a trip length**.
- **The only question the app asks is "Which harbour?",** and it lists the harbour names. It's a template, so it can be reviewed.
  It also says what the app does: "I can check the sea for one harbour and one time. Which harbour do you want to leave from? ..."

**Multi-turn rules done by code (12 Nov 2026, after testing real conversations in English, Kannada and Arabic by text and voice).**
Each was a mistake the model made at least once; code now does the part it got wrong. Tests: `tests/test_conversation.py`.
- **The previous departure is kept by code.** When the user does not say a day or time ("what about Mangalore?", "back by 9"),
  the model sends `day = same` / `hour = -1` and code reuses the previous check's departure, else the one on screen.
  *Seen:* Kannada "ನಾನು 9 ಗಂಟೆಗೆ ವಾಪಸ್ ಬರ್ತೀನಿ" and Arabic "برجع الساعة 9" moved a 14:00 departure to 05:00.
- **"Back by 9" is worked out by code.** The model passes the hour in `back_by_hour`; code takes the first 9:00 or 21:00 after
  departure (`trip_from_return`), so 14:00 → back by 9 is a 7-hour trip, marked as given by the user.
- **A harbour named in the question wins.** If the user's own words name exactly one harbour (any language, any alias,
  joined forms such as Arabic "ودبا" or Kannada "ಮಲ್ಪೆಯಿಂದ"), code uses it, even if the model kept the previous one.
  *Seen:* "طيب ودبا؟" (and Dibba?) was answered for Umm Suqeim.
- **Speech-to-text is told the harbour names** (Scribe `keyterms`: names in the screen language, English and the aliases),
  so "دبا" is heard as "دبا", not "ذبة".
- **Days outside the forecast** ("yesterday", "next week") give a templated limit, not "Which harbour?".
- **Tool choice in Kannada and Arabic.** The prompt has worked examples: "ಹೋಗಬಹುದಾ?" / "هل أقدر أطلع؟" (can I go?) always check
  that time; only "when / ಯಾವಾಗ / متى" asks for the departure windows. "Night" means 21:00.
- **A trip length the user chose stays theirs** in follow-ups ("for your 7-hour trip", not "we assumed").
- **"Here is the check." is only said when there is a check**, never in front of an error message.
- **A "when" answer speaks only the windows** (with the replay label); the example trip stays on the card.
- **"Which harbours are safe at 1 pm?"** has its own tool, `check_all_harbours` (13 Nov 2026). It checks every harbour
  at that departure. The voice keeps it short (13 Nov 2026): it names the SAFE harbours, names any UNSAFE ones
  (never left out), and sums up the rest: "Okay, leaving now on a 4-hour trip: Dibba Al-Hisn looks safe. The others
  are a caution." The card lists every harbour.
  *Seen:* the model answered this question by checking one harbour it picked itself (Abu Dhabi), and the answer did
  not name it, so it seemed to contradict the SAFE answer for Khor Fakkan given just before.
  On the page it gets its own card: harbours grouped by verdict as buttons (tap one for its reasons), with the
  disclaimer, official warnings, data line and credit; the chat bubble shows the short spoken version and the map
  pins move to the same time. *Seen:* without a card, the chat showed the long written text and the fisher asked again.
- **"Will it get worse today?" uses the day's departure windows** (find_safest_time), not one more check of the
  same hour. The prompt has examples in all three languages; the real model chose it in 12 of 12 test runs.
  *Seen:* "would the conditions become worse today, or is it always safe?" repeated the "leaving now" answer.
- **The page state is checked on arrival.** A departure that is not a whole-hour time, or a trip length outside
  1-24 hours, is dropped and the defaults are used, so a bad value can never crash the chat.
- **"Right now" is said as "now".** A departure in the current hour of the live forecast is spoken as "leaving from
  Abu Dhabi – Mina Zayed now", not "on Thursday at midnight" at 00:40 on Friday.
- **"When" answers name the harbour and end with the disclaimer** ("Leaving from Abu Dhabi – Mina Zayed on Friday ...").
- **A trip length the user says is read by code** ("a six-hour trip", "6 ಗಂಟೆಗಳ ಕಾಲ", "6 ساعات"; not clock times
  like "at 6", "ಬೆಳಿಗ್ಗೆ 6 ಗಂಟೆಗೆ", "الساعة 6"). *Seen:* "a six-hour trip" came back as "I've assumed a 6-hour trip".
  A length the user chose stays theirs if the model later falls back to the default.
- **A harbour named without a tool call is checked, not asked about.** *Seen:* "didn't you just say Khor Fakkan was
  safe?" got "Which harbour?".
- **Midnight is said as the end of the day before:** 00:00 Friday is "Thursday at midnight".
- **Memory.** Within a conversation the page sends the last 12 messages, plus the last check (harbour, departure,
  trip length, whether the user gave it) and what is on screen; code uses these for follow-ups. The server stores
  nothing. **The phone remembers the usual harbour and trip length** (13 Nov 2026), one per region, in the browser
  only (`localStorage`, key `usual.<region>`): never a forecast or verdict, so nothing old can pass for today's answer.
  It is saved when the fisher picks a harbour (tap or chat) or chooses a trip length, and on opening the page it is
  selected again, so "is it safe today?" works at once. A line in the welcome box says what is remembered, with
  **Forget**. A remembered length counts as the user's own ("as you chose"), and every answer still says the harbour
  and time back.
- **More kinds of questions (13 Nov 2026), all reviewed templates, never the model's own words** (owner's choice:
  "code + reviewed answers"). Three more tools:
  - `weather_details(detail, place, day, hour, ...)`: rain, air and sea temperature, wind direction, wave direction and
    period, sunrise and sunset, plus that trip's verdict. `detail` picks the one thing asked ("sunset?" says only the
    sun times). Air temperature and rain come with the wind request (`temperature_2m`, `precipitation`); sea
    temperature needs one extra marine request (only Open-Meteo's default marine model has it). They are details only:
    the verdict never uses them. Sunrise and sunset are worked out by code (`app/sun.py`, NOAA formulas, within a
    minute), so they also work for replay days and offline. The card's table and "More details" show them too.
    The saved replay files got these fields added on 13 Nov 2026; their existing values were checked unchanged.
  - `explain_app(topic)`: what the verdicts mean, how it decides (numbers read from `config/thresholds.yaml`), the
    sources, the near-line rule, which boats, how far to trust a forecast, the data source, replay, missing data, what
    the phone remembers, and what it cannot check (tides, currents, fish).
  - `official_info(topic)`: the official warning services with links, and emergency numbers at sea. Numbers are only
    shown once the owner approves them (`emergency_contacts` in `config/app.yaml`, each with its source); without one
    the answer says "call your local emergency number". **Approved 13 Nov 2026:** Indian Coast Guard 1554 (toll-free
    search and rescue for fishermen; Indian Coast Guard bulletin) and UAE Coast Guard 996 (UAE Government portal,
    Handling emergencies). The voice says them digit by digit ("1 5 5 4").
  - Code backstops: a tide question always gets the "what I can't check" answer (`asks_about_tides`); a part of the
    day the user said ("this afternoon") fills a missing hour (`stated_part_of_day`, greetings excluded).
    *Seen:* "the tides?" got "Which harbour?"; "this afternoon" was once answered for now.
  - Unrelated chat (cricket, etc.) is still not answered: the app asks which harbour.
- **Known limit:** a *typed* misspelling that matches no harbour ("وذبة") can still get the previous harbour. The answer always
  names the harbour, in writing and aloud, so the user hears which one was checked.

**How "safest time" is answered (decided 12 Nov 2026).** The answer is a departure **window**, never a single "best" hour.
- Code checks every whole departure hour in the search range whose trip fits inside the window.
- **A departure hour counts as SAFE only if the whole trip from that hour is SAFE.**
- Consecutive departure hours with the same verdict form a window. There are four cases:

| Case | Answer |
|---|---|
| All SAFE | SAFE for the whole period, with the range |
| Mixed | The SAFE departure window or windows |
| No SAFE departure, some CAUTION | Says plainly there is no SAFE time, then gives the CAUTION window or windows |
| All UNSAFE | Says there is no SAFE time and every departure is UNSAFE |

**The UNSAFE window is always stated.** Whenever any departure is UNSAFE, the answer ends with it, for example "UNSAFE: do not leave between Tue 20 May, 06:00 and 19:00." Leaving it out would be the wrong omission for a safety app. This applies in every case, including when every departure is UNSAFE.

- **Never "safest".** A CAUTION or UNSAFE hour is never presented as the safest time. The guard also blocks "safest", "safer", "safety" and "best" in the model's sentence.
- **Example card.** The card shows one example trip so the reasons are visible: the first SAFE departure, or else the first CAUTION departure, or else the first departure.
- **What the model is told about time ranges:** "today" means from now to 23:00 today; "tomorrow" means 00:00 to 23:00 tomorrow.

**Guard (deterministic):**
- After a tool call, the model's sentence is dropped if it contains a digit or any verdict word in any language. A neutral templated sentence replaces it.
- With no tool call, the model's reply is replaced with the templated "Which harbour?" prompt (`chat.ask_place`).
- So numbers and verdicts can only come from code.

**Providers:**
- **Groq first, Gemini as automatic fallback** (decided 12 Nov 2026, for speed). Both are called through their OpenAI-compatible chat-completions endpoints, so there is one code path.
- **Fallback triggers:** an HTTP error, rate limiting (429), a malformed tool call, or **no answer within 4 seconds**. Any of these moves to the next provider.
  - **The 4 seconds are a hard cap** (`LLM_TIMEOUT_SECONDS`), timed by the app's own clock (fixed 12 Nov 2026). Before, it was httpx's timeout, which limits each network step, not the whole call, and Groq once took 9–11 s through it.
  - **Early second provider.** If Groq has not answered after 1.5 s (`LLM_HEDGE_SECONDS`), Gemini is asked as well and the first good answer is used. Groq usually answers in 0.4–0.9 s, so this only costs a second call on the rare slow turn.
- **If every provider fails:** the chat says so plainly, and the map and verdicts keep working, because they never use the model. The message is "The chat is not working right now. The map and the colours still work: tap a harbour or the sea to check." 
- **Settings live in `.env`:** provider order, model names, reasoning effort and keys.
  - Defaults: Groq `openai/gpt-oss-120b` with `reasoning_effort=low`, then Gemini `gemini-3.5-flash-lite`.
- **Speed (measured 12 Nov 2026).** With the model's sentence off (the default), each question makes **one model call**, to pick the tool. With it on, there is a second call to write the sentence.

| Model | Time per call |
|---|---|
| `gemini-3.8-flash` | 4–5 s, whatever the thinking setting ("low" and "none" made no difference; "minimal" is rejected for this model) |
| `gemini-3.5-flash-lite` | about 1.2 s, with the same tool arguments |
| Groq gpt-oss, default reasoning | 1–3.6 s |
| Groq gpt-oss, `reasoning_effort=low` | about 0.7 s |

  - With one call per question, a question takes about 0.7 s on Groq; one measured run took 3.5 s. Groq occasionally stalls (one earlier run took 11.7 s). The 4-second timeout now hands such a call to Gemini.
- **Time format.** Groq checks tool arguments against the schema itself, and gpt-oss writes times with seconds (`05:00:00`). So the time pattern accepts optional `:00` seconds.
- **Logging:** the server logs which provider and model answered each turn.

## 9. Languages and text

- **Translation files.** All fixed interface text is in `translations/en.json`, `kn.json` and `ar.json`, one file per language. That covers labels, verdict words, reason templates, disclaimers, place names, weekday and month names, and replay labels.
- **Languages per region:** Karnataka uses English and Kannada; the UAE uses English and Arabic.
- **Switching off.** A language or a region is switched off in `config/app.yaml` with `enabled: false`, and nothing else breaks.
- **Arabic layout.** Selecting Arabic sets `dir="rtl"` on the page. Layout uses CSS logical properties, so it mirrors correctly. Numbers stay Western digits in every language.
- **Review.** The Kannada and Arabic files are drafts for native-speaker review before the demo.

## 10. The page

**Redesigned on 13 November 2026: [ui.md](ui.md) describes the page as it is now.** The list below is the original outline; everything in it is still on the page.

One plain HTML page with two JS files (`app.js`, and `wind.js` for the wind picture) and one CSS file. There is no build step. It uses MapLibre GL 4.7.1 from unpkg and a vector map from OpenFreeMap, with OpenStreetMap attribution.

**Header**
- region selector
- language selector, showing that region's enabled languages
- Live / Replay switch
- REPLAY banner when replay is on

**Map**
- harbour pins coloured by the verdict for the current departure and trip length
- click on the sea to assess that point
- clicking on land shows "pick a point at sea"

**Controls**
- departure hour within the 48-hour window
- trip length chips: 4, 6, 8, 12 hours

**Verdict card**
- a big colour and word
- place and boat class
- the reasons, from templates
- an hour-by-hour strip of coloured cells across the trip
- details: every parameter's worst value and hour, wave period and direction, wind direction, sea-cell distance, model, forecast hour, fetch time
- the Open-Meteo attribution link
- the disclaimer and official-warning links: IMD and INCOIS for India, NCM for the UAE

**Chat panel**
- the conversation
- example questions to tap

**"How we decide" panel**
- every threshold with its source document, link and paragraph
- our own rules, marked as ours

**Layout.** Built for phones first. On a laptop the map sits beside the panels.

### 10a. Voice-first page (rebuilt 13 Nov 2026)

The first page made people scroll past the map to reach the mic, and repeated every answer as a 14-line block of text. It has been rebuilt around asking by voice.

- **The voice dock.** It is always in reach:
  - **On a phone:** fixed at the bottom of the screen, on both the Answer and the Map tab.
  - **On a laptop:** at the bottom of the answer panel.
  - **Contents:** one large mic button, with a small typing box under it as the fallback.
  - **Mic states:** "Tap and speak", then red and pulsing with "Tap to stop" while recording, then "Checking…", then green with "Speaking — tap to stop".
- **Phones: Answer and Map tabs.**
  - Tapping a harbour or the sea on the map switches back to the answer.
  - Settings (region, language, replay) fold behind a "⚙ Settings" button.
  - The answer card comes **first**, above the time buttons, and the page scrolls to it when a new answer arrives.
- **Laptops** keep the map and the answer side by side, for the judges' screen.
- **The answer card, verdict first:**
  - the big colour, shape and word, and the advice
  - the harbour and the departure and return times, with **Listen**
  - one reason per parameter, each with a picture (🌊 waves, 💨 wind, 🌬️ gusts, ⛈️ thunderstorm, 🌫️ visibility)
  - the hour strip and the trip length, with a quick way to change it
  - the boat class, the far-sea-point warning, the disclaimer, the official warnings, and the forecast and fetch time with the Open-Meteo credit, all still visible
  - "More details" holds the hour table and the model names
- **Departure.** Big buttons ("Now", "This evening", "Tomorrow 5 am") replace the 48-item list. "Pick a time" opens the full list. "Tomorrow" follows the same before-04:00 rule as the chat.
- **The conversation** shows each answer as a coloured verdict badge plus the **short spoken version**, not the whole card again. The language-model provider moved into the bubble's tooltip, for the team.

## 11. The callable service (ready for voice)

**`app/service.py` is the only entry point to an assessment:**
- `assess_trip(region, place, departure_local, trip_hours, trip_length_given_by_user, mode, map_point)`
- `find_safest_time(...)`

**How each part reaches it:**
- **Map page:** calls it through `POST /api/assess` and `POST /api/assess_region` (for pin colours).
- **HTTP for other callers:** `POST /api/safest` exposes "safest time" over HTTP for the voice agent or any other client. The page itself asks for it only through the chat.
- **Chat:** calls the same functions directly.
- **Tool schemas:** defined once in `app/tools.py`.

**For the future voice agent:**
- It uses the same schemas and the same service.
- It gets the same templated text, so speech can read it out.
- It needs no change to the assessment.

## 11a. Voice (built 12 Nov 2026)

**The approach (option A, approved).** ElevenLabs is the ears and the voice; the app keeps the brain.
- **Speech-to-text:** Scribe (`scribe_v2`) turns the question into text. The language is fixed to the one chosen on screen (`eng` / `kan` / `ara`), which is more accurate than letting it guess.
- **Answering:** the text goes through **the same chat as typing**. The model picks the tool, and code decides the verdict.
- **Text-to-speech:** `eleven_v4_turbo` (ElevenLabs v4 Turbo) reads the **spoken template** produced by `explain.spoken()` word for word, in Kannada, Arabic or English. The answer is **streamed**: playback starts as soon as the first audio arrives.

**Measured on 12 Nov 2026, with your keys:**

| Step | Time |
|---|---|
| Speech-to-text | 1.4–1.7 s (Scribe v2 and v3 were both exact in all three languages) |
| Chat and check | about 1.2 s |
| First spoken audio, streamed | about 1.3 s |
| Written answer on screen | 3.0–3.3 s after the question |
| **Voice starts** | **3.5–4.9 s** after the question (9–18 s before streaming) |

**Faster voice (12 Nov 2026).** Most of the remaining time was opening a new secure connection for every call
(Groq 1.12 s on a new connection, 0.52 s on a kept one). Now:
- **One shared, kept-open connection** to each service (`app/net.py`), kept for 90 s when idle.
- **Warm-up when the mic is pressed.** The page calls `/api/voice/warm`, so the connections are ready while the fisher is still speaking. They are also opened when the server starts.
- **Speech is fetched before the page asks.** As soon as the answer is known, the server starts fetching the spoken answer from ElevenLabs. The page joins that stream, so audio is already arriving when it asks.
- **The model's hard 4 s cap and early second provider** (section 8).

| Stage, new answer (9 questions, replay days) | Before | After |
|---|---|---|
| Speech-to-text | 1.2–1.6 s | 0.7–0.8 s |
| Chat | 1.4–1.9 s | 0.7–0.9 s |
| First audio after the page asks | 1.3–1.5 s | about 0.3 s |
| **Voice starts after the fisher stops speaking** | **4.1–4.6 s** | **1.6–2.0 s** |

A repeated answer comes from the audio cache. A slow Groq turn now costs at most about 1.5 s plus Gemini's ~1 s,
not 9–11 s. Times are from the server; on a phone, add the upload of the recording and the network to the server.

**Speech model timings:**

| Model | Time to produce a short sentence |
|---|---|
| v4 Turbo | 1.5–1.7 s |
| v4 | 3.0–3.8 s |
| v3 | 2.8–5.3 s |

All three speak Kannada through the standard speech endpoint.
- **What the model never does:** it never writes what is spoken. `model_sentence` stays off, and the spoken text is built only from translation templates.

**Why not an ElevenLabs voice agent:** its own language model phrases the spoken reply, and we could not confirm that it reads tool output verbatim. Its Kannada support was also unconfirmed.

**The spoken template** is conversational (approved 13 Nov 2026), built only from translation templates; no model writes it:
1. a replay line first, when in replay: "This is a replay of 20 May 2025."
2. the question said back with the verdict: "Okay, leaving from Malpe on Tuesday at 5 in the morning: that's a caution."
   The opener (Okay / Alright / Right) is picked by code from the place and time, so the same question always sounds the same.
3. short advice: "Be careful out there." / "Please don't take a small boat out."
4. one reason per parameter, joined the way people talk: "Watch out for the waves: up to 1.9 metres around 11 in the
   morning, over the caution line." Then "Also ..." and "And ...". The threshold numbers stay on the card.
5. spoken numbers are rounded (waves to 0.1 m, wind and gusts to whole km/h). If rounding would give a different
   result in the verdict code, the exact value is said instead (`say_num`).
6. "You'd be back around 11 in the morning."
7. "I've assumed a 6-hour trip, so tell me if yours is different." only when the length was assumed
8. "It's a forecast, not a promise, so check the official warnings too. Stay safe."

No filler words ("um", "uh"): they make a safety answer sound unsure, add length and do not translate.
The card on screen still carries the exact values, thresholds, data line, fetch time, model and Open-Meteo credit.

Length history (the shortening of 12 Nov; the conversational style added about 4-6 s per answer):

| Same 9 questions (3 per language) | Before | After |
|---|---|---|
| English answer | about 31 s | about 22 s |
| Kannada answer | about 44 s | about 29 s |
| Arabic answer | about 55 s | about 41 s |

Checked by transcribing the real speech back to text in all three languages: every word and number came back as written.

**Voices** (my choice; reviewers should listen). Sample answers made by the app are in `docs/voice-samples/` (regenerated 13 Nov 2026 in the conversational style; the text of each is in its README). The aim is a calm, clear "radio weather bulletin" style, not sales or drama:

| Language | Voice | voice id |
|---|---|---|
| English | Riya Rao, warm, calm, trustworthy Indian English; one of the most-used ElevenLabs voices (replaced Anya on 12 Nov 2026) | `l69wlWTZVIKv0UxMucTn` |
| Kannada | Krishna Priya M, Kannada news anchor, composed, crisp diction | `z5dCxveFRvWeqsaKgMqe` |
| Arabic | Heba Mansuri, calm and trustworthy, Saudi Gulf accent, made for GCC customer care | `QsV9PCczMIklRM6xLPAS` |

These were chosen over livelier "radio presenter", "storytelling" or "sales" voices. The Arabic voice is Saudi rather than Emirati, because no Emirati voice in the library fitted the brief. Gulf listeners understand it easily.

**Page:**
- **Mic button:** one large "Tap and speak" button. It turns red while recording and stops by itself after 20 seconds.
- **Listen button:** every card has one. The server works the answer out again and speaks it; spoken text is never taken from the page.
- **Hidden when unavailable:** both buttons stay hidden when the voice isn't available: no key, voice switched off, or a language without a voice.

**Failures:**
- **Speech-to-text fails:** the page says "The voice is not working right now".
- **Text-to-speech fails:** the written answer still appears, with that note.
- **Nothing was heard:** a templated "I did not hear a question" is spoken.

**Credits:**
- Audio is cached by its exact text, model and voice, so rehearsals don't re-spend credits.
- Text over `max_spoken_chars` (1500) is never sent.
- `python -m app.voice` checks the key and each voice. Listing the account and its models needs the optional `user_read` and `models_read` key permissions; speaking does not.

**Privacy:** recordings go to ElevenLabs for transcription.

## 12. Code layout

```
run.bat                  one command: create venv, install, start server, open browser
requirements.txt         fastapi, uvicorn, httpx, pyyaml, python-dotenv, pytest
.env.example             LLM provider order, model names, keys (copy to .env)
config/app.yaml          regions, harbours, languages, window, trip, replay days, cache, models
config/thresholds.yaml   thresholds, sources, margin, boat class
translations/*.json      all fixed text per language
app/config.py            load and validate config
app/assessment.py        pure verdict logic: no network, no LLM
app/weather.py           Open-Meteo fetch, cache, replay files
app/explain.py           render templated text from an assessment
app/service.py           the callable service: fetch, then assess
app/tools.py             tool schemas shared by chat and (later) voice
app/voice.py             ElevenLabs speech-to-text and text-to-speech, audio cache, `python -m app.voice` check
app/llm.py               Groq then Gemini client (order in .env) with 4-second timeout, fallback and logging
app/chat.py              chat loop, system prompt, guard
app/main.py              FastAPI routes and static files
static/                  index.html, app.js, style.css
data/replay/             committed replay data
data/cache/              live cache (git-ignored)
tests/                   pytest: assessment, safest time, explain, guard, config
docs/                    this design, place names for review
```

## 13. Testing

- **Every threshold fires.** `tests/test_assessment.py` checks each parameter:
  - just below the near-line value gives SAFE
  - within the margin gives CAUTION with "near"
  - at the CAUTION line gives CAUTION
  - at the UNSAFE line gives UNSAFE
  - thunderstorm codes give CAUTION
  - visibility, the "lower is worse" parameter, works in the inverse direction
- **Missing and stale data.** A missing value in any one hour, trip hours beyond the window, and stale data all give CAUTION and never SAFE. The stale case is also tested end to end through the service, with a 7-hour-old cache file.
- **Exact lines.** Values exactly on the near-line (33.3 km/h, 1.125 m, 36 km/h, 2037.2 m) give CAUTION.
- **The trip window.** The trip reads its departure and return records, both included, and a record exactly at the window end counts as inside the window.
- **Switching things off.** A harbour switched off does not break replay offline, and a language switched off is never served (requests fall back to English).
- **Bad inputs.** Trip lengths of 0 or 25 hours, bad map points and unknown languages all get a clean message, never a server error.
- **Worst hour and drivers.** The worst hour decides the trip, and the drivers list names the right parameter and hour.
- **Safest time** has a test for each of the four cases, on recorded replay data:
  - all SAFE: Dibba, 25 Feb 2025
  - mixed, two SAFE windows: Khor Fakkan, 25 Feb 2025
  - CAUTION only: Gangolli, 20 May 2025
  - all UNSAFE: Tauktae, 15 May 2021
  - There is also a test that a departure is SAFE only if its whole trip is.
- **Text and guard.**
  - Every template key exists in every enabled language.
  - The guard drops digits and verdict words.
- **No network.** Tests use fixed hourly data, so none of them touch the network.

## 14. Calls made by the builder (not from the user)

- The live wave model is ECMWF WAM and the replay wave model is MFWAM (section 6).
- Wind is requested at the wave model's sea cell.
- Clicks on land are detected with the Elevation API. If that service can't be reached, the click is accepted, but a point more than 20 km from the nearest wave-model sea cell is still refused. That applies to "safest time" as well.
- Live data is cached for 30 minutes.
- The replay clock starts at 04:00, with a default departure of 05:00.
- The guard rules are as described in section 8.
- **Chat time words:** "morning" means 05:00, "afternoon" 14:00, "evening" 17:00 and "night" 21:00, unless the user gives an hour. "5 tomorrow" with no am/pm means 05:00. These are set in the system prompt in `app/chat.py`.
- **Wave heights show 2 decimals, and wind and gusts 1 decimal**, so a value never rounds onto a line it has not reached. For example, 1.98 m must not read "2.0 m", and 42.6 km/h must not read "43", which is the UNSAFE line. Line values print exactly as configured.
- **The page script** treats the region's times as fixed wall-clock times, independent of the browser's time zone. It refreshes its clock every 5 minutes in live mode, and ignores any answer that arrives after a newer request was made. An answer from the chat moves the departure, trip-length and place controls to match it.
- **Source titles and notes** on the "How we decide" panel stay in English in every language, because the documents themselves are in English.
- **Verdict shapes:** every verdict is shown with colour, shape and word together, so it still reads without colour vision. The shapes are a circle (SAFE), a triangle (CAUTION) and a square or octagon (UNSAFE).
- **Attribution text:** "Weather data by Open-Meteo.com" is kept in English in every language, exactly as required.
- Times use 24-hour format, and numbers use Western digits.
- The design file lives at `docs/design.md`.
- A `.gitignore` is created so that `.env` and the cache are never committed. The folder is not made into a git repository unless you ask.
