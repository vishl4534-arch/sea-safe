"""Watch this trip, on the server (owner, 13 Nov 2026).

The fisher taps "Watch this trip"; the browser gives a Web Push subscription; the server keeps the trip and checks
it again every `watch.check_minutes` (15) with the same verdict code as every other answer, until the departure
time. Only a change of verdict is sent, once, as a phone notification - so it works with the page closed, unlike
the page-open version that was removed earlier the same day.

Safety and privacy:
- Notifications go only to the browsers' own push services (`watch.push_hosts`), so the server can never be made
  to call another address with a forged "subscription".
- The words come from reviewed templates (push.title, push.body); the verdict from code, never the model.
- A notification can be late or not arrive: the card says so, and the official warnings still come first.
- What is stored: the push subscription (an address at the push service, no name or number) and the trip, in
  data/watch/watches.json; the server's own signing key (VAPID) in data/watch/vapid_private.pem. Both stay local
  (git-ignored).
"""
from __future__ import annotations

import base64
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse

from app import explain, service
from app.config import ROOT, load_app

log = logging.getLogger("seasafe.watch")
DIR = ROOT / "data" / "watch"
_lock = threading.Lock()


class Gone(Exception):
    """The push service says this subscription no longer exists (the fisher turned notifications off)."""


def cfg() -> dict:
    return load_app()["watch"]


# ---- the server's signing key (VAPID): made once, kept ------------------------------------------------------
def _key_path():
    return DIR / "vapid_private.pem"


def _private_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    path = _key_path()
    with _lock:
        if not path.exists():
            DIR.mkdir(parents=True, exist_ok=True)
            key = ec.generate_private_key(ec.SECP256R1())
            path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()))
            log.info("made a new push signing key")
        return serialization.load_pem_private_key(path.read_bytes(), password=None)


def public_key() -> str:
    """The key the browser needs to subscribe (applicationServerKey): the public point, base64url, no padding."""
    from cryptography.hazmat.primitives import serialization
    raw = _private_key().public_key().public_bytes(serialization.Encoding.X962,
                                                   serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# ---- where notifications may go -----------------------------------------------------------------------------
def allowed_endpoint(url: str) -> bool:
    """True only for https addresses at the browsers' own push services (or their sub-domains)."""
    try:
        u = urlparse(url or "")
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(host == h or host.endswith("." + h) for h in cfg()["push_hosts"])


# ---- the stored watches -------------------------------------------------------------------------------------
def _store():
    return DIR / "watches.json"


def all_watches() -> list[dict]:
    try:
        return json.loads(_store().read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return []


def _save(watches: list[dict]) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = _store().with_suffix(".tmp")
    tmp.write_text(json.dumps(watches, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(_store())


def add(subscription: dict, trip: dict, verdict: str) -> str:
    """Keep a watch; the same phone watching the same trip again replaces the old one. Returns its id."""
    wid = uuid.uuid4().hex[:16]
    with _lock:
        watches = [w for w in all_watches()
                   if not (w["subscription"]["endpoint"] == subscription["endpoint"] and w["trip"] == trip)]
        if len(watches) >= cfg()["max_watches"]:
            watches.pop(0)                           # the oldest makes room
        watches.append({"id": wid, "subscription": subscription, "trip": trip, "verdict": verdict,
                        "started": datetime.now().isoformat(timespec="seconds"), "checked": None})
        _save(watches)
    return wid


def remove(wid: str) -> None:
    with _lock:
        _save([w for w in all_watches() if w["id"] != wid])


# ---- sending ------------------------------------------------------------------------------------------------
def send(subscription: dict, payload: dict) -> None:
    """One Web Push notification. Raises Gone when the subscription no longer exists."""
    from pywebpush import WebPushException, webpush
    _private_key()                                   # make sure the key file exists
    try:
        webpush(subscription_info=subscription, data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=str(_key_path()), vapid_claims={"sub": cfg()["vapid_subject"]},
                ttl=cfg().get("ttl_seconds", 3600), timeout=10)
    except WebPushException as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        if status in (404, 410):
            raise Gone(str(status)) from e
        raise


def message(lang: str, res: dict, old: str, new: str) -> dict:
    """The notification, from reviewed templates: "Khor Fakkan: now CAUTION" / "Leaving Fri 13 Nov, 14:00:
    was SAFE, now CAUTION. Tap for the full answer." """
    place = explain.place_name(lang, res["place"])
    return {"title": explain.t(lang, "push.title", place=place, verdict=explain.t(lang, f"verdict.{new}")),
            "body": explain.t(lang, "push.body", departure=explain.when(lang, res["departure"]),
                              old=explain.t(lang, f"verdict.{old}"), new=explain.t(lang, f"verdict.{new}")),
            "url": "/"}


# ---- checking -----------------------------------------------------------------------------------------------
def _departed(trip: dict) -> bool:
    now, _, _ = service._clock(service.get_region(trip["region"]), "live")
    return datetime.fromisoformat(trip["departure_local"][:16]) < now


def check_all() -> int:
    """Check every watch once. Sends a notification for each changed verdict; forgets watches whose departure
    has passed, that can no longer be checked, or whose phone unsubscribed. Returns how many were sent."""
    sent, keep = 0, []
    snapshot = all_watches()
    for w in snapshot:
        trip = w["trip"]
        try:
            if _departed(trip):
                continue                             # watching ends at departure
            res = service.assess_trip(trip["region"], trip["place"], trip["departure_local"], trip["trip_hours"],
                                      trip["trip_length_given_by_user"], "live", trip.get("map_point"))
        except Exception as e:                       # one bad watch never stops the others
            log.warning("watch %s not checked: %s", w["id"], e)
            keep.append(w)
            continue
        if not res.get("ok"):
            continue                                 # cannot be checked any more (past, outside the window)
        w["checked"] = datetime.now().isoformat(timespec="seconds")
        if res["verdict"] != w["verdict"]:
            try:
                send(w["subscription"], message(trip.get("lang", "en"), res, w["verdict"], res["verdict"]))
                sent += 1
            except Gone:
                log.info("watch %s: the phone unsubscribed", w["id"])
                continue
            except Exception as e:                   # sent next time
                log.warning("watch %s: notification not sent: %s", w["id"], e)
                keep.append(w)
                continue
            w["verdict"] = res["verdict"]
        keep.append(w)
    before = {w["id"] for w in snapshot}
    with _lock:
        current = all_watches()
        still = {w["id"] for w in current}
        # checked watches that were not stopped meanwhile, plus any started while checking
        _save([w for w in keep if w["id"] in still] + [w for w in current if w["id"] not in before])
    return sent


def start() -> None:
    """Check all watches every check_minutes, in the background, for as long as the server runs."""
    def loop():
        while True:
            time.sleep(cfg()["check_minutes"] * 60)
            try:
                n = check_all()
                if n:
                    log.info("watch: %d notification(s) sent", n)
            except Exception:
                log.exception("watch check failed")
    threading.Thread(target=loop, name="watch", daemon=True).start()
