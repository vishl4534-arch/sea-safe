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

## Groq vs Gemini, 13 November 2026 (afternoon)

**Why:** the owner asked which is better for the chatbot and the voice agent: Groq `openai/gpt-oss-120b` (reasoning low, first today) or Gemini `gemini-3.5-flash-lite` (fallback today).

**Method.** 5 conversations, 34 turns (English 16, Kannada 8, Arabic 10), replay weather, through `app/chat.py`, each provider ALONE (no fallback, no early second call, 20 s limit so the true time shows). Run twice, Groq first then Gemini first, so 68 turns each. Scored: the right tool with the right place, day, hour and length; small talk with no tool, in the right language, passing the word guard. Small sample.

| | Groq gpt-oss-120b | Gemini 3.5 flash-lite |
|---|---|---|
| Turns right | 66 / 68 | **68 / 68** |
| Misses | Kannada "ಯಾಕೆ?" (why?) both times: explained the app instead of checking again | none |
| Model time, median | **0.52 s** | 0.89 s |
| 90% of turns under | 1.46 s | 1.40 s |
| Slowest | 5.02 s (would have gone to the fallback) | **1.79 s** |
| Over 1.5 s | 6 | 4 |

**Voice.** Speech-to-text (~0.6 s) and the first sound of the answer (~0.9 s) are the same for both. A voice turn is about 2.0 s with Groq and 2.4 s with Gemini (median); "One moment." starts at 1.5 s, so it plays more often with Gemini.

**Small talk.** Both warm, right language, used the fisher's name. Gemini's Arabic was richer; it once misspelt Kannada "ಪರವಾಗಿಲ್ಲ" and once did not ask which harbour after "Muscat". Groq answered Kannada "thank you" with "ನಮಸ್ಕಾರ!".

**Decision (owner, 13 Nov 2026): Gemini first, Groq as the fallback** (`LLM_PROVIDERS=gemini,groq`).
