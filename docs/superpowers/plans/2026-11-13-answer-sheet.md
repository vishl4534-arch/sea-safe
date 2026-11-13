# Full Answer in a Slide-up Sheet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Answers become bullet bubbles in a chat that never jumps; the full card opens in a slide-up sheet from "See the full answer"; nothing in the card is cut off; a clear message when the server is down.

**Architecture:** The card element moves from the scrolling answer column into a new sheet element inside `.panel`. Every answer bubble keeps its own card data and opens the sheet with it. Checks started outside the chat (map tap, safer time, offline saved answer) post a bubble instead of drawing a card. The server adds the bullet text to every card view so the page can post those bubbles.

**Tech Stack:** FastAPI (Python 3.13), vanilla JS (no build), CSS. Tests: pytest. Page checked in the preview browser.

**Spec:** `docs/superpowers/specs/2026-11-13-answer-sheet-design.md`

## Global Constraints
- Keep every animation: sheet slides up; card reveal (wash, gauges, hour bars, boat) plays when the sheet opens. Reduced motion: no sliding, no reveal.
- Phone: sheet covers about 92% of the screen from the bottom, with a handle and a close button. Laptop: sheet covers the answer panel; the map stays visible. The sheet sits above voice mode.
- Close: close button, Escape, "Back to chat"; focus returns to the opener.
- The time slider never posts bubbles.
- All new on-screen text exists in en, kn, ar (kn/ar are drafts); `tests/test_text.py` enforces this.
- No git: the project is not a repository. Instead of commits, copy the touched files to `backup/before-answer-sheet-2026-11-13/` before Task 1.

## Review Focus
- Two answers in the chat: each "See the full answer" opens its own answer, not the latest. (Task 3, browser check 2)
- Sheet open, then the slider moves: the sheet updates quietly; no new bubble. (Task 3, browser check 4)
- Voice mode open, then "Full answer": the sheet shows above voice mode, and closing it returns to voice mode. (Task 3, browser check 5)
- "More details" open on a 375 px phone: nothing is cut off on the right; the table scrolls in its own box. (Task 3, browser check 3)
- Server stopped: pins and chat say the server can't be reached, not "Something went wrong". (Task 2, browser check)

---

### Task 1: Bullets on every card view

**Files:**
- Modify: `app/explain.py` (`render()` return dict)
- Test: `tests/test_bullets.py`

**Interfaces:**
- Produces: `render(res, lang)["bullets"] -> str`, the same text as `bullets(res, lang)`.

- [ ] **Step 1: Write the failing test**

```python
def test_every_card_view_carries_its_bullets():
    res = check(UAE, UAR, "umm_al_quwain", "2025-02-25T16:00", 2)
    assert explain.render(res, "en")["bullets"] == explain.bullets(res, "en")
```

- [ ] **Step 2: Run it:** `.venv/Scripts/python.exe -m pytest tests/test_bullets.py -q`. Expected: FAIL with KeyError 'bullets'.
- [ ] **Step 3: Add `"bullets": bullets(res, lang)` to the `render()` dict.**
- [ ] **Step 4: Run the full suite:** `.venv/Scripts/python.exe -m pytest -q`. Expected: all pass.

### Task 2: "Can't reach the server" message

**Files:**
- Modify: `static/app.js` (`api()`, `refreshPins()`, `assessSelected()`, `sendChat()`), `translations/en.json`, `kn.json`, `ar.json`

**Interfaces:**
- Produces: `api()` throws an `Error` with `.offline = true` when `fetch` itself fails (network or server down); HTTP errors stay as they are.
- Produces: `failText(e) -> string`: `t("error.server_down")` when `e.offline`, else `t("error.generic")`.
- Strings: `error.server_down` en "Can't reach the Sea Safe server. Check that it is running, then try again." (kn, ar drafts).

- [ ] **Step 1: Add the three strings; run `tests/test_text.py`.** Expected: pass.
- [ ] **Step 2: Implement `failText`; use it where `t("error.generic")` is shown after a failed request in the four functions above.** `sendChat` keeps `chat.llm_unavailable` for HTTP errors.
- [ ] **Step 3: Browser check:** stop the server, reload the page (served by the offline helper), and confirm the map status reads the new message.

### Task 3: The sheet

**Files:**
- Modify: `static/index.html` (move `#card` into the new sheet), `static/app.js`, `static/voicemode.js`, `static/style.css`, translations (`ui.full_answer` en "Full answer", `ui.close_sheet` en "Close"; kn, ar drafts)

**Interfaces:**
- Consumes: `view.bullets` (Task 1).
- Produces (app.js): `openSheet(view, opener)`: renders `view` into `#card` with the reveal, slides the sheet up, and remembers `opener` for focus. A view with `groups` (all harbours) renders with the existing region-card markup. `closeSheet()`: hides the sheet and returns focus to the opener. `postAnswer(view, verdict)`: adds a bot bubble whose text is `view.bullets` and whose "See the full answer" opens that `view`.
- Changes: `addMsg(cls, text, verdict, provider, view)`: the last argument is now the card view (or a region view), not a boolean. The bubble's link calls `openSheet(view, link)`.
- `showChatCard(card)` and `showRegionCard(v)` keep updating place, departure, length, context and pins, but no longer draw the card or scroll.
- `assessSelected(quiet)`: quiet (slider, clock tick, watch) with the sheet open re-renders it without the reveal; quiet with the sheet closed only updates `S.view`; not quiet (map tap, safer time) posts a bubble via `postAnswer`, and if the sheet is open also re-renders it with the reveal.
- `showSaved()`: posts a bubble with the saved note line plus the bullets; the sheet shows the saved note when opened.
- `syncWelcome()`: empty state depends on the chat only.
- `toChat()` ("Back to chat"): calls `closeSheet()` then scrolls to the newest message.
- voicemode.js `line()`: for a bot line with a card, adds a "Full answer" link that calls `openSheet(view, link)`.
- Escape closes the sheet first, then voice mode.
- CSS: `.sheet` (absolute in `.panel`, `z-index` above `.vm`, translateY slide with `--ease`, about 92% height on phones, full panel on laptops, backdrop dim); `.card-body { grid-template-columns: minmax(0, 1fr); }` and `.card { min-width: 0; }` so content cannot widen the card.

- [ ] **Step 1: Back up the files:** copy `static/*.js`, `static/*.css`, `static/index.html`, `app/explain.py` and `translations/*.json` to `backup/before-answer-sheet-2026-11-13/`.
- [ ] **Step 2: Implement as above;** run `node --check` on both scripts and `pytest -q`. Expected: no syntax errors, all tests pass.
- [ ] **Step 3: Browser checks (preview, 375 px and 1440 px):**
  1. Ask by chat: a bullet bubble appears, the chat does not scroll up, and no card shows in the column.
  2. Ask twice (UAQ, then Dibba): each "See the full answer" opens its own place.
  3. Open the sheet, open "More details" at 375 px: nothing is cut off on the right.
  4. With the sheet open, drag the slider: the card updates, no new bubble.
  5. In voice mode, a typed question: "Full answer" opens above voice mode; close returns to voice mode.
  6. Map tap with a known trip, and a safer-time pick: each posts a bubble.
  7. Escape and "Back to chat" close the sheet, and focus returns.
- [ ] **Step 4: Update `docs/ui.md`** (one short section) and the memory note.
