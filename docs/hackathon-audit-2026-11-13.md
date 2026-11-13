# Sea Safe: hackathon audit and submission priorities

Audit date: 13 November 2026. Submission deadline supplied by the owner: noon today, Asia/Dubai.

## Recommendation

Sea Safe already has enough functionality for a credible working demonstration. The best use of the remaining morning is to correct trip interpretation, make the existing decision flow easier to demonstrate, and produce convincing evidence in the seven-slide presentation. Do not start a new warning-feed integration, notification system, route planner, or model migration before this submission.

The strongest product proposition is: **A fisher asks in their own language about a specific trip, receives a traceable weather assessment, and can explore alternative departure times.** The language model interprets the request; shared deterministic code evaluates the weather. The remaining weakness is that incorrect interpretation can cause the code to assess a different trip.

## Presentation guide

Source: `C:/Users/Lenovo/Downloads/NOVA_2026_Final_Presentation_Guide.xlsx`, worksheet `NOVA Presentation Guide`.

- A2 and A15: maximum seven slides.
- A17–A18: prioritize actual implementation and include evidence, screenshots and diagrams.
- A22: slide 5 must show what is actually built.
- B5:C11: overview, problem, solution/innovation, architecture, demonstration, results/impact/scalability, conclusion/team.
- The guide does not contain numerical judging weights or the presentation duration. This audit does not invent either.

These are presentation requirements supplied as task context. They are not authorization to publish, create a repository, or submit the project.

## What was verified

- Read the application, configuration, translations, design documents, and test coverage.
- Ran the existing suite: **362 passed in 4.03 seconds**. This measures the existing test cases, not field safety or natural-language accuracy.
- Ran eight actual typed-chat requests against the configured language-model service using cached replay weather. Requests took approximately **0.30–0.68 seconds** locally. This is a small warm-cache text sample, not a voice or production latency benchmark.
- Simple English, Kannada and Arabic trip requests produced localized results with the expected place/time. Safest-time and emergency-information requests also returned answers. Three deliberately difficult time/duration requests exposed the errors below.
- Reproduced the overnight-trip error through the browser as well as the HTTP API.
- Inspected the English phone flow, desktop controls/map, and Arabic right-to-left phone layout.
- A live Malpe assessment returned a forecast with a two-minute-old cache, no fetch error, and the live model identified in the result.
- Tested malformed model arguments and invalid numeric inputs with isolated local calls.

No application source was changed. Microphone transcription, newly generated speech, real-device outdoor use, and native-speaker comprehension were not independently retested during this audit. Existing voice samples and earlier timing claims are not fresh audit measurements.

## Status of items 1-6 (fixed on 13 November 2026, morning)

All six were fixed after this audit. The old files are in `backup/before-audit-fixes-2026-11-13/`. Regressions are in `tests/test_audit_2026_11_13.py`; the full suite is now **445 passed** (450 after the features below).

| Item | What changed |
|---|---|
| 1. Overnight return | The tools now carry a return day (`back_day`). A return on a later day, or a return hour that can only fall on the next day, is refused with a reviewed message asking for the trip length in hours. A trip stated in hours across midnight ("5 pm for 16 hours") is still checked. |
| 2. Minutes, long trips | The tools carry `minute`; code also reads minutes in the user's words (en/kn/ar). A time not on the hour is refused, never rounded. A trip over 24 hours is refused, never capped (the model may now report up to 168 so code can see it). Direct API times with minutes are refused, never cut. |
| 3. Tool-call validation | Each call is checked against its own schema (known tool, object, required fields, no extras, types, enums, ranges) before it runs; a bad call falls back to the next provider, then to the reviewed "unavailable" message. Chat and voice history/context are checked by the API (roles, sizes, turn count, context fields), voice before any paid transcription. |
| 4. Invalid weather values | Non-numbers, NaN, infinity and impossible values (our own sanity limits, far beyond every caution line) count as missing data, so CAUTION. |
| 5. Caution text colour | Fixed: dark text on amber again. |
| 6. Overlapping chat requests | The page asks one question at a time (typed or spoken); Send, suggestions and the mic wait until the answer is in. |

Checked with the real model on replay data, 13 Nov: the audit's three questions are now refused with the right message (en); the overnight question is refused in Kannada and Arabic; "5 ونص" (5:30) is refused in Arabic; "back by 9" after 2 pm and "5 tomorrow morning" are still checked normally. Refusal texts in Kannada and Arabic are drafts for the native-speaker review.

**Features (13 Nov, after the fixes):** 1, 2, 3, 6 and 7 were added, and 5 in a lite form (rechecks while the page is open, no server or notifications). 4 and 8 were deliberately not built. Details in `docs/ui.md`, section 2a.

## Fix before adding features

