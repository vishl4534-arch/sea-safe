# Sea Safe: the page (redesign of 13 November 2026)

This replaces the short page description in [design.md](design.md) section 10. The rules for verdicts, data and wording are unchanged and still live in design.md.

The page before this redesign is saved in `backup/ui-before-redesign-2026-11-13/`.

## 1. The idea: "night watch"

A fisher decides in the dark before dawn. The page is black and dark gray, so the only colour on screen is the answer. Everything that moves on screen shows real data. (The first version used navy and teal; the owner asked for black and dark gray on 13 November 2026.)

Colour is kept for meaning:

| Colour | Means | Used for anything else? |
|---|---|---|
| Green, amber, red | The verdict: SAFE, CAUTION, UNSAFE | No |
| White | Something you can press, or what is chosen; calm wind on the map | No |
| Purple | Replay: recorded weather, not a forecast | No |

A verdict is always **colour + shape + word** together: circle = SAFE, triangle = CAUTION, octagon = UNSAFE. The same three shapes are used on the card, the map pins, the hour bars, the chat badge and the time slider.

## 2. What is on the page

**The stage (the map)**
- **Map.** MapLibre GL draws a free vector map from OpenFreeMap (no key). The page recolours it so the sea carries the light, and switches roads and buildings off.
- **Harbour pins.** One shape per harbour, coloured by the trip verdict. On the first load of a region the pins light up one after another. The chosen harbour pulses slowly.
- **Wind picture.** Thin streaks drift over the sea the way the forecast wind blows. See section 3.
- **Time slider.** One slider over the 48-hour window. Dragging it changes the departure hour: the pins recolour at once, the wind moves to that hour, and the card follows when the hand rests. The ribbon on the slider shows the chosen harbour's verdict for leaving at each hour. The lighter bands are daylight (sunrise to sunset, from `app/sun.py`). The play button steps through the hours.
- **Region switch.** The camera flies to the new coast.

**The answer card**
- **Verdict.** The colour washes out from the shape, then the word and the advice arrive.
- **Trip facts.** Times, trip length (with a pencil to change it) and boat class, using the same reviewed sentences as before.
- **Reasons.** The same template sentences as before, with a line icon each.
- **Gauges.** One per verdict parameter: the worst value of the trip on a line with the caution and unsafe lines marked. The striped part before the caution line is our own 10% rule.
- **Hour bars.** One bar per trip hour. Height = how close that hour comes to a caution line; colour and shape = that hour's verdict. An hour with no data is drawn striped.
- **Small print.** Disclaimer, official warnings, forecast and fetch times, Open-Meteo credit, and the details table. Nothing was removed.

**The conversation**
- Messenger style: answers on the left with the app's mark, the fisher's questions on the right (mirrored in Arabic). Each message has its time.
- An answer with a verdict carries the verdict badge (shape and word), short bullet points and an hour strip that opens that answer's card in the slide-up sheet (section 2d). The strip (13 Nov 2026, owner's pick, replacing "See the full answer") has one small bar per trip hour, coloured by that hour's verdict and as tall as the hour comes to a caution line (the card's hour bars in small, with the dashed caution line), the trip's times, and "Why CAUTION? ›" (`chat.why`, kn/ar drafts). Answers with no verdict of their own (safer times, all harbours) say "Full answer ›". The same strip is used in the voice-mode transcript.
- Three moving dots while the answer is worked out. A question said into the mic shows a small mic icon.
- Suggested questions sit just above the mic until the conversation starts.

**Menus**
- "Forecast or replay" and "Pick a time" open a list drawn by the page, not the browser's own drop-down, so they look the same on every phone. Pick a time shows the 48 hours as small buttons, one group per day. Arrow keys, Enter and Escape work.

**The voice dock**
- The mic is a round orb. It moves with the real sound: the fisher's voice while recording, the answer while it is spoken.

## 2b. Conversation first (13 November 2026, owner request)

