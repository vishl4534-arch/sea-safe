"""FastAPI app: JSON routes for the page, plus the static page itself."""
import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from typing import Literal

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from app import chat as chat_mod, explain, llm, net, service, voice, watch  # noqa: E402  (after .env is loaded)
from app.assessment import _near  # noqa: E402
from app.config import ROOT, load_app, load_thresholds, load_translations  # noqa: E402

@asynccontextmanager
async def _lifespan(_app):
    net.warm(_warm_urls())          # connections to the model and ElevenLabs are open before the first question
    if load_app()["watch"].get("enabled", True):
        watch.start()               # watched trips are checked again every few minutes (13 Nov 2026)
    yield


app = FastAPI(title="Sea Safe", lifespan=_lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    """The offline helper. Served from the site root so it may look after the whole page (feature 6)."""
    return FileResponse(ROOT / "static" / "sw.js", media_type="text/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(ROOT / "static" / "img" / "favicon-32.png", media_type="image/png")


@app.get("/api/config")
def config():
    cfg = load_app()
    th = load_thresholds()
    wind = th["parameters"]["wind_speed"]
    return {
        "languages": cfg["languages"],
        "map_style": cfg.get("map_style"),
        # Where the wind streaks change colour: the same three lines the verdict uses for wind.
        "wind_picture": {"enabled": bool((cfg.get("wind_picture") or {}).get("enabled")),
                         "near": _near(wind["caution"]["value"], 1 - th["near_line_margin"]),
                         "caution": wind["caution"]["value"], "unsafe": wind["unsafe"]["value"]},
        "trip": cfg["trip"],
        "forecast": {"window_hours": cfg["forecast"]["window_hours"],
                     "stale_after_hours": cfg["forecast"]["stale_after_hours"]},
        "llm_providers": llm.provider_order(),
        "regions": [{"id": r["id"], "languages": r["languages"], "map": r["map"], "timezone": r["timezone"],
                     "official_warnings": r["official_warnings"],
                     "harbours": [{"id": h["id"], "lat": h["lat"], "lon": h["lon"]} for h in r["harbours"]],
                     "replays": [{"id": x, **cfg["replays"][x]} for x in r["replay"]]}
                    for r in cfg["regions"].values()],
    }


@app.get("/api/translations/{lang}")
def translations(lang: str):
    if lang not in load_app()["languages"]:
        raise HTTPException(404, "language not enabled")
    return load_translations(lang)


@app.get("/api/clock")
def clock(region: str, mode: str = "live"):
    return _safe(lambda: service.clock_info(region, mode))


@app.get("/api/how")
def how(lang: str = "en"):
    return explain.how_we_decide(explain.pick_lang(lang))


class AssessIn(BaseModel):
    region: str
    place: str
    departure_local: str
    trip_hours: int
    trip_length_given_by_user: bool
    mode: str = "live"
    map_point: list[float] | None = None
    lang: str = "en"


# ---- watch this trip, on the server (13 Nov 2026): Web Push when the verdict changes ----------------------
class WatchIn(BaseModel):
    subscription: dict
    region: str
    place: str
    departure_local: str
    trip_hours: int = Field(ge=1, le=168)
    trip_length_given_by_user: bool = False
    lang: str = "en"
    map_point: list[float] | None = Field(default=None, min_length=2, max_length=2)


class WatchStopIn(BaseModel):
    id: str = Field(min_length=1, max_length=40)


@app.get("/api/push/key")
def push_key():
    """The server's public push key, for the browser's subscription."""
    try:
        return {"ok": True, "key": watch.public_key()}
    except Exception as e:          # the push library is missing or the key cannot be made
        logging.getLogger("seasafe.watch").warning("no push key: %s", e)
        return {"ok": False}


@app.post("/api/watch")
def watch_start(body: WatchIn):
    """Start watching a trip (live forecasts only). The verdict now is the one later checks compare against."""
    sub = body.subscription
    if not watch.allowed_endpoint(sub.get("endpoint", "")) or not isinstance(sub.get("keys"), dict):
        raise HTTPException(422, "not a browser push subscription")
    lang = explain.pick_lang(body.lang, body.region)
    res = _safe(lambda: service.assess_trip(body.region, body.place, body.departure_local, body.trip_hours,
                                            body.trip_length_given_by_user, "live", body.map_point))
    if not res.get("ok"):
        return {"ok": False, "message": explain.error_text(res, lang)}
    trip = {"region": body.region, "place": body.place, "departure_local": body.departure_local,
            "trip_hours": body.trip_hours, "trip_length_given_by_user": body.trip_length_given_by_user,
            "lang": lang, "map_point": body.map_point}
    wid = watch.add({"endpoint": sub["endpoint"], "keys": sub["keys"]}, trip, res["verdict"])
    return {"ok": True, "id": wid, "verdict": res["verdict"]}


@app.post("/api/watch/stop")
def watch_stop(body: WatchStopIn):
    watch.remove(body.id)
    return {"ok": True}


@app.post("/api/assess")
def assess(body: AssessIn):
    res = _safe(lambda: service.assess_trip(body.region, body.place, body.departure_local, body.trip_hours,
                                            body.trip_length_given_by_user, body.mode, body.map_point))
    lang = explain.pick_lang(body.lang, body.region)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error"), "message": explain.error_text(res, lang)}
    return {"ok": True, "result": res, "view": explain.render(res, lang)}


class SafestIn(BaseModel):
    region: str
    place: str
    search_from_local: str
    search_to_local: str
    trip_hours: int
    trip_length_given_by_user: bool
    mode: str = "live"
    map_point: list[float] | None = None
    lang: str = "en"


@app.post("/api/safest")
def safest(body: SafestIn):
    """'When is the safest time': departure windows, never a single best hour. For the voice agent."""
    res = _safe(lambda: service.find_safest_time(body.region, body.place, body.search_from_local, body.search_to_local,
                                                 body.trip_hours, body.trip_length_given_by_user, body.mode,
                                                 body.map_point))
    lang = explain.pick_lang(body.lang, body.region)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error"), "message": explain.error_text(res, lang)}
    return {"ok": True, "result": res, "line": explain.safest_line(res, lang),
            "view": explain.render(res["shown"], lang)}


class RegionIn(BaseModel):
    region: str
    departure_local: str
    trip_hours: int
    mode: str = "live"


@app.post("/api/assess_region")
def assess_region(body: RegionIn):
    res = _safe(lambda: service.assess_region(body.region, body.departure_local, body.trip_hours, body.mode))
    if not res.get("ok"):
        return res
    return {"ok": True, "harbours": {k: {"verdict": v["verdict"], "sea_cell_km": v["place"]["sea_cell_km"]}
                                     for k, v in res["harbours"].items()}}


class TimelineIn(BaseModel):
    region: str
    trip_hours: int
    mode: str = "live"


@app.post("/api/timeline")
def timeline(body: TimelineIn):
    """Verdict per harbour for every departure hour in the window: the time slider on the map."""
    return _safe(lambda: service.region_timeline(body.region, body.trip_hours, body.mode))


@app.get("/api/wind")
def wind(region: str, mode: str = "live"):
    """Wind on a grid for the moving streaks on the map. A picture only, never part of a verdict."""
    return _safe(lambda: service.wind_picture(region, mode))


# What the page may send about the conversation. Checked here, so a bad or oversized request is refused
# before any model is called (audit 13 Nov 2026, item 3). The page sends at most 12 turns back anyway.
class Turn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class Context(BaseModel):
    """The previous check, exactly as /api/chat returned it."""
    model_config = ConfigDict(extra="forbid")
    place: str | None = Field(default=None, max_length=64)
    departure: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:00$")
    trip_hours: int | None = Field(default=None, ge=1, le=24)
    given: bool | None = None


History = TypeAdapter(list[Turn])
MAX_TURNS = 40


def _history(items) -> list[dict]:
    turns = History.validate_python(items)
    if len(turns) > MAX_TURNS:
        raise ValueError(f"at most {MAX_TURNS} turns")
    return [t.model_dump() for t in turns]


def _context(item) -> dict | None:
    return None if item is None else Context.model_validate(item).model_dump(exclude_none=True)


class ChatIn(BaseModel):
    history: list[Turn] = Field(max_length=MAX_TURNS)
    lang: str = "en"
    region: str
    mode: str = "live"
    map_point: list[float] | None = Field(default=None, min_length=2, max_length=2)
    context: Context | None = None
    page: dict | None = None          # what is selected on screen; checked in chat._clean_page


@app.post("/api/chat")
def chat(body: ChatIn):
    history = [t.model_dump() for t in body.history]
    context = body.context.model_dump(exclude_none=True) if body.context else None
    return _safe(lambda: chat_mod.chat(history, body.lang, body.region, body.mode, body.map_point, context or None,
                                       body.page))


# ---------------------------------------------------------------- voice
@app.get("/api/voice/status")
def voice_status():
    s = voice.settings()
    return {"available": voice.available(), "max_record_seconds": s.get("max_record_seconds", 20),
            "languages": [lang for lang in s.get("languages", {}) if voice.available(lang)]}


def _speak(text: str, lang: str):
    """(audio_url, error message). The audio is streamed when the page plays the url.
    A voice failure never hides the written answer."""
    try:
        return f"/api/voice/audio/{voice.prepare(text, lang)}", None
    except voice.VoiceError as e:
        logging.getLogger("seasafe.voice").warning("%s", e)
        return None, explain.t(lang, "voice.unavailable")


def _warm_urls() -> list[str]:
    return llm.warm_urls() + ([voice.warm_url()] if voice.available() else [])


@app.post("/api/voice/warm")
def voice_warm():
    """Called when the mic is pressed: connections to ElevenLabs and the model are opened while the
    fisher is still speaking, so the answer does not wait for them (about 0.5 s each)."""
    net.warm(_warm_urls())
    return {"ok": True}


VOICE_LINES = {"greeting": "say.greeting", "acks": ["say.ack.0", "say.ack.1"], "wait": "say.wait"}


@app.get("/api/voice/lines")
def voice_lines(lang: str = "en"):
    """Short lines she says without waiting for an answer (13 Nov 2026, owner's choice; the idea comes from
    the Jessa voice agent): the greeting when voice mode opens, "Okay." / "Right." the instant the fisher
    stops talking, and "One moment." if the answer takes longer. Fixed reviewed text, so each is rendered
    once and then served from the cache; asking here starts the render, so they are ready when needed."""
    if not voice.available(lang):
        return {"ok": False}

    def one(key):
        text = explain.t(lang, key)
        url, _ = _speak(text, lang)
        return {"text": text, "url": url}

    out = {"greeting": one(VOICE_LINES["greeting"]), "acks": [one(k) for k in VOICE_LINES["acks"]],
           "wait": one(VOICE_LINES["wait"])}
    if not all(x["url"] for x in [out["greeting"], out["wait"], *out["acks"]]):
        return {"ok": False}
    return {"ok": True, **out}


@app.post("/api/voice/ask")
async def voice_ask(audio: UploadFile = File(...), region: str = Form(...), lang: str = Form("en"),
                    mode: str = Form("live"), history: str = Form("[]"), context: str = Form("null"),
                    map_point: str = Form("null"), page: str = Form("null"), interrupted: str = Form("")):
    """Spoken question in, spoken answer out: speech-to-text -> the same chat as typing -> reviewed
    spoken templates -> text-to-speech. The model never writes what is spoken.
    interrupted: the line she was saying when the fisher talked over her (13 Nov 2026). If no words came
    through, or only her own words heard back, it was noise: {"resume": true} and she carries on."""
    lang = explain.pick_lang(lang, region) if region in load_app()["regions"] else lang
    if not voice.available(lang):
        return {"ok": False, "message": explain.t(lang, "voice.unavailable")}
    try:                                # the same checks as /api/chat, before any paid speech-to-text
        past = _history(_json(history, []))
        ctx = _context(_json(context, None)) or None
    except (ValidationError, ValueError) as e:
        raise HTTPException(422, f"bad history or context: {e}")
    data = await audio.read()
    try:
        region_cfg = load_app()["regions"].get(region)
        terms = voice.harbour_keyterms(region_cfg, lang) if region_cfg else None
        question = await run_in_threadpool(voice.transcribe, data, audio.filename, audio.content_type, lang, terms)
    except voice.VoiceError as e:
        logging.getLogger("seasafe.voice").warning("%s", e)
        return {"ok": False, "message": explain.t(lang, "voice.unavailable")}
    if interrupted and voice.is_echo(question, interrupted):
        return {"ok": True, "resume": True}
    if not question:
        said = explain.t(lang, "say.not_heard")
        url, err = _speak(said, lang)
        return {"ok": True, "transcript": "", "reply": said, "spoken": said, "audio_url": url,
                "voice_error": err, "cards": [], "context": ctx, "provider": None}
    res = await run_in_threadpool(_safe, lambda: chat_mod.chat(
        past + [{"role": "user", "content": question}], lang, region, mode,
        _json(map_point, None), ctx, _json(page, None)))
    url, err = _speak(res["spoken"], lang)
    return {"ok": True, "transcript": question, **res, "audio_url": url, "voice_error": err}


class VoiceTextIn(BaseModel):
    """A question typed inside voice mode: answered by the same chat, and read aloud."""
    question: str = Field(min_length=1, max_length=1000)
    region: str
    lang: str = "en"
    mode: str = "live"
    history: list[Turn] = Field(default_factory=list, max_length=MAX_TURNS)
    context: Context | None = None
    map_point: list[float] | None = Field(default=None, min_length=2, max_length=2)
    page: dict | None = None


@app.post("/api/voice/text")
def voice_text(body: VoiceTextIn):
    """Voice mode, typed: the same chat as /api/chat, then the reviewed spoken text read aloud (13 Nov 2026)."""
    lang = explain.pick_lang(body.lang, body.region) if body.region in load_app()["regions"] else body.lang
    if not voice.available(lang):
        return {"ok": False, "message": explain.t(lang, "voice.unavailable")}
    past = [t.model_dump() for t in body.history]
    ctx = body.context.model_dump(exclude_none=True) if body.context else None
    res = _safe(lambda: chat_mod.chat(past + [{"role": "user", "content": body.question}], lang, body.region,
                                      body.mode, body.map_point, ctx or None, body.page))
    url, err = _speak(res["spoken"], lang)
    return {"ok": True, "transcript": body.question, **res, "audio_url": url, "voice_error": err}


@app.post("/api/voice/say")
def voice_say(body: AssessIn):
    """Read the current card aloud ("Listen" button). The answer is computed again here, never taken
    from the page, so only code-made verdicts and reviewed templates are spoken."""
    lang = explain.pick_lang(body.lang, body.region)
    res = _safe(lambda: service.assess_trip(body.region, body.place, body.departure_local, body.trip_hours,
                                            body.trip_length_given_by_user, body.mode, body.map_point))
    said = explain.spoken(res, lang) if res.get("ok") else explain.error_text(res, lang)
    url, err = _speak(said, lang)
    return {"ok": url is not None, "spoken": said, "audio_url": url, "message": err}


@app.get("/api/voice/audio/{aid}")
def voice_audio(aid: str):
    """A cached answer is served from disk; a new one is streamed from ElevenLabs as it is made."""
    path = voice.audio_path(aid)
    if path:
        return FileResponse(path, media_type="audio/mpeg")
    if not voice.AUDIO_ID.match(aid):
        raise HTTPException(404, "no such audio")
    try:
        return StreamingResponse(voice.open_stream(aid), media_type="audio/mpeg")
    except voice.VoiceError as e:
        logging.getLogger("seasafe.voice").warning("%s", e)
        raise HTTPException(404 if "unknown" in str(e) else 502, "voice not available")


def _json(raw: str, default):
    try:
        return json.loads(raw) if raw else default
    except ValueError:
        return default


def _safe(fn):
    try:
        return fn()
    except ValueError as e:
        raise HTTPException(400, str(e))
