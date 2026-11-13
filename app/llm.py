"""Language-model client. Gemini first, Groq as automatic fallback (order set in .env; Gemini first since
13 Nov 2026: it handled 68/68 test turns against Groq's 66, see docs/model-comparison-2026-11-13.md).
Both are called through their OpenAI-compatible chat-completions endpoints, so there
is one code path. Order, model names and keys come from .env."""
import json
import logging
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from app import net

log = logging.getLogger("seasafe.llm")

PROVIDERS = {
    "groq": {"base_url": "https://api.groq.com/openai/v1/", "key_env": "GROQ_API_KEY",
             "model_env": "GROQ_MODEL", "default_model": "openai/gpt-oss-120b", "effort_env": "GROQ_REASONING_EFFORT"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "key_env": "GEMINI_API_KEY",
               "model_env": "GEMINI_MODEL", "default_model": "gemini-3.5-flash-lite", "effort_env": "GEMINI_REASONING_EFFORT"},
}


class LLMUnavailable(Exception):
    pass


def provider_order() -> list[str]:
    return [p.strip() for p in os.getenv("LLM_PROVIDERS", "gemini,groq").split(",") if p.strip() in PROVIDERS]


def call_timeout() -> float:
    """Seconds to wait for one model call before trying the next provider (LLM_TIMEOUT_SECONDS in .env)."""
    try:
        return float(os.getenv("LLM_TIMEOUT_SECONDS", "4"))
    except ValueError:
        return 4.0


def hedge_seconds() -> float:
    """If the first provider has not answered after this long, ask the next one too (LLM_HEDGE_SECONDS)."""
    try:
        return float(os.getenv("LLM_HEDGE_SECONDS", "1.5"))
    except ValueError:
        return 1.5


_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="llm")


def _fits(value, spec: dict) -> bool:
    """One argument against its schema entry: type, enum and bounds. bool is not accepted as an integer."""
    kind = spec.get("type")
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        return spec.get("minimum", value) <= value <= spec.get("maximum", value)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "string":
        return isinstance(value, str) and ("enum" not in spec or value in spec["enum"])
    return False


def call_problem(call: dict, tools: list[dict]) -> str | None:
    """Why a tool call does not match the tool it names (None if it does): a known tool, arguments that are
    a JSON object, every required field, no extra field, and each value of the right type, enum and range.
    Checked before anything runs (audit 13 Nov 2026, item 3)."""
    try:
        name, raw = call["function"]["name"], call["function"].get("arguments")
    except (KeyError, TypeError, AttributeError):
        return "no function name"
    schema = next((t["function"]["parameters"] for t in tools if t["function"]["name"] == name), None)
    if schema is None:
        return f"unknown tool {name!r}"
    try:
        args = json.loads(raw or "{}") if isinstance(raw, str) else raw
    except ValueError:
        return "arguments are not JSON"
    if not isinstance(args, dict):
        return "arguments are not an object"
    props, required = schema.get("properties", {}), schema.get("required", [])
    missing = [k for k in required if k not in args]
    if missing:
        return f"missing {missing}"
    extra = [k for k in args if k not in props]
    if extra:
        return f"unexpected {extra}"
    bad = [k for k, v in args.items() if not _fits(v, props[k])]
    if bad:
        return f"bad value for {bad}"
    return None


def _valid(message: dict, tools: list[dict] | None = None) -> bool:
    """A tool call that does not match its tool counts as a failure, so we fall back to the next provider."""
    for call in message.get("tool_calls") or []:
        problem = call_problem(call, tools or [])
        if problem:
            log.warning("tool call refused: %s", problem)
            return False
    return bool(message.get("tool_calls")) or bool((message.get("content") or "").strip())