### 1. Overnight return times can truncate a trip — high priority

Actual question: “Can I leave Malpe today at 5 pm and return tomorrow at 9 am?”

Observed result: departure 17:00, return **21:00 the same day**, duration **4 hours**, described as the user's choice. The requested trip is 16 hours. The remaining overnight hours are never evaluated.

`app/tools.py:33` accepts only a return hour and selects the next matching morning/evening occurrence. The tool schema cannot preserve an explicit return date. `app/chat.py` then overrides the duration using that calculation.

Required behavior: preserve departure and return dates, minutes and explicit AM/PM; ask a focused clarification when genuinely ambiguous. Until that is implemented reliably, reject unsupported overnight expressions with a clear limitation rather than producing a shorter-trip verdict. Add regression cases in all supported languages.

### 2. Minutes and unsupported durations are silently changed — high priority

Actual question: “Can I leave Malpe today at 5:30 am for 6 hours?”

Observed: a 05:00–11:00 assessment. `app/service.py:127` also truncates direct API timestamps to the hour. The chat tool represents departure only as an integer hour.

Actual question: “Can I go from Malpe today at 5 am for 30 hours?”

Observed: a 24-hour assessment. At `app/chat.py:271`, an explicitly stated duration outside the supported range is discarded, allowing the model's substitute to be used.

Required behavior: reject unsupported precision/durations clearly, or preserve the requested times and assess all overlapping hourly intervals conservatively. Do not silently round or clamp. Display a compact, editable “Trip understood” summary before relying on the verdict.

### 3. Model output validation checks JSON, not the tool schema — high priority

`app/llm.py:49` accepts any parseable JSON arguments. In isolated calls, arguments `[]` passed `_valid` but raised `AttributeError` downstream. Arguments `{"hour":"tomorrow"}` passed `_valid` but raised `ValueError` before the guarded section of `_run_tool`.

Required behavior: validate tool name, object shape, required fields, types, enums and bounds before execution. Trigger the existing provider fallback on invalid arguments. Return a reviewed error if neither provider supplies a valid call. Validate client history/context as well; `list[dict]` is too permissive for a public endpoint.

### 4. Invalid weather values can look safe — defensive correctness

With the other inputs calm, direct calls to the assessment returned SAFE for both `wave_height = NaN` and `wave_height = -2`. Missing `None` is handled correctly, but invalid numbers are not.

Required behavior: normalize non-finite, wrong-type and physically invalid measurements to unavailable data before evaluation. Test invalid weather codes too. This was a synthetic test; it is not evidence that Open-Meteo currently supplies these values.

### 5. Caution text colour is broken — quick visual fix

`static/style.css:29` defines `--caution-ink: var(--caution-ink)`, a self-reference. The caution banner visibly uses pale text on amber. Set a real dark foreground value and verify all caution badges and labels at phone size.

### 6. Overlapping chat requests can overwrite newer context — code-review finding

`static/app.js:713` allows multiple sends. The sequence check at line 719 changes for region/mode resets, not each message. An earlier response can arrive last and replace the latest card/context.

Required behavior: serialize conversational requests, or use a per-turn sequence with consistent history handling. This was identified from code, not reproduced with controlled network delay in the browser.

## Important limits to explain accurately

**Official warnings are linked, not ingested.** `config/app.yaml` holds links, and `app/explain.py:528` builds static guidance. An active official warning currently cannot override a benign model forecast. Do not present the prototype as checking whether authorities have permitted a trip.

**The assessment follows time at one forecast location.** It does not evaluate a boat's outbound route, fishing grounds and return corridor. In the Dibba replay example, the weather cell was 18.4 km from the harbour and the app correctly disclosed that distance. Put location coverage near the main answer; do not imply harbour-mouth or route-navigation precision.

**Boat length alone does not establish a vessel's design category.** The current thresholds apply one profile to small open boats under 10 m. The cited FAO document distinguishes vessel design categories and requires adaptation to vessel type, use and area. Obtain maritime review of the operational rules; published threshold sources and owner approval are not field validation. [FAO/ILO/IMO safety recommendations, sections 1.1 and 1.2.14](https://www.fao.org/docrep/017/i3108e/i3108e.pdf).

**Offline replay is not a fully offline product.** The server has saved replay data, but the client has no service worker/installed offline package. Map assets and fonts are external, and chat/voice depend on external providers. Describe the current capability as cached replay assessment. A browser reload without connectivity and without a running local server is a different requirement.

**Tests are not proof of real-world safety.** Do not claim forecasting accuracy, prevented accidents, adoption, or lives saved without measurements. Record multilingual task success separately from deterministic rule tests. New Kannada/Arabic interface wording is still described as draft in `docs/ui.md`.

## Features worth adding, in order

