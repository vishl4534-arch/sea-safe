# Groq model comparison, 13 November 2026

Why: the owner's test chat went badly ("what's your name" was dodged; "around 4:10, 2-3 hours, back by 6-6:30" was refused). Before switching models, the two causes were fixed in the app (both were app rules, not the model), then two Groq models were compared.

**Method.** The same 10 conversations (22 turns) in English, Kannada and Arabic, on saved replay weather, through `app/chat.py`, with Groq only (Gemini fallback switched off, so each model is judged on its own). Script and raw results were kept outside the project. Small sample; this is a sanity check, not a benchmark.

Models available on the account on 13 Nov: `openai/gpt-oss-120b` (in use), `openai/gpt-oss-20b`, `qwen/qwen3.6-27b`, `qwen/qwen3.8-27b`. The comparison used the current model and the newest alternative.

| | gpt-oss-120b (reasoning low) | qwen3.8-27b (reasoning none) |
|---|---|---|
| Turns handled correctly | **22 / 22** | 13 / 22 |
| Invalid tool calls (Groq refused them) | 0 | 7 (missing `place` or `day`, text where a number or true/false was needed) |
| Owner's chat, turn 3 (approximate times) | Checked 16:00 to 19:00, said so | Wrote its own sentence, no check |
| Greetings, with name (en, kn, ar) | Yes | Yes |
| Typical time per turn | 0.4-1 s (one Kannada turn 2 s) | 0.5-1 s |

**Decision: keep `openai/gpt-oss-120b`.** Gemini (`gemini-3.5-flash-lite`) stays as the automatic fallback.

What changed in the app the same morning:
- Approximate times are covered instead of refused: a departure with minutes starts at its hour, a return with minutes ends at the next hour, a range uses the longest length and the latest return; the reply says which hours were checked ("chat.covered"). This only ever checks more hours, never fewer.
- The bot can say its name ("the Sea Safe assistant"); the guard no longer treats the app's name as a verdict word.