- **No time or trip-length buttons.** The fisher says where, when and for how long. The old "Leaving at" and "Trip length" buttons are hidden (kept in the page only because the map slider and "safer times" still set the departure). The welcome bubble and the "remembered on this phone" line are gone, and no harbour is chosen for the fisher at start.
- **Empty state.** One centred line, "Where are you heading out today?", a short hint and two example questions.
- **One input.** A rounded bar with a round white button with a black waveform (voice). It turns into a send arrow when there is text. While listening it turns red with live bars; while speaking it shows moving bars.
- **The bot asks for what is missing.** Code (not the model) decides what is missing: harbour, departure time, trip length (or a return time). It asks with reviewed templates (`chat.need_*`, kn/ar drafts), remembers what is known across turns, and only checks once the trip is complete. Nothing is assumed any more: no default departure, no default 6 hours. A map tap asks the same questions; the card's Change buttons ask in the chat.
- **Small talk.** Greetings ("hi, I'm Vish, how are you?") get the model's own short reply, using the name, then an invitation to give the trip. The guard still blocks numbers-free safety talk and verdict words; around a check, only templates are shown (model_sentence stays off).
- Checked with the real model on replay data in English, Kannada and Arabic: greeting -> name used; place only -> asks time and length; time given -> asks length; length given -> verdict card.
- The page before this change is in `backup/before-conversation-2026-11-13/`.

## 2c. Voice mode (13 November 2026, owner request)

