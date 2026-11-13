I'm building "Sea Safe" for the NOVA Hackathon (Track D, AI & Autonomous Systems). This folder is empty and you are starting the project from scratch.

## Goal

A web app that helps small-scale fishers decide whether to go out to sea. A user picks a coastal location on a map, or asks in plain language ("Is it safe to leave from Malpe at 5 tomorrow morning?"), and gets a clear SAFE / CAUTION / UNSAFE assessment for that place and time, with the reasons, in their own language.

For this first session, get the core working end to end: live marine data, the assessment, an interactive map, and a conversational chat in both languages. A voice interface (speak a question, hear the answer) comes next, so the assessment must be reachable as one callable service that a voice agent can later use as a tool.

## Context

- Users are fishers with limited literacy and little experience of apps. Answers must be short and plain, with no jargon.
- Region: the Karnataka coast, India, with a fixed set of about 8 to 10 fishing harbours as map pins, plus click-anywhere on the sea.
- Languages: English and Kannada. A native speaker will review the Kannada.
- Forecast window: the next 48 hours.
- This will be demoed live to judges, who score against these deliverables:
  - a working web app with a conversational interface
  - English plus at least one more language
  - integration with a public marine weather API
  - an interactive map with location selection
  - clear safe / caution / unsafe visual indicators
  - an explanation of each recommendation
  - a working demonstration on at least one coastal location
- The sea may be calm on demo day, which would make every location look the same.

## Constraints

- Data: free public sources only. Use the Open-Meteo Marine API for sea state and the Open-Meteo forecast API for wind. No paid APIs, no paid map tiles, no model training.
- The verdict is computed by deterministic code from named weather and sea-state parameters against thresholds. The language model never decides, changes or restates differently a verdict or a number. Its job is to understand the question, call the assessment, and explain the result in the user's language.
- Thresholds live in one config file, each with the published source it came from. Do not invent threshold values silently: show me the table with sources and get my approval before relying on it.
- Every assessment shows the parameters that drove it, the forecast time it applies to, when the data was fetched, and a visible "Weather data by Open-Meteo.com" attribution link.
- Uncertainty: never promise safety. Missing data or values close to a threshold resolve to CAUTION, never SAFE. Every answer makes clear it is a forecast, not a guarantee, and points to official warnings.
- Region, harbours, languages and forecast window are configuration, not scattered through the code. All fixed interface text sits in one translations file so it can be corrected.
- Include a replay mode that runs the same assessment on a past rough-weather day, clearly labelled as a replay wherever it appears.
- Tests for the assessment logic must prove each threshold actually fires, including the missing-data case.
- Secrets go in .env and are never committed. Ask me which LLM provider and key to use.
- It must run locally on Windows with one command, with a README explaining how.
- Keep it small and simple. I need to be able to explain every part of it to judges.

Before writing any code, ask me anything whose answer would change what you build.
