// Sea Safe offline helper (feature 6). It keeps a copy of the page, its styles and scripts, its text in
// every language, the settings and the map library, so the page still opens without a connection. It never
// keeps a verdict: the last answer is kept by the page itself (with its time), and shown only with its age.
// Everything is fetched fresh when there is a connection ("network first"); the copy is only a fallback.
const CACHE = "seasafe-shell-v3";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// What may be kept: the page and its files, its text and settings, and the libraries and fonts it loads.
// Never weather answers, chat or voice (those are POST requests or audio, and must be fresh).
function keep(url) {
  if (url.origin === self.location.origin) {
    return url.pathname === "/" || url.pathname.startsWith("/static/") || url.pathname === "/api/config"
      || url.pathname.startsWith("/api/translations/") || url.pathname === "/api/clock" || url.pathname === "/api/voice/status";
  }
  return ["unpkg.com", "fonts.googleapis.com", "fonts.gstatic.com"].includes(url.hostname);
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (!keep(url)) return;
  e.respondWith(fetch(req).then((res) => {
    if (res.ok || res.type === "opaque") {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
    }
    return res;
  }).catch(() => caches.match(req).then((hit) => hit
    // a page file asked for with a newer ?v= than the one kept: the kept one is better than nothing
    || (url.pathname.startsWith("/static/") ? caches.match(req, { ignoreSearch: true }) : undefined)
    || Response.error())));
});

// Watch this trip (13 Nov 2026): the server sends a notification when a watched trip's verdict changes
// (app/watch.py). It is shown even when the page is closed; tapping it opens Sea Safe.
self.addEventListener("push", (e) => {
  let msg = {};
  try { msg = e.data ? e.data.json() : {}; } catch { msg = { title: "Sea Safe", body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(msg.title || "Sea Safe", {
    body: msg.body || "", icon: "/static/img/logo-96.png", badge: "/static/img/logo-96.png",
    tag: "seasafe-watch", renotify: true, data: { url: msg.url || "/" } }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    const open = list.find((c) => new URL(c.url).origin === self.location.origin);
    return open ? open.focus() : self.clients.openWindow(url);
  }));
});