- The waveform button opens a voice panel (over the chat on a laptop, full screen on a phone): a pearl orb, the transcript above it, and a bar with **Type**, **mute** (red when muted) and **close**. Escape also closes.
- **Hands-free.** It notices when you start and stop speaking, sends the question (ElevenLabs Scribe, then the same chat as typing: code still decides every verdict), reads the reviewed spoken answer (ElevenLabs v4 Turbo) and listens again. The orb swells with her voice and gently with yours. Typed text in voice mode is answered aloud too (`/api/voice/text`).
- **Background noise**: browser noise suppression, echo cancellation and gain control; speech detected in the voice band only (300-3400 Hz); the room level is learnt while nobody speaks and speech must be about 3 times louder; sound must last 0.25 s to count. While she speaks, the microphone is not listened to (no talking over her yet).
- Closing it leaves the whole conversation, with the verdict cards, in the chat.
- Code: `static/voicemode.js`. Checked in the browser with typed questions; live speech could not be tested there (the preview blocks the microphone) and must be tried on a real device. The detection numbers are our own first settings, not tuned on real recordings.
- The page before voice mode is in `backup/before-voice-mode-2026-11-13/`.
- **No dead air** (13 Nov 2026, owner chose it; the idea comes from the Jessa voice agent in `Documents/Voice Assistant`, its opener cache and thinking sounds). As voice mode opens she says "Hi, I'm the Sea Safe assistant. Where are you heading out today?". The moment you stop talking she says "Okay." or "Right." (they take turns, never the same twice running), and "One moment." if the answer is not back after 1.5 s. The answer waits for a line to finish and never cuts one off. These are fixed lines (`say.greeting`, `say.ack.0/1`, `say.wait`; kn/ar drafts), rendered once and served from the cache by `/api/voice/lines`, so they play at once (the greeting took about 0.1 s on reopening). Checked in the browser with a stand-in silent mic and typed turns; not yet heard on a real phone. Backup: `backup/before-voice-lines-2026-11-13/`.
- **Follow-up answers** (13 Nov 2026, from the owner's first real-mic test). The voice now says it too: with one SAFE window, "Leave at 1 in the afternoon, and be back at 5 in the evening." (`say.safest.leave_at` / `leave_by`, kn/ar drafts). When the question is about today and today has one SAFE hour or none, the code also checks tomorrow for the same trip and, if tomorrow has more SAFE hours, adds "Tomorrow: SAFE to leave …" to the chat and "Tomorrow there are more SAFE times: …" to the voice (`chat.b.safest.tomorrow`, `say.safest.tomorrow`; backup `backup/before-suggest-tomorrow-2026-11-13/`). "What time should I leave by?" is now short bullets: the SAFE departure times; with one SAFE window, "Leave at 13:00: back by 17:00." (or "Leave by ... at the latest"); when not to leave; the disclaimer. It shows no verdict badge, because the card is an example trip, not the one planned. "What time do I come back by?" puts "Back by 17:00." first (the voice already says "You'd be back around ..."; if the model picks weather details instead, the voice says "You'll be back ..." first). The model is also told to answer return-time questions with a trip check. New strings `chat.b.safest.*`, `chat.b.leave_at`, `chat.b.leave_by`, `chat.b.back_by`, `say.back_by` (kn/ar drafts). Backup: `backup/before-followup-answers-2026-11-13/`.
- **Talking over her** (13 Nov 2026, owner; layered like the Jessa agent's barge-in). While she speaks the microphone is still measured; speech about 2.2 times louder than ordinary speech detection, for 0.3 s, stops her and is recorded. Under 0.5 s of speech is treated as noise and she carries on. Otherwise the recording goes to `/api/voice/ask` with the line she was saying (`interrupted`): no words, or mostly her own words heard back through the speaker (`voice.is_echo`), and she carries on from a second before where she stopped; real words are a new question. No "Okay." after an interruption. Checked in the browser with a stand-in microphone; not yet on a real phone, where speaker echo is the risk.
- **Questions in the model's words** (13 Nov 2026, owner). When a detail is missing, code decides what to ask and says back what it understood ("Dibba Al-Hisn, got it."); the model only words the question (one short question, no digits, no verdict or safety words, else the reviewed template). `model_questions` in `config/app.yaml`; `chat.got_*` strings (kn/ar drafts).
- Not built yet: spelling out units in code, and a mishear list for harbour names.

## 2d. Full answer in a slide-up sheet (13 November 2026, owner chose option B)

- **The chat never jumps.** No card is drawn in the chat column any more. Every answer is a bullet bubble; its "See the full answer" (in voice mode: "Full answer") opens a sheet that slides up with that bubble's own answer, so older bubbles open their own place, not the latest.
- **Same animations.** The card reveal (colour wash, gauges, hour bars) plays when the sheet opens. Reduced motion: no slide, no reveal.
- **Size.** Phone: the sheet covers about 92% of the screen from the bottom, with a handle and a close button. Laptop: it covers the answer panel and the map stays visible. It sits above voice mode, so closing it goes back to voice mode.
- **Closing.** Close button, tapping the dimmed area, Escape, or "Back to chat" (on the all-harbours card too). Focus goes back to the link that opened it, or to the chat input if that link is gone (region switch).
- **Keyboard and screen readers.** While it is open, what it covers can't be reached with Tab: on a phone the whole page (the sheet is modal); on a laptop only the chat panel, so the map and the time slider still work beside it.
- **No Change buttons** (13 Nov 2026, owner). The "Trip understood" box (harbour, leaving, back, length, and whether the length was the fisher's or assumed) stays, without its Change links: the trip is changed by tapping another harbour, moving the time slider, or saying it in the chat.
- **A map tap answers on the map** (13 Nov 2026, owner). Tapping a harbour, a point at sea, or a harbour in the all-harbours list opens that place's full answer in the sheet for the time on the slider and the trip length the pins use (the fisher's own if the chat knows it; otherwise the standard one, marked as assumed on the card). Nothing is posted in the chat. On a phone the sheet slides up over the map. An assumed length never becomes the chat's trip: the chat still asks. A problem shows in the map's status line.
- **What posts a bubble.** Picking a safer time and the saved offline answer each post a bubble. The time slider, the clock and watch-this-trip never post; with the sheet open they update it quietly.
- **Nothing cut off.** The card can no longer grow wider than the screen (`minmax(0, 1fr)` columns); the details table scrolls in its own box.
- **Server down.** When nothing answers at all, the pins, the chat and safer times say "Can't reach the Sea Safe server. Check that it is running, then try again." (`error.server_down`, kn/ar drafts) instead of "Something went wrong".
- New strings, kn/ar drafts: `ui.full_answer`, `error.server_down`. Checked in the browser at 375 px and 1440 px. The page before this change is in `backup/before-answer-sheet-2026-11-13/`.

## 2a. Features added on 13 November 2026 (from the hackathon audit)

| # | Feature | What it does | Limits, said plainly |
|---|---|---|---|
| 1 | Trip understood | Under the main reason: harbour, leaving, back and length, exactly as checked. The length is tagged "assumed" or "your choice". Harbour, departure and length each have a Change button. | Trips the app cannot check exactly (minutes, overnight return times, over 24 hours) are refused before this point. |
| 2 | Check safer departure times | On CAUTION and UNSAFE cards. Same place, same trip length, every departure hour left in the 48-hour window, using the existing safest-time check. Says plainly when no SAFE time exists, and when not to leave. Up to four SAFE windows can be checked in one tap. | Windows only, never a single "best" hour. |
| 3 | Compact answer | Verdict, main reason and the trip first; then the actions; then the other reasons, gauges and hours. The disclaimer, official-warning links, times and Open-Meteo credit always stay on the card. Listen stays in the verdict bar. | |
| 5 | Watch this trip (lite): REMOVED 13 Nov 2026 by the owner (it only worked while the page stayed open, so a fisher at sea could believe they were watched when they were not) | Live forecasts only. While the page stays open, the trip is checked again every 5 minutes. Only a change of verdict is reported, once, in the conversation and on the card, with the old and new verdict and the time. Stops when the departure time passes or when stopped. | No server, no account, no notification: closing the page stops it. A full version (server rechecks, delivery, expiry) is future work. |
| 6 | Offline | A service worker (`static/sw.js`, served at `/sw.js`) keeps the page, its text, the settings and the map library. The page keeps the last answer with its time. Offline, a bar says so; the last answer is shown with its age in a warning box, but not at all if it is older than 6 hours (the same stale limit the verdict uses). Chat, voice, new checks, safer times and watching are switched off. | Map tiles and spoken audio are not kept. Works only after one online visit, and only on https or localhost. |
| 7 | Share | Only when tapped. Uses the phone's share sheet, else copies the text, else shows it to copy by hand. The text has the place, leaving and back times, length (assumed or chosen), verdict, main reason, replay label, disclaimer, data source and fetch time, and when it was checked. | Never sends anything to anyone by itself. |

Not built, on purpose: **4. official-warning integration** (needs a structured warning feed from IMD/INCOIS/NCM and precedence rules reviewed by a domain expert) and **8. vessel and journey support** (needs expert-reviewed limits per boat type and a validated way to sample weather along a route). Building either without those would show numbers or warnings no one has checked.

The page as it was before these features is in `backup/before-features-2026-11-13/`. New strings (`trip.*`, `ui.change`, `safer.*`, `share.*`, `watch.*`, `offline.*`) are drafts in Kannada and Arabic.

## 3. What is display only

None of these is read by `app/assessment.py`. A test (`tests/test_picture.py`) checks that the verdict code never mentions the wind picture.

| Picture | Where its numbers come from | Our own choices (not sourced) |
|---|---|---|
| Gauges | `explain._gauges`: the worst value, the lines from `config/thresholds.yaml`, and the level from the verdict code's own check | The length of each line: a quarter past the unsafe line. For visibility: four times the caution line |
| Hour bars | `explain._closeness`: the hour's worst value divided by its caution line | Bars stop growing at 1.3 times the line |
| Time slider | `service.region_timeline`: `assess_region` asked once per departure hour | None |
| Wind streaks | `app/windfield.py`: Open-Meteo Forecast API wind on a grid, one call per region | The grid areas and the 0.5° step in `config/app.yaml` (`wind_picture`) |

**Wind streak colours.** The streaks change colour at the three wind lines the verdict uses: amber from 33.3 km/h (the 10% near-line), red from 43 km/h. The wind picture uses grid points, while a verdict uses the wave model's sea cell, so the two can differ slightly. The page says so ("Wind picture only. The answer uses the numbers on the card.") on the wind button and on the "How we decide" panel.

**Replay.** The wind grid of each replay day is saved under `data/replay/` (`wind_*.json`), so replay still works offline.

## 4. Motion rules

- Every animation has a job: show a result arriving, show a value against its line, or show wind.
- Nothing blocks the page. The fisher can tap, type or speak while things move.
- **Reduced motion.** If the phone asks for less motion, nothing slides, grows, pulses or flies. The wind is drawn as still lines.
- **Slow phones.** The wind uses fewer streaks on a small or modest phone, and halves them again if frames get slow.

## 5. The design tokens

All in `static/style.css` under `:root`.

| Group | Tokens |
|---|---|
| Surfaces, darkest first (one neutral gray; only the lightness changes) | `--abyss` #0a0a0b, `--deep` #111113, `--swell` #18181b, `--crest` #222226, `--crest-hi` #2c2c31 |
| Map | `--land` #0b0b0c, `--sea` #1a1b1e (a step lighter, so the sea leads) |
| Text | `--foam` (main), `--mist` (supporting), `--haze` (small print) |
| Pressable and chosen | `--glow`: white |
| Verdict | `--safe`, `--caution`, `--unsafe`, each with a lighter `-lit` for text on dark |
| Replay | `--replay` |
| Corners | `--r-xs` 4px (marks, bars), `--r-s` 8px (inside cards), `--r-m` 14px (cards), `--r-l` 22px (floating panels, chat bubbles), pills for buttons, circles for round buttons. No other values. |

**Type.** Barlow Condensed for the wordmark, headings and the verdict word. Lexend for everything else: it was designed to make reading easier, and its zero has no slash. Noto Sans Kannada and Noto Sans Arabic for those languages.

**Logo.** "Wave S": two waves, one the other turned round, that together read as an S. Black waves on a white tile. The owner chose it on 13 November 2026 from four generated concepts; it was then redrawn by hand as a vector (`static/img/logo.svg`, copy in `brand/sea-safe-mark.svg`). The favicon and phone icons are drawn from that file. The wordmark is Lexend Bold in capitals. The old logo files are in `backup/ui-before-redesign-2026-11-13/` and `brand/`.

**Icons.** One set of line icons (Lucide, ISC licence), written into `static/app.js`. No emoji: they look different on every phone.

## 6. Waiting for the owner

- **New on-screen text**, in all three languages. The Kannada and Arabic are drafts for the native-speaker review: `card.bars_note`, `map.wind_note`, `ui.play`, `ui.pause`, `chat.see_card`, and the two refusal messages `error.time_minutes` and `error.trip_overnight` (13 Nov audit fixes).
- **The wind picture areas** and the 0.5° step in `config/app.yaml`.
- **The map provider** (OpenFreeMap) in place of OpenStreetMap's own tiles.
- **Dark only.** The page has one dark theme, as the owner asked. In direct sun a light theme would be easier to read. Not built.
- **Wind streak colour.** Amber starts at 33.3 km/h (the 10% near-line, which already gives CAUTION on the card), not at 37 km/h, so the streaks never look calm where the card says caution.

## 2e. Settings button and light mode (13 November 2026, owner)

- **Settings button on laptops too.** The round sliders button at the top right, with How we decide always visible just after it (on a phone, as a round "?" button). Pressed, Region, Language and the new Dark/Light switch slide out towards the left from it, nearest first; pressed again, Escape, or a click elsewhere puts them away. On a phone they drop down under the top bar as before.
- **Light mode.** Every colour has a light value (`:root[data-theme="light"]` in `static/style.css`): the panels, cards and chat, the map (light land, cool grey sea, dark labels), the wind streaks (dark instead of light; the near-line and over-line colours are darker so they read on light), and the map's zoom buttons. The verdict colours keep their hue; their text versions are darker.
- **Starts in the phone's own mode.** `index.html` sets the mode before the first paint: the remembered choice, else the phone's or laptop's setting (and it follows that setting until a choice is made here).
- **The switch.** The new mode spreads out in a circle from the button pressed (View Transitions), with the recoloured map in it. Reduced motion: it simply switches. Browsers without View Transitions: the colours fade.
- **The logo** is inverted in light mode (white waves on a dark tile), in the top bar and on the chat's avatar.
- New strings `ui.theme`, `ui.theme_dark`, `ui.theme_light` (kn/ar drafts). The unused replay colours were removed. Backup: `backup/before-theme-2026-11-13/`.

## 2f. Watch this trip, on the server (13 November 2026, owner)

- **What it does.** "Watch this trip" (live forecasts only) asks for notification permission and subscribes the phone (Web Push). The server (`app/watch.py`) checks the trip again every 15 minutes with the same verdict code, until the departure hour, and sends a phone notification only when the verdict changes ("Khor Fakkan: now CAUTION" / "Leaving Fri 13 Nov, 14:00: was SAFE, now CAUTION. Tap for the full answer."). It works with the page closed. The card says a notification can be late and to check the official warnings.
- **Safety and privacy.** Notifications go only to the browsers' push services (`watch.push_hosts`). Stored: the push address and the trip (`data/watch/watches.json`) and the server's signing key (`data/watch/vapid_private.pem`); both git-ignored. A phone that unsubscribes is forgotten.
- **Settings** in `config/app.yaml` (`watch:`). `vapid_subject` is the contact address the push services see (set by the owner).
- **Limits.** iPhone: only when Sea Safe is added to the Home Screen. Checked with tests (real encryption and signing, the network call faked) and in the browser with the browser's permission faked: the preview blocks notifications, so a real notification on a phone has not been seen yet. New dependency: `pywebpush==2.0.3`.
- Replaces the page-open version removed earlier the same day.
- **Emails** (13 Nov 2026, owner). Tapping Watch opens a small form: an email box (optional, the last address filled in, kept on that phone only) and Start watching. With an email, a confirmation is sent when watching starts (the trip, the verdict now, every 15 minutes until departure, how to stop) and each verdict change is emailed as well as notified. A watch can run on email alone (an iPhone without the Home Screen app). If neither notifications nor email can work, the watch is refused with a plain message. The bold line says how the fisher will be told (notification / email / both). Sent through Gmail: `SMTP_USER` and `SMTP_PASSWORD` (an app password) in `.env` (`app/mailer.py`); the address is stored only with the watch and deleted when it ends. Not yet sent for real: needs the app password.
- **Email design** (13 Nov 2026, owner). The watch emails are HTML in Sea Safe's dark look (`app/emails.py`): the logo and wordmark at the top (the logo travels inside the email as `cid:seasafe-logo`), a kicker ("Watching your trip" / "The forecast changed"), the harbour, the verdict as a coloured badge (a change shows the old one struck through, then the new one), the trip in rows, the disclaimer apart, the footer. Plain text stays inside for mail apps without HTML. The sender's round profile picture in Gmail is the sending account's photo: `brand/sea-safe-profile-512.png` is a square logo for a dedicated "Sea Safe" Gmail account.


## 2g. The assistant offers to watch the trip (13 November 2026, owner)

- **The offer.** After a live CAUTION or UNSAFE answer for one harbour, the reply (written and spoken) ends with "Want me to watch this trip and email you if the forecast changes?". Once per trip: the page sends back the trips already offered or watched (`watch_skip`). Never for SAFE answers, replay days or a point tapped on the map.
- **Yes, no, or something else.** The next message is read by code, not the model (`chat.watch_answer`, English, Kannada and Arabic): a short yes, a short no, or an email address. Anything else (a new question, a time, a harbour) goes to the chat as usual and the offer lapses.
- **The email.** On yes the assistant asks for the email. If this phone remembers one from an earlier watch it offers it ("Should I send the updates to you@...? Say yes, or type another email"); the voice does not read the address aloud.
- **Confirmed only once set.** With the email, the server itself starts the watch (`app/watch.py`, email only, rechecked every 15 minutes until departure, any change of verdict emailed: the owner chose every change, because a trip getting worse matters most) and sends the confirmation email. Only if that email was sent does it say "Done. I'm watching this trip until you leave... I've sent you a confirmation email." If it could not be sent, the watch is removed and the fisher is asked to check the address. If email is not set up on the server, it says so and points to the card's Watch button (phone notifications).
- **The page** remembers the watch like one started from the card (button shows Stop watching, the note says email), and the email for next time. New strings `chat.watch_*` / `say.watch_*` are drafts in Kannada and Arabic.
