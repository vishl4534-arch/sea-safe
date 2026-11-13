# Full answer in a slide-up sheet (design, 13 Nov 2026)

## Why
While chatting or talking to the voice agent, each new answer redrew the big card above the chat and (on a phone) scrolled up to it, which broke the flow. Opening "More details" also pushed the card off the right edge.

## Goals
- The conversation never jumps: a new answer is a bullet bubble at the bottom of the chat, nothing else moves.
- The full answer (verdict bar, trip understood, safer times, share, watch, gauges, hour bars, small print, details table) opens in a sheet that slides up over the chat from "See the full answer", and closes back to the same place in the chat.
- Keep every animation: the sheet slides up; the card's reveal (colour wash, gauges sliding, hour bars growing, boat sailing) plays when the sheet opens.
- Nothing in the card is cut off at any width, including with "More details" open.

## Non-goals
- No change to what an answer says, the verdict, or the bullets.
- No change to voice mode beyond letting its answers open the same sheet.

## Approaches (owner picked B)
- A. Card inside each chat bubble, expanding in place: one thread, but long answers make it long.
- **B. Slide-up sheet (picked):** clean thread; one tap to see the full answer; no jumping.
- C. Keep the card above the chat, just stop scrolling to it: smallest, but answers still appear far from where the fisher reads.

## Design
- The card moves out of the scrolling column into a sheet inside the answer panel: on a phone it covers the screen from the bottom (with a handle and a close button); on a laptop it covers the answer panel, so the map stays visible. It opens above voice mode too.
- Opens from: "See the full answer" in any answer bubble (chat or voice transcript). Each bubble opens its own answer.
- Closes with the close button, the Escape key, or "Back to chat" at the bottom of the card; focus returns to the link that opened it.
- A tapped harbour (with a known trip), a picked safer time, and offline saved answers post a bubble with the bullets (the server adds `bullets` to every card view) instead of drawing a card; the sheet stays closed until asked.
- Moving the map's time slider updates the answer quietly if the sheet is open; it never posts bubbles.
- "Which harbours are safe" answers open in the same sheet.
- Reduced motion: the sheet appears without sliding; the reveal does not play.
- Layout fix: the card's content column may shrink below its widest child (`minmax(0, 1fr)`), so the details table scrolls inside its own box.

## Left to the builder
- Exact sheet height on a phone (about 92% of the screen), duration and easing (same easing as the rest of the page).