| Priority | Addition | Smallest useful implementation | Timing |
|---|---|---|---|
| 1 | Trip understood + edit | Clearly show harbour, departure date/time, return date/time and duration; visibly flag defaults; correct or reject unsupported input | Today, alongside fixes |
| 2 | “Check safer departure times” action | Reuse the existing `find_safest_time` service directly from CAUTION/UNSAFE cards; retain place and duration; explicitly say when no SAFE window exists | Only after fixes pass |
| 3 | Compact answer | Verdict, main reason and trip summary first; detailed gauges below; retain attribution and uncertainty; direct Listen action | Small polish only today |
| 4 | Official-warning integration | Structured, location/time-matched bulletin with issuer, validity, checked time and source; explicit unavailable state; deterministic precedence rules reviewed by a domain expert | After submission |
| 5 | Watch my trip | Save an explicit trip and opt in to changes; server-side rechecks, deduplication, expiration and notification delivery; show what changed and when | After submission |
| 6 | Real offline access | Cache app shell, translations, last trip assessment and selected audio; prominent age/expiry; clearly disable unsupported live functions offline | After submission |
| 7 | Shareable trip card | User-initiated export with place, departure/return, verdict, source, timestamp and replay label; never automatically message contacts | Later |
| 8 | Vessel and journey support | Expert-reviewed vessel profiles and weather samples along planned waypoints; state that this is not navigational routing | Later, after validation |

Safest-time search, checking all harbours, remembered harbour/trip length, emergency contact information, voice output and three languages already exist. Present and improve them rather than spending time rebuilding them under new names.

The largest later improvement is a complete journey: **plan a trip, check warnings, monitor changes, and tell the fisher why the plan needs attention**. Do not describe this as implemented today.

## Differentiation for judges

INCOIS SAMUDRA already provides marine alerts, ocean-state forecasts and marine services. Sea Safe should demonstrate the value of its conversational trip workflow, transparent rules and local-language delivery rather than claiming weather maps or alerts alone are novel. [Official SAMUDRA product page](https://www.incois.gov.in/site/SAMUDRA/index.html).

If tides/currents are added later, use an appropriate validated source and clearly define the use. Open-Meteo explicitly cautions that its modeled coastal tides/currents have limited accuracy and are unsuitable for coastal navigation. [Marine API documentation](https://open-meteo.com/en/docs/marine-weather-api).

## Seven-slide content plan

| Slide | Sea Safe content | Evidence |
|---|---|---|
| 1 — Overview | One sentence about helping small-scale fishers assess a trip in their own language; actual team/institution | Product name and team details |
| 2 — Problem | A before-dawn departure decision; changing conditions during the trip; language and literacy barriers | A concrete user scenario; label it illustrative unless based on an interview |
| 3 — Solution and innovation | Voice/text request, trip interpretation, worst-hour weather check, understandable reasons and alternative departures | Show the journey with three or four steps |
| 4 — Architecture | Browser/mic → transcription → language-model tools → shared service → weather/cache → deterministic rules → reviewed text/speech | Architecture diagram that matches the current code; JSON file cache, not an invented database |
| 5 — Demonstration | One local-language trip, a follow-up changing duration/time, a clearly labeled rough-weather replay, then safer-time search | Working demo or short real recording; future features stay off this slide |
| 6 — Results, impact and scalability | 362 current tests; scoped local text timing; three languages; two configured regions; limitations and next validation step | Update test count after fixes; separate measured results from intended impact |
| 7 — Conclusion and team | Key takeaway, real contributions, repository/product/video links and Q&A | Verify every shared link from a signed-out browser |

The workspace is not currently a Git repository. The presentation guide requests repository and live-product links, but the source folder itself is not evidence those links exist. Prepare and verify the submission access path, without exposing `.env` or private caches. If public hosting is used, add request/upload size limits and rate limits around paid AI endpoints. The current voice endpoint reads the full upload before validation, and no application-level rate limiter was found.

## Morning plan (Dubai time)

Suggested allocation, not a promise of implementation duration:

- **08:20–09:20:** correct time/duration handling and tool validation; add targeted regressions; fix caution foreground.
- **09:20–09:45:** if the core passes, add the safer-departure button and compact trip summary. Stop new feature work at 09:45.
- **09:45–10:30:** prepare seven slides, architecture diagram and actual screenshots. Keep future features clearly labeled.
- **10:30–11:00:** rehearse and record the demo with a backup video. Verify speech audibility and all three verdicts using labeled replay scenarios.
- **11:00–11:30:** verify required files and links, remove secrets from any source package, check access without the owner's login, and submit.
- **11:30–12:00:** reserve for upload or portal failures.

No feature list can guarantee a win. A reliable demonstration, clear differentiation, truthful evidence and confident technical answers are the strongest controllable improvements before this deadline.