def _clean(messages: list[dict], provider: str) -> list[dict]:
    """Keep only standard fields, so a turn that started on one provider can finish on another.
    Gemini's tool calls carry an extra 'thought signature' that Gemini needs back; others may reject it."""
    out = []
    for m in messages:
        c = {k: m[k] for k in ("role", "content", "tool_call_id", "name") if k in m}
        if m.get("tool_calls"):
            c["tool_calls"] = [{k: tc[k] for k in ("id", "type", "function", "extra_content")
                                if k in tc and (k != "extra_content" or provider == "gemini")}
                               for tc in m["tool_calls"]]
        out.append(c)
    return out


def _post(url: str, **kw):
    return net.CLIENT.post(url, **kw)


def _ask(name: str, messages: list[dict], tools: list[dict]) -> tuple[dict, str]:
    """One call to one provider. Returns (assistant message, "provider (model)") or raises."""
    p = PROVIDERS[name]
    key = os.getenv(p["key_env"], "").strip()
    model = os.getenv(p["model_env"], "").strip() or p["default_model"]
    body = {"model": model, "messages": _clean(messages, name), "tools": tools,
            "tool_choice": "auto", "temperature": 0}
    effort = os.getenv(p["effort_env"], "").strip()
    if effort:
        body["reasoning_effort"] = effort
    r = _post(p["base_url"] + "chat/completions", timeout=call_timeout(),
              headers={"Authorization": f"Bearer {key}"}, json=body)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    message = r.json()["choices"][0]["message"]
    if not _valid(message, tools):
        raise RuntimeError("empty reply or a tool call that does not match its tool")
    for i, call in enumerate(message.get("tool_calls") or []):
        call.setdefault("id", f"call_{i}")
        call.setdefault("type", "function")
    return message, f"{name} ({model})"


def warm_urls() -> list[str]:
    """The providers that have a key, for net.warm()."""
    return [PROVIDERS[n]["base_url"] for n in provider_order() if os.getenv(PROVIDERS[n]["key_env"], "").strip()]


def complete(messages: list[dict], tools: list[dict]) -> tuple[dict, str]:
    """Returns (assistant message, "provider (model)").

    - Each provider gets at most call_timeout() seconds IN TOTAL (a hard cap, measured by the clock here;
      httpx's own timeout only limits each network step, and Groq once took 9-11 s through it).
      A provider that runs out of time is left behind and the next one is asked.
    - If the first provider has not answered after hedge_seconds(), the next one is asked as well and the
      first good answer is used. Groq answers in ~0.5 s, so this only costs a second call when it stalls.
    - An error (HTTP error, 429, malformed tool call) moves to the next provider at once."""
    names, errors, running = provider_order(), [], {}      # running: future -> (provider, start time)
    queue = list(names)

    def start_next() -> bool:
        while queue:
            name = queue.pop(0)
            if not os.getenv(PROVIDERS[name]["key_env"], "").strip():
                errors.append(f"{name}: no key")
                continue
            running[_POOL.submit(_ask, name, messages, tools)] = (name, time.monotonic())
            return True
        return False

    cap, hedge = call_timeout(), hedge_seconds()
    start_next()
    while running:
        newest = max(t for _, t in running.values())
        wake = min([t + cap for _, t in running.values()] + ([newest + hedge] if queue else []))
        done, _ = wait(running, timeout=max(0.0, wake - time.monotonic()), return_when=FIRST_COMPLETED)
        for f in done:
            name, _ = running.pop(f)
            try:
                message, label = f.result()
            except Exception as e:
                log.warning("LLM %s failed, trying next: %s", name, e)
                errors.append(f"{name}: {e}")
                continue
            log.info("LLM answered by %s", label)
            return message, label
        now = time.monotonic()
        for f, (name, t) in list(running.items()):
            if now - t >= cap:
                running.pop(f)
                log.warning("LLM %s gave no answer within %.1f s, trying next", name, cap)
                errors.append(f"{name}: no answer within {cap} s")
        if not running:
            start_next()
        elif queue and now - max(t for _, t in running.values()) >= hedge:
            log.info("LLM %s is slow, asking %s as well", ", ".join(n for n, _ in running.values()), queue[0])
            start_next()
    raise LLMUnavailable("; ".join(errors) or "no providers configured")
