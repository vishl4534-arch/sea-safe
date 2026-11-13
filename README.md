<img src="brand/sea-safe-mark.svg" alt="Sea Safe" width="96">

# Sea Safe

Sea Safe helps small-scale fishers decide whether to take a small boat out to sea. You pick a harbour or a point at sea on the map, or ask in plain words, for example "Is it safe to leave from Malpe at 5 tomorrow morning?". The app answers **SAFE**, **CAUTION** or **UNSAFE**, with the reasons, in English, Kannada or Arabic.

It covers two regions:
- the Karnataka coast (English and Kannada)
- the UAE coast (English and Arabic)

Built for the NOVA Hackathon, Track D (AI & Autonomous Systems). The full design is in [docs/design.md](docs/design.md).

## Run it (Windows, one command)

1. Install **Python 3.11 or newer** from python.org. Tick "Add python.exe to PATH".
2. Double-click **`run.bat`**, or run this in PowerShell from this folder (PowerShell needs the `.\`):

```bash
.\run.bat
```

**What `run.bat` does:**
- The first run creates a virtual environment (`.venv`) and installs the packages. This takes about a minute.
- It creates `.env` from `.env.example` if `.env` doesn't exist yet.
- It starts the server and opens http://localhost:8000.

**The map works without any keys.** The chat needs a language-model key: put `GEMINI_API_KEY` and/or `GROQ_API_KEY` in `.env`, then run `run.bat` again. `.env` is never committed.

Running the tests needs no keys and no network:

```bash
.\.venv\Scripts\python -m pytest -q
```

## How a verdict is made

```
question or map tap
   -> (chat only) the language model picks the place, time and trip length and calls a tool
   -> app/service.py         fetch Open-Meteo data for the place (cached)
   -> app/assessment.py      fixed rules from config/thresholds.yaml -> SAFE / CAUTION / UNSAFE
   -> app/explain.py         reasons and numbers from translations/<lang>.json
   -> (chat only) the model adds ONE short sentence, checked by a code guard
```

- **The language model never decides or changes a verdict or a number.** The page and the chat both call the same `app/service.py`, and a voice agent can later call it the same way, using the same tool schemas in `app/tools.py`.
- **The worst hour of the trip decides.** A trip reads every hourly record from departure to return, both included.
- **Missing data, stale data (over 6 hours old), or values within 10% of a caution line all give CAUTION, never SAFE.**
- **HTTP endpoints for other callers.** `POST /api/assess` checks one trip. `POST /api/safest` gives the departure windows for "when is the safest time". A voice agent can call these directly.
- **Every threshold and its published source** is in `config/thresholds.yaml`, and on the "How we decide" panel in the app.

## Where things live

| To change | Edit |
|---|---|
| Thresholds and their sources | `config/thresholds.yaml` |
| Regions, harbours, languages, the 48-hour window, the trip length (default 6 hours, an assumption), replay days | `config/app.yaml` |
| Any text on screen | `translations/en.json`, `kn.json`, `ar.json` |
| Language-model order, model names, keys | `.env` |

- **Switching things off.** To turn off a language, region or harbour, set `enabled: false` in `config/app.yaml`. For example, set it on `kn` to hide unreviewed Kannada on demo day.
- **Reviewer list.** [docs/place-names-for-review.md](docs/place-names-for-review.md) lists every Kannada and Arabic place name for the native-speaker reviewers.

## Data

- **Waves.** Open-Meteo Marine API. Live forecasts use ECMWF WAM; replay days use Météo-France MFWAM.
- **Wind, gusts, thunderstorms, visibility.** Open-Meteo Forecast API, plus the Historical Forecast API for replay days.
- **Map.** A free vector map from OpenFreeMap (OpenStreetMap data), drawn with MapLibre GL and recoloured so the sea leads.
- **Wind picture.** The moving streaks on the map use Open-Meteo Forecast API wind on a grid of points. It is a picture only and is never used for a verdict.
- **Credit.** Weather data by [Open-Meteo.com](https://open-meteo.com/). Every answer shows this credit, the forecast hour, the time the data was fetched, and the distance to the sea point used.
- **Cache.** Live data is cached in `data/cache/` for 30 minutes. If the internet drops, the last data is shown with its age. Once it is older than 6 hours it counts as missing, which means CAUTION.

## The page

The page was redesigned on 13 November 2026: a dark "pre-dawn" look, a map where the sea leads, moving wind, a 48-hour time slider, gauges and hour bars on the card, and a voice orb. [docs/ui.md](docs/ui.md) explains every part, which parts are display only, and what still waits for the owner's approval. The page as it was before is in `backup/ui-before-redesign-2026-11-13/`.

## Replay mode

The sea may be calm on demo day. The "Forecast or replay" menu runs the same assessment on recorded weather from a past day. Each day is labelled as a replay everywhere it appears.

| Region | Day | What it shows |
|---|---|---|
| Karnataka | 20 May 2025 | Waves build before the monsoon. Harbours differ, and verdicts change through the day |
| UAE | 25 February 2025 | A Shamal wind on the Gulf coast while the east coast stays calm |
| Karnataka (optional) | 15 May 2021, Cyclone Tauktae | Uses coarse data: about a 50 km grid, so neighbouring harbours share the same numbers |

**Replay works offline.** Its data is saved in `data/replay/`.

## Voice (ElevenLabs)

Tap **Tap and speak**, ask your question, then tap again to stop. The app does the following:
1. ElevenLabs Scribe v3 turns your speech into text, in the language chosen on screen.
2. The same chat as typing picks the check, and code decides the verdict.
3. An ElevenLabs v4 Turbo voice reads the reviewed **spoken template** word for word. The audio is streamed, so the voice starts about 4 seconds after you finish speaking. That's the verdict, the advice, one reason per parameter, the times, the trip length and "forecast, not a guarantee".
4. The written answer and the card, with the Open-Meteo credit and the fetch time, appear on screen at the same time.

Every card also has a **Listen** button, which reads that card aloud.

**Setup:**
- Put `ELEVENLABS_API_KEY` in `.env` and restart.
- Run this to confirm the key, the model and each voice:

```bash
.\.venv\Scripts\python -m app.voice
```

**Voices:** set in `config/app.yaml` under `voice.languages`.

| Language | Voice |
|---|---|
| English | Riya Rao, warm and calm Indian English |
| Kannada | Krishna Priya M, Kannada news anchor |
| Arabic | Heba Mansuri, calm Gulf (Saudi) customer care |

**Cost:**
- Each spoken answer is about 350–650 characters, which is roughly the same number of ElevenLabs credits.
- Audio is cached by its exact text, so replaying a rehearsed answer costs nothing.
- Answers longer than `max_spoken_chars` are never sent to ElevenLabs.

**Turning it off:** set `voice: enabled: false` in the config. The buttons disappear, and everything else keeps working.

**Privacy:** the recorded question is sent to ElevenLabs for transcription.

## Language-model providers

- **Fallback order.** Groq is tried first, at about 0.7 s per call. If it errors, is rate-limited or returns a malformed tool call, the app moves on to Gemini (`gemini-3.5-flash-lite`) automatically.
- **Logging.** The server log shows which provider answered and how many model calls a question took, for example `LLM answered by groq (openai/gpt-oss-120b)`.
- **Settings.** The order, the model names and the reasoning effort are set in `.env`.
- **Templates only, by default.** The model's own words never reach the user: `model_sentence: false` for every language in `config/app.yaml`. The model only reads the question and picks the tool, which is one call per question. Setting it to `true` for a language lets the model add one intro sentence, checked by a word guard.
- **Timeout.** If a provider hasn't answered within 4 seconds (`LLM_TIMEOUT_SECONDS`), the next one is tried. If all fail, the chat says so, and the map and the colours keep working.

## Important

This is a forecast tool, not a guarantee. Always check the official warnings:
- India: [IMD](https://mausam.imd.gov.in/) and [INCOIS](https://incois.gov.in/portal/osf/osf.jsp)
- UAE: [National Centre of Meteorology](https://www.ncm.gov.ae/)
