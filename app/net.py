"""One shared HTTP client for the outside services (Groq, Gemini, ElevenLabs, Open-Meteo).

Opening a new secure connection costs 0.5-0.8 s from here (measured 12 Nov 2026: Groq 1.12 s on a new
connection, 0.52 s on a kept one). So connections are kept open and reused, and warmed when the fisher
presses the mic, while they are still speaking."""
import logging
import threading

import httpx

log = logging.getLogger("seasafe.net")

# Idle connections are kept for 90 s (httpx's default is 5 s). retries=1 re-opens a connection the
# server closed while it was idle, so a stale connection costs a reconnect, not an error.
CLIENT = httpx.Client(timeout=30, transport=httpx.HTTPTransport(retries=1),
                      limits=httpx.Limits(max_connections=40, max_keepalive_connections=20, keepalive_expiry=90))


def warm(urls: list[str]) -> None:
    """Open (or refresh) a connection to each host in the background. The answer does not matter;
    a 401 or 404 still leaves a ready connection behind."""
    def run(url):
        try:
            CLIENT.head(url, timeout=5)
        except httpx.HTTPError as e:
            log.info("warm-up of %s failed: %s", url, e)
    for url in dict.fromkeys(urls):
        threading.Thread(target=run, args=(url,), daemon=True).start()
