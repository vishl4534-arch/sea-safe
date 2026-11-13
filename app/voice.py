"""Voice: ElevenLabs speech-to-text (Scribe) and text-to-speech.

The voice never decides anything. Speech-to-text only turns the fisher's question into text for
the chat; text-to-speech only reads the reviewed spoken templates from app/explain.py, word for word.
Spoken audio is cached by its exact text, so rehearsing the same answer costs no extra credits.
"""
import hashlib
import logging
import os
import re
import threading

import httpx

from app.config import ROOT, load_app
from app.net import CLIENT as _http

log = logging.getLogger("seasafe.voice")

API = "https://api.elevenlabs.io/v1"
AUDIO_DIR = ROOT / "data" / "cache" / "tts"
AUDIO_ID = re.compile(r"^[0-9a-f]{24}$")


class VoiceError(Exception):
    pass


def settings() -> dict:
    return load_app().get("voice", {})


def _key() -> str:
    return os.getenv("ELEVENLABS_API_KEY", "").strip()


def available(lang: str | None = None) -> bool:
    """Voice works only if it is switched on, a key is set, and (if given) the language has a voice."""
    s = settings()
    if not s.get("enabled") or not _key():
        return False
    return lang is None or lang in s.get("languages", {})


def transcribe(audio: bytes, filename: str, content_type: str, lang: str, keyterms: list | None = None) -> str:
    """The question as text. The language is fixed to the one chosen on screen (more accurate than guessing).
    keyterms (harbour names) bias Scribe towards hearing them right: "Dibba" was once heard as "ذبة"."""
    s = settings()
    if not available(lang):
        raise VoiceError("voice not available")
    if not audio:
        return ""
    try:
        r = _http.post(f"{API}/speech-to-text", timeout=s.get("timeout_seconds", 20),
                       headers={"xi-api-key": _key()},
                       data={"model_id": s["stt_model"], "language_code": s["languages"][lang]["stt"],
                             **({"keyterms": keyterms} if keyterms else {})},
                       files={"file": (filename or "question.webm", audio, content_type or "audio/webm")})
    except httpx.HTTPError as e:
        raise VoiceError(f"speech-to-text failed: {e}") from e
    if r.status_code != 200:
        raise VoiceError(f"speech-to-text HTTP {r.status_code}: {r.text[:200]}")
    text = (r.json().get("text") or "").strip()
    log.info("speech-to-text (%s, %s): %d characters", s["stt_model"], lang, len(text))
    return text


BAD_KEYTERM = set("<>{}[]\\")


def is_echo(heard: str, her_line: str) -> bool:
    """Talking over her (13 Nov 2026): was what the microphone heard while she spoke only noise? True when no
    words came through, or when most of them are her own words heard back through the speaker. Then she carries
    on instead of treating it as a new question (the Jessa voice agent's "did any words actually arrive?")."""
    words = re.findall(r"\w+", (heard or "").lower())
    if not words:
        return True
    hers = set(re.findall(r"\w+", (her_line or "").lower()))
    return sum(w in hers for w in words) / len(words) >= 0.6


def harbour_keyterms(region: dict, lang: str) -> list:
    """Harbour names in the screen language and English, plus the local aliases, as Scribe key terms
    (at most 50 characters and 5 words each, no brackets)."""
    from app.explain import t
    terms = []
    for h in region["harbours"]:
        for name in [t(lang, f"place.{h['id']}"), t("en", f"place.{h['id']}"), *h.get("aliases", [])]:
            for part in name.replace("–", ",").split(","):
                part = part.strip()
                if part and len(part) <= 50 and len(part.split()) <= 5 and not BAD_KEYTERM & set(part) \
                        and part not in terms:
                    terms.append(part)
    return terms[:100]


def audio_id(text: str, lang: str) -> str:
    s = settings()
    v = s["languages"][lang]
    raw = "|".join([s["tts_model"], v["voice_id"], s.get("output_format", ""), lang, text])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]


