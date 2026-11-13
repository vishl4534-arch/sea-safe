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

from app import emails, explain, mailer, service
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


def _who(w: dict) -> str:
    return (w.get("subscription") or {}).get("endpoint") or w.get("email") or ""


def add(subscription: dict | None, trip: dict, verdict: str, email: str | None = None) -> str:
    """Keep a watch (a phone subscription, an email, or both); the same phone or email watching the same trip
    again replaces the old one. Returns its id. The email is kept only with the watch."""
    wid = uuid.uuid4().hex[:16]
    new = {"id": wid, "subscription": subscription, "email": email, "trip": trip, "verdict": verdict,
           "started": datetime.now().isoformat(timespec="seconds"), "checked": None}
    with _lock:
        watches = [w for w in all_watches() if not (_who(w) == _who(new) and w["trip"] == trip)]
        if len(watches) >= cfg()["max_watches"]:
            watches.pop(0)                           # the oldest makes room
        watches.append(new)
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


# ---- email (13 Nov 2026): a confirmation when watching starts, and each verdict change ------------------------
def _in_background(fn) -> None:
    """Emails take a second or two: never make the page wait for one."""
    threading.Thread(target=fn, name="watch-mail", daemon=True).start()


def mail(to: str, subject: str, body: str, html: str | None = None) -> bool:
    try:
        mailer.send(to, subject, body, html=html)
        return True
    except Exception as e:                           # not set up, refused, no connection: logged, never fatal
        log.warning("email not sent: %s", e)
        return False


def confirm(email: str, trip: dict, res: dict) -> bool:
    """The email when watching starts: the trip, the verdict now, how it works and how to stop (templates)."""
    lang = trip.get("lang", "en")
    place = explain.place_name(lang, res["place"])
    body = "\n\n".join([
        explain.t(lang, "email.start.body", place=place, departure=explain.when(lang, trip["departure_local"]),
                  hours=trip["trip_hours"], verdict=explain.t(lang, f"verdict.{res['verdict']}"),
                  minutes=cfg()["check_minutes"]),
        explain.t(lang, "chat.b.disclaimer"), explain.t(lang, "email.footer")])
    page = emails.html(lang, kicker=explain.t(lang, "email.start.kicker"), heading=place,
                       badges=[(res["verdict"], explain.t(lang, f"verdict.{res['verdict']}"), False)],
                       rows=_rows(lang, trip), lead=explain.t(lang, "email.start.next"),
                       note=explain.t(lang, "chat.b.disclaimer"), footer=explain.t(lang, "email.footer"))
    return mail(email, explain.t(lang, "email.start.subject", place=place), body, page)


def _rows(lang: str, trip: dict) -> list:
    return [(explain.t(lang, "email.row.leaving"), explain.when(lang, trip["departure_local"])),
            (explain.t(lang, "email.row.length"), explain.t(lang, "trip.hours", hours=trip["trip_hours"])),
            (explain.t(lang, "email.row.checks"), explain.t(lang, "email.checks_value", minutes=cfg()["check_minutes"]))]


def change_email(lang: str, trip: dict, res: dict, old: str, new: str, payload: dict) -> tuple[str, str]:
    """The email for a changed verdict: (plain text, html). Old verdict struck through, then the new one."""
    text = payload["body"] + "\n\n" + explain.t(lang, "chat.b.disclaimer")
    page = emails.html(lang, kicker=explain.t(lang, "email.change.kicker"), heading=explain.place_name(lang, res["place"]),
                       badges=[(old, explain.t(lang, f"verdict.{old}"), True), (new, explain.t(lang, f"verdict.{new}"), False)],
                       rows=_rows(lang, trip), lead=explain.t(lang, "email.change.next"),
                       note=explain.t(lang, "chat.b.disclaimer"), footer=explain.t(lang, "email.footer"))
    return text, page


# ---- checking -----------------------------------------------------------------------------------------------
def _departed(trip: dict) -> bool:
    now, _, _ = service._clock(service.get_region(trip["region"]), "live")
    return datetime.fromisoformat(trip["departure_local"][:16]) < now


def check_all() -> int:
    """Check every watch once. Sends a notification and/or an email for each changed verdict; forgets watches
    whose departure has passed, that can no longer be checked, or that have nobody left to tell. Returns how many
    changes were delivered."""
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
            lang = trip.get("lang", "en")
            payload, delivered = message(lang, res, w["verdict"], res["verdict"]), False
            if w.get("subscription"):
                try:
                    send(w["subscription"], payload)
                    delivered = True
                except Gone:
                    log.info("watch %s: the phone unsubscribed", w["id"])
                    w["subscription"] = None
                except Exception as e:
                    log.warning("watch %s: notification not sent: %s", w["id"], e)
            if w.get("email"):
                text, page = change_email(lang, trip, res, w["verdict"], res["verdict"], payload)
                if mail(w["email"], payload["title"], text, page):
                    delivered = True
            if not w.get("subscription") and not w.get("email"):
                continue                             # nobody left to tell
            if not delivered:
                keep.append(w)                       # tried again at the next check
                continue
            sent += 1
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