def audio_path(aid: str):
    """The cached file for an audio id, or None. Ids are checked so no other file can be served."""
    if not AUDIO_ID.match(aid or ""):
        return None
    path = AUDIO_DIR / f"{aid}.mp3"
    return path if path.exists() else None


def synthesize(text: str, lang: str) -> str:
    """Speak text in the language's voice; returns an audio id (see audio_path). Cached by exact text."""
    s = settings()
    if not available(lang):
        raise VoiceError("voice not available")
    if not text or len(text) > s.get("max_spoken_chars", 1500):
        raise VoiceError(f"text length {len(text or '')} outside the allowed range")
    aid = audio_id(text, lang)
    if audio_path(aid):
        log.info("text-to-speech (%s): from cache", lang)
        return aid
    v = s["languages"][lang]
    try:
        r = _http.post(f"{API}/text-to-speech/{v['voice_id']}", timeout=s.get("timeout_seconds", 20),
                       params={"output_format": s.get("output_format", "mp3_44100_64")},
                       headers={"xi-api-key": _key(), "Content-Type": "application/json"},
                       json={"text": text, "model_id": s["tts_model"], "language_code": v["tts"]})
    except httpx.HTTPError as e:
        raise VoiceError(f"text-to-speech failed: {e}") from e
    if r.status_code != 200:
        raise VoiceError(f"text-to-speech HTTP {r.status_code}: {r.text[:200]}")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    tmp = AUDIO_DIR / f"{aid}.tmp"
    tmp.write_bytes(r.content)
    os.replace(tmp, AUDIO_DIR / f"{aid}.mp3")
    log.info("text-to-speech (%s, %s, voice %s): %d characters", s["tts_model"], lang, v["voice_name"], len(text))
    return aid


# ---- streaming: the answer starts playing ~1 s after the request instead of 4-8 s --------------------
# The server starts fetching the spoken answer from ElevenLabs as soon as the answer is known, so speech is
# already arriving while the page is still receiving the written answer. The page then plays it as it streams.
_pending: dict = {}          # audio id -> (text, lang), not fetched yet
_fetches: dict = {}          # audio id -> _Fetch, being fetched now
MAX_PENDING = 200


def warm_url() -> str:
    return f"{API}/models"


def prepare(text: str, lang: str, start: bool = True) -> str:
    """Register text to be spoken and return its audio id at once. With start=True the fetch from
    ElevenLabs begins now in the background; /api/voice/audio/<id> streams it as it arrives."""
    s = settings()
    if not available(lang):
        raise VoiceError("voice not available")
    if not text or len(text) > s.get("max_spoken_chars", 1500):
        raise VoiceError(f"text length {len(text or '')} outside the allowed range")
    aid = audio_id(text, lang)
    if not audio_path(aid):
        _pending[aid] = (text, lang)
        while len(_pending) > MAX_PENDING:
            _pending.pop(next(iter(_pending)))
        if start and aid not in _fetches:
            _Fetch(aid, text, lang).start()
    return aid


class _Fetch:
    """One spoken answer coming from ElevenLabs in a background thread. Any number of readers get the
    chunks as they arrive; the complete file is saved to the cache at the end."""

    def __init__(self, aid: str, text: str, lang: str):
        self.aid, self.text, self.lang = aid, text, lang
        self.chunks, self.done, self.error = [], False, None
        self.cv = threading.Condition()

    def start(self) -> "_Fetch":
        _fetches[self.aid] = self                       # registered before the thread can finish
        threading.Thread(target=self._run, args=(self.aid, self.text, self.lang), daemon=True).start()
        return self

    def _run(self, aid, text, lang):
        s = settings()
        v = s["languages"][lang]
        try:
            with _http.stream("POST", f"{API}/text-to-speech/{v['voice_id']}/stream", timeout=s.get("timeout_seconds", 20),
                              params={"output_format": s.get("output_format", "mp3_44100_64")},
                              headers={"xi-api-key": _key(), "Content-Type": "application/json"},
                              json={"text": text, "model_id": s["tts_model"], "language_code": v["tts"]}) as r:
                if r.status_code != 200:
                    raise VoiceError(f"text-to-speech HTTP {r.status_code}: {r.read()[:200]!r}")
                log.info("text-to-speech stream (%s, %s, voice %s): %d characters",
                         s["tts_model"], lang, v["voice_name"], len(text))
                for chunk in r.iter_bytes():
                    with self.cv:
                        self.chunks.append(chunk)
                        self.cv.notify_all()
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            part = AUDIO_DIR / f"{aid}.{os.getpid()}.{id(self)}.part"
            part.write_bytes(b"".join(self.chunks))
            os.replace(part, AUDIO_DIR / f"{aid}.mp3")
            _pending.pop(aid, None)
        except Exception as e:                          # noqa: BLE001 - any failure becomes a clean voice error
            self.error = e if isinstance(e, VoiceError) else VoiceError(f"text-to-speech failed: {e}")
            log.warning("%s", self.error)
        finally:
            with self.cv:
                self.done = True
                self.cv.notify_all()
            if _fetches.get(aid) is self:
                _fetches.pop(aid)

    def wait_first(self) -> None:
        """Wait for the first audio; raise VoiceError (before anything is sent) if there is none."""
        with self.cv:
            self.cv.wait_for(lambda: self.chunks or self.done)
        if not self.chunks:
            raise self.error or VoiceError("text-to-speech returned no audio")

    def read(self):
        i = 0
        while True:
            with self.cv:
                self.cv.wait_for(lambda: i < len(self.chunks) or self.done)
                if i >= len(self.chunks):
                    return
                chunk = self.chunks[i]
            i += 1
            yield chunk


def open_stream(aid: str):
    """Stream a prepared answer: join the fetch already running, or start it now. Raises VoiceError
    before any audio is sent if ElevenLabs refuses, so the page gets a clean error."""
    fetch = _fetches.get(aid)
    if fetch is None:
        if aid not in _pending:
            raise VoiceError("unknown audio id")
        fetch = _Fetch(aid, *_pending[aid]).start()
    fetch.wait_first()
    return fetch.read()


def check() -> None:
    """`python -m app.voice`: confirm the key works, the models exist and every configured voice speaks."""
    from dotenv import load_dotenv
    load_dotenv()
    s = settings()
    if not _key():
        print("ELEVENLABS_API_KEY is not set in .env")
        return
    h = {"xi-api-key": _key()}
    sub = httpx.get(f"{API}/user/subscription", headers=h, timeout=20)
    if sub.status_code == 200:
        j = sub.json()
        print(f"plan: {j.get('tier')}  credits used {j.get('character_count')} of {j.get('character_limit')}")
    else:
        print("subscription check:", sub.status_code, sub.text[:200])
    models = httpx.get(f"{API}/models", headers=h, timeout=20)
    if models.status_code == 200:
        tts = {m["model_id"]: [x["language_id"] for x in m.get("languages", [])]
               for m in models.json() if m.get("can_do_text_to_speech")}
        langs = tts.get(s["tts_model"])
        print(f"text-to-speech model {s['tts_model']}: {'found' if langs is not None else 'NOT FOUND'}",
              "" if langs is None else {lg: lg in langs for lg in ("en", "kn", "ar")})
    for lang, v in s.get("languages", {}).items():
        try:
            aid = synthesize({"en": "Sea Safe voice check.", "kn": "ಸೀ ಸೇಫ್ ಧ್ವನಿ ಪರಿಶೀಲನೆ.",
                              "ar": "اختبار صوت سي سيف."}.get(lang, "Sea Safe."), lang)
            print(f"voice {lang} ({v['voice_name']}): OK -> data/cache/tts/{aid}.mp3")
        except VoiceError as e:
            print(f"voice {lang} ({v['voice_name']}): FAILED {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check()
