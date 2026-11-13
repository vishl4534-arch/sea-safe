// Sea Safe page. Plain JS, no build step. All text comes from /api/translations;
// all verdicts come from the server (app/assessment.py). Voice first: the answer card and the
// mic are the page; the map is a second tab on phones and sits beside the answer on a laptop.
// Everything that moves on screen shows real data: the pins, the gauges, the hour bars, the wind.
const S = {
  cfg: null, tr: {}, region: null, lang: "en", mode: "live",
  clock: null, departure: null, tripHours: 6, tripGiven: false, pickOpen: false,
  place: null,            // {kind: "harbour", id} or {kind: "map_point", lat, lon}
  history: [], context: null,
  watchOffer: null,       // the trip the last answer offered to watch ("Want me to watch this trip?"), until answered
  watchSkip: [],          // trips already offered in this conversation: offered once only
  map: null, pins: {}, pointMarker: null, pinsLit: false, fitPending: false,
  tl: null,               // the 48-hour timeline: verdict per harbour per departure hour
  wind: null, windOn: true, play: null, commit: null,
  seq: { pins: 0, card: 0, chat: 0, tl: 0, wind: 0 },   // newest request number of each kind; chat: bumped on region/mode switch
  voice: { status: null, rec: null, timer: null, audio: null, busy: false, speaking: false, ctx: null, meter: 0, metered: false },
};

// ---------------------------------------------------------------- pictures
// One set of line icons (Lucide, ISC licence) and one shape per verdict, used everywhere:
// circle = SAFE, triangle = CAUTION, octagon = UNSAFE. Colour is never the only signal.
const ICONS = {
  waves: '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
  wind: '<path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/>',
  gust: '<path d="M21 4H3"/><path d="M18 8H6"/><path d="M19 12H9"/><path d="M16 16h-6"/><path d="M11 20H9"/>',
  storm: '<path d="M6 16.326A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 .5 8.973"/><path d="m13 12-3 5h4l-3 5"/>',
  eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  hourglass: '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
  boat: '<path d="M22 18H2a4 4 0 0 0 4 4h12a4 4 0 0 0 4-4Z"/><path d="M21 14 10 2 3 14h18Z"/><path d="M10 2v16"/>',
  pin: '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
  volume: '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/><path d="M16 9a5 5 0 0 1 0 6"/><path d="M19.364 18.364a9 9 0 0 0 0-12.728"/>',
  mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
  pencil: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
  sliders: '<path d="M21 4h-7"/><path d="M10 4H3"/><path d="M21 12h-9"/><path d="M8 12H3"/><path d="M21 20h-5"/><path d="M12 20H3"/><path d="M14 2v4"/><path d="M8 10v4"/><path d="M16 18v4"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
  moon: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  send: '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>',
  audio: '<path d="M2 10v3"/><path d="M6 6v11"/><path d="M10 3v18"/><path d="M14 8v7"/><path d="M18 5v13"/><path d="M22 10v3"/>',
  map: '<path d="M14.106 5.553a2 2 0 0 0 1.788 0l3.659-1.83A1 1 0 0 1 21 4.619v12.764a1 1 0 0 1-.553.894l-4.553 2.277a2 2 0 0 1-1.788 0l-4.212-2.106a2 2 0 0 0-1.788 0l-3.659 1.83A1 1 0 0 1 3 19.381V6.618a1 1 0 0 1 .553-.894l4.553-2.277a2 2 0 0 1 1.788 0z"/><path d="M15 5.764v15"/><path d="M9 3.236v15"/>',
  message: '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  play: '<path d="M6 4.5v15a1 1 0 0 0 1.5.86l12.5-7.5a1 1 0 0 0 0-1.72L7.5 3.64A1 1 0 0 0 6 4.5Z"/>',
  pause: '<path d="M8 4v16"/><path d="M16 4v16"/>',
  down: '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  share: '<path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><path d="m16 6-4-4-4 4"/><path d="M12 2v13"/>',
  bell: '<path d="M10.268 21a2 2 0 0 0 3.464 0"/><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326"/>',
};
const icon = (name) => `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ICONS.info}</svg>`;
// what each reason or parameter is about -> its icon
const PICON = { wave_height: "waves", wind_speed: "wind", wind_gusts: "gust", thunderstorm: "storm", visibility: "eye",
                missing: "help", stale: "hourglass", beyond_window: "hourglass", summary: "waves" };
const SHAPES = {
  SAFE: '<circle cx="12" cy="12" r="9"/>',
  CAUTION: '<path d="M12 3.4 21.6 20H2.4Z"/>',
  UNSAFE: '<path d="M8 2.6h8l5.4 5.4v8L16 21.4H8L2.6 16V8Z"/>',
};
const shape = (verdict) => `<svg class="shape" viewBox="0 0 24 24" aria-hidden="true">${SHAPES[verdict] || SHAPES.SAFE}</svg>`;

const $ = (id) => document.getElementById(id);
const t = (key, vars = {}) => (S.tr[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const store = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
                set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
                del: (k) => { try { localStorage.removeItem(k); } catch { /* private mode */ } } };
const calm = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;   // the user asked for less motion

// The fisher's usual harbour and trip length, kept only in this browser, one per region. Only these two
// settings: never a forecast or a verdict, so nothing old can be mistaken for today's answer.
const usualKey = () => `usual.${S.region}`;
function getUsual() {
  try { return JSON.parse(store.get(usualKey()) || "null") || {}; } catch { return {}; }
}
function saveUsual(change) {
  store.set(usualKey(), JSON.stringify({ ...getUsual(), ...change }));
  renderUsual();
}
function forgetUsual() { store.del(usualKey()); renderUsual(); }
function renderUsual() {
  const u = getUsual(), el = $("usual");
  const known = u.place && regionCfg().harbours.some((h) => h.id === u.place);
  el.hidden = true;                          // not shown since 13 Nov: the bot asks instead
  renderExamples();
  if (!known) return;
  $("usual-text").textContent = t("ui.usual", { place: t(`place.${u.place}`),
    trip: u.hours ? t("ui.usual_trip", { hours: u.hours }) : "" });
}
const isPhone = () => window.matchMedia("(max-width: 959px)").matches;

async function api(path, body) {
  let r;
  try {
    r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" },
                                   body: JSON.stringify(body) } : {});
  } catch (e) {                              // no answer at all: the server is not running, or no connection
    const err = new Error(`${path}: ${e.message}`); err.offline = true; throw err;
  }
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

// What to say after a failed request: "can't reach the server" when nothing answered, else the usual line.
const failText = (e) => t(e && e.offline ? "error.server_down" : "error.generic");

// Times are the region's wall-clock times ("2026-11-13T05:00"). They are handled as UTC inside the
// browser so the browser's own time zone (and its daylight saving) can never shift or drop an hour.
const utc = (iso) => new Date(Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10), +(iso.slice(11, 13) || 0), +(iso.slice(14, 16) || 0)));
const isoOf = (d) => d.toISOString().slice(0, 16);
const addHours = (iso, h) => isoOf(new Date(utc(iso).getTime() + h * 3600e3));
function when(iso) {
  const d = utc(iso);
  return t("time.format", { weekday: t(`weekday.${(d.getUTCDay() + 6) % 7}`), day: d.getUTCDate(),
    month: t(`month.${d.getUTCMonth() + 1}`), hh: String(d.getUTCHours()).padStart(2, "0"), mm: "00" });
}
function onDate(iso) {
  const d = utc(iso);
  return t("date.format", { day: d.getUTCDate(), month: t(`month.${d.getUTCMonth() + 1}`), year: d.getUTCFullYear() });
}
const regionCfg = () => S.cfg.regions.find((r) => r.id === S.region);

// ---------------------------------------------------------------- setup
async function init() {
  document.querySelectorAll("[data-icon]").forEach((el) => { el.innerHTML = icon(el.dataset.icon); });
  S.cfg = await api("/api/config");
  S.region = S.cfg.regions.some((r) => r.id === store.get("region")) ? store.get("region") : S.cfg.regions[0].id;
  S.tripHours = S.cfg.trip.default_hours;
  S.windOn = store.get("wind") !== "off";
  initMap();

  $("settings-toggle").onclick = () => showSettings(!document.body.classList.contains("show-settings"));
  // Settings close on a click anywhere else (13 Nov 2026), and with Escape (below).
  document.addEventListener("click", (e) => {
    if (document.body.classList.contains("show-settings") && !e.target.closest(".top")) showSettings(false);
  });
  // No choice made here yet: follow the phone when it switches between light and dark.
  if (window.matchMedia) matchMedia("(prefers-color-scheme: light)").addEventListener("change", (e) => {
    if (!store.get("theme")) applyTheme(e.matches ? "light" : "dark");
  });
  $("tab-answer").onclick = () => setTab("answer");
  $("tab-map").onclick = () => setTab("map");
  $("how-open").onclick = openHow;
  $("how-close").onclick = () => $("how").close();
  $("chat-form").onsubmit = (e) => { e.preventDefault(); sendChat($("chat-input").value); };
  $("chat-input").oninput = () => syncComposer();
  $("sheet-close").onclick = closeSheet;
  $("sheet").querySelector("[data-close]").onclick = closeSheet;
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sheetOpen()) { e.stopPropagation(); closeSheet(); }
    else if (e.key === "Escape" && document.body.classList.contains("show-settings")) {
      e.stopPropagation(); showSettings(false); $("settings-toggle").focus();
    }
  }, true);
  // The waveform button opens voice mode: a hands-free conversation (static/voicemode.js).
  $("mic").onclick = () => (typeof VoiceMode !== "undefined" && navigator.mediaDevices ? VoiceMode.open() : onMic());
  $("usual-forget").onclick = forgetUsual;
  $("tl-range").oninput = (e) => { stopPlay(); previewHour(+e.target.value); };
  $("tl-play").onclick = () => (S.play ? stopPlay() : startPlay());
  $("wind-toggle").onclick = () => { S.windOn = !S.windOn; store.set("wind", S.windOn ? "on" : "off"); renderWindToggle(); };
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch((e) => console.warn(e));
  window.addEventListener("offline", renderOnline);
  window.addEventListener("online", () => { renderOnline(); refreshAll(true); });
  S.voice.status = await api("/api/voice/status").catch(() => null);
  setInterval(tickClock, 5 * 60 * 1000);   // live clock moves on: drop past hours from the list
  await switchRegion();
}

function setTab(which) {
  document.body.classList.toggle("show-map", which === "map");
  $("tab-answer").setAttribute("aria-selected", which !== "map");
  $("tab-map").setAttribute("aria-selected", which === "map");
  if (which === "map" && S.map) setTimeout(() => { S.map.resize(); if (S.fitPending) flyToRegion(); }, 0);
}

function clearChat() {
  S.history = []; S.context = null; S.seq.chat++;
  $("chat-log").innerHTML = "";
  syncWelcome();
  stopAudio();
  if (S.voice.rec) { S.voice.rec.onstop = null; S.voice.rec.stop(); S.voice.rec = null; }
  renderMic();
}

// The welcome message makes room for the answer: it shows only while there is no card and no
// conversation. The suggested questions above the mic go once the conversation has started.
function syncWelcome() {
  const talking = $("chat-log").children.length > 0;   // the answer is in the chat now, the card in the sheet
  $("welcome").hidden = talking;
  $("examples").hidden = talking;
  document.body.classList.toggle("picked", !!S.place);
  document.body.classList.toggle("empty", !talking);
}

// ---------------------------------------------------------------- the sheet: the full answer, on request
// "See the full answer" slides the card up over the chat; closing it lands back in the same place in
// the chat. The card's own reveal plays as it opens. Nothing ever scrolls the chat to a card.
const sheetOpen = () => !$("sheet").hidden;
function openSheet(view, opener) {
  if (!view) return;
  if (view.groups) renderRegion(view);
  else {
    const ok = selectView(view);
    renderCard(view, !calm());
    if (!ok) $("card").classList.add("no-actions");      // safer times would act on another trip
  }
  const sheet = $("sheet");
  S.sheetOpener = opener || document.activeElement;
  sheet.hidden = false;
  coverBehind(true);
  requestAnimationFrame(() => sheet.classList.add("open"));
  $("sheet-body").scrollTop = 0;
  $("sheet-close").focus({ preventScroll: true });
}
function closeSheet() {
  const sheet = $("sheet");
  if (sheet.hidden) return;
  sheet.classList.remove("open");
  setTimeout(() => { if (!sheet.classList.contains("open")) sheet.hidden = true; }, calm() ? 0 : 320);
  coverBehind(false);                        // before the focus moves: covered things can't take focus
  const back = S.sheetOpener; S.sheetOpener = null;
  if (back && document.contains(back)) back.focus({ preventScroll: true });
  else if (sheet.contains(document.activeElement)) $("chat-input").focus({ preventScroll: true });   // the opener went with the chat
}

// While the sheet is open, what it covers can't be reached with Tab or a screen reader. On a phone that is
// the whole page (the sheet is modal); on a laptop only the chat panel, so the map and the time slider
// still work beside the sheet and update it.
function coverBehind(on) {
  document.querySelectorAll("[data-sheet-inert]").forEach((el) => { el.inert = false; el.removeAttribute("data-sheet-inert"); });
  $("sheet").querySelector(".sheet-panel").setAttribute("aria-modal", String(on && isPhone()));
  if (!on) return;
  const covered = [...document.querySelectorAll(".panel > :not(#sheet)")];
  if (isPhone()) covered.push(...document.querySelectorAll("body > :not(main):not(script):not(dialog), .layout > .stage"));
  covered.filter((el) => !el.inert).forEach((el) => { el.inert = true; el.setAttribute("data-sheet-inert", ""); });
}

// An older answer opened from the chat becomes the selection again (place, departure, length, pins), so
// "safer times" and the slider act on the trip the sheet shows, never on a newer one.
// A trip that can't be selected here (another coast or mode, or an older map point) returns false.
function selectView(v) {
  const f = v.trip_fields;
  if (!f) return false;
  if (!!f.live !== (S.mode === "live")) return false;
  if (S.pins[f.place_id]) {
    stopPlay();
    S.place = { kind: "harbour", id: f.place_id };
    if (S.pointMarker) { S.pointMarker.remove(); S.pointMarker = null; }
    S.departure = f.departure; S.tripHours = f.hours; S.tripGiven = !!f.given;
    // An assumed trip length (a map answer) never becomes the chat's trip: the chat still asks for it.
    S.context = f.given ? { place: f.place_id, departure: f.departure, trip_hours: f.hours, given: true }
                        : { place: f.place_id };
    renderDepartures(); renderTripChips();
    S.seq.card++;                            // an older check in flight must not replace this answer
    refreshPins();
    return true;
  }
  return !!S.place && S.place.id === f.place_id && S.departure === f.departure && S.tripHours === f.hours;
}

// An answer that did not come from the chat (a tapped harbour, a safer time, a saved answer): a bubble
// with its bullets, like a chat answer; its "See the full answer" opens this answer.
function postAnswer(view, lead) {
  if (!view) return;
  const text = (lead ? lead + "\n" : "") + (view.bullets || view.advice);
  addMsg("bot", text, view.verdict, null, view);
  S.history.push({ role: "assistant", content: text });
}

async function tickClock() {
  if (S.mode !== "live" || !S.clock) return;
  const fresh = await api(`/api/clock?region=${S.region}&mode=live`).catch(() => null);
  if (!fresh || S.mode !== "live" || fresh.now === S.clock.now) return;
  S.clock = fresh;
  if (S.departure < fresh.now) S.departure = fresh.now;
  renderDepartures();
  refreshAll(true);
}

async function switchRegion() {
  const r = regionCfg();
  const saved = store.get("lang");
  S.lang = r.languages.includes(saved) ? saved : r.languages[0];
  S.mode = "live"; S.place = null; S.tl = null; stopPlay(); clearChat();
  // Start from the fisher's usual harbour and trip length, if this phone remembers them for this region.
  const u = getUsual();
  // (13 Nov) No harbour is chosen for the fisher at start: they say it, or tap the map.
  const okHours = Number.isInteger(u.hours) && u.hours >= 1 && u.hours <= S.cfg.trip.max_hours;
  S.tripHours = okHours ? u.hours : S.cfg.trip.default_hours; S.tripGiven = okHours;
  closeSheet(); S.view = null;
  buildPins();
  flyToRegion();
  await loadLang();
  await startClock();
  loadWind();
  await refreshAll();
}

async function loadLang() {
  S.tr = await api(`/api/translations/${S.lang}`);
  const dir = S.cfg.languages[S.lang].dir;
  document.documentElement.lang = S.lang; document.documentElement.dir = dir; document.body.dir = dir;
  document.title = t("app.title");
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
  document.querySelectorAll("[data-t-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.tPlaceholder); });
  $("sheet-close").innerHTML = icon("x"); $("sheet-close").setAttribute("aria-label", t("ui.close")); $("sheet-close").title = t("ui.close");
  const r = regionCfg();
  seg($("region"), S.cfg.regions.map((x) => [x.id, t(`region.${x.id}`)]), S.region,
      (v) => { S.region = v; store.set("region", v); switchRegion(); });
  seg($("lang"), r.languages.map((l) => [l, S.cfg.languages[l].name]), S.lang,
      (v) => { S.lang = v; store.set("lang", v); loadLang().then(() => refreshAll(true)); });   // the open sheet follows; no new bubble
  renderTheme();
  document.querySelectorAll(".avatar").forEach((a) => { a.innerHTML = avatarHtml(); });
  renderTripChips(); renderDepartures(); renderPins(); renderMic(); renderTimeline(); renderWindToggle();
  renderUsual(); renderOnline();
}

// A list to choose one item from (forecast or replay, departure hour). Built here instead of the
// browser's own drop-down so it looks the same everywhere. Keyboard: arrows move, Enter chooses,
// Escape closes; a tap outside closes it too.
// groups: [{label?, items: [[value, label, longer label for the button?]]}]
function menu(root, groups, value, onPick) {
  const btn = root.querySelector(".menu-btn"), list = root.querySelector(".menu-list");
  const items = groups.flatMap((g) => g.items), chosen = items.find(([v]) => v === value) || items[0] || ["", ""];
  root._value = value; root._pick = onPick;
  root.querySelector(".menu-val").textContent = chosen[2] || chosen[1];
  list.innerHTML = groups.map((g) => (g.label ? `<div class="menu-group" role="presentation">${esc(g.label)}</div>` : "") +
    `<div class="menu-items" role="presentation">${g.items.map(([v, label, long]) =>
      `<div class="menu-opt" role="option" tabindex="-1" aria-selected="${v === value}" data-v="${esc(v)}" data-long="${esc(long || label)}">${esc(label)}</div>`).join("")}</div>`).join("");
  if (root._wired) return;
  root._wired = true;
  const opts = () => [...list.querySelectorAll(".menu-opt")];
  const pick = (v) => {                     // show the choice at once, then act on it
    closeMenu(root, true);
    if (v === root._value) return;
    root._value = v;
    opts().forEach((o) => o.setAttribute("aria-selected", o.dataset.v === v));
    const o = opts().find((x) => x.dataset.v === v);
    if (o) root.querySelector(".menu-val").textContent = o.dataset.long;
    root._pick(v);
  };
  btn.onclick = () => (list.hidden ? openMenu(root) : closeMenu(root, true));
  btn.onkeydown = (e) => { if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); openMenu(root); } };
  list.onclick = (e) => { const o = e.target.closest(".menu-opt"); if (o) pick(o.dataset.v); };
  list.onkeydown = (e) => {
    const all = opts(), i = all.indexOf(document.activeElement);
    const go = (k) => { e.preventDefault(); all[Math.max(0, Math.min(all.length - 1, k))].focus(); };
    if (e.key === "ArrowDown") go(i + 1);
    else if (e.key === "ArrowUp") go(i - 1);
    else if (e.key === "Home") go(0);
    else if (e.key === "End") go(all.length - 1);
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (all[i]) pick(all[i].dataset.v); }
    else if (e.key === "Escape") { e.preventDefault(); closeMenu(root, true); }
    else if (e.key === "Tab") closeMenu(root, false);
  };
}
function openMenu(root) {
  document.querySelectorAll(".menu").forEach((m) => { if (m !== root) closeMenu(m, false); });
  const btn = root.querySelector(".menu-btn"), list = root.querySelector(".menu-list");
  list.hidden = false; btn.setAttribute("aria-expanded", "true");
  const on = list.querySelector('[aria-selected="true"]') || list.querySelector(".menu-opt");
  if (on) { on.focus({ preventScroll: true }); on.scrollIntoView({ block: "nearest" }); }
}
function closeMenu(root, focusButton) {
  const btn = root.querySelector(".menu-btn"), list = root.querySelector(".menu-list");
  if (list.hidden) return;
  list.hidden = true; btn.setAttribute("aria-expanded", "false");
  if (focusButton) btn.focus({ preventScroll: true });
}
document.addEventListener("pointerdown", (e) => {
  document.querySelectorAll(".menu").forEach((m) => { if (!m.contains(e.target)) closeMenu(m, false); });
});

// A row of buttons where exactly one is chosen (region, language): one tap, no list to open.
// The settings: on a laptop Region, Language, Dark/Light and How we decide slide out from the button; on a
// phone they drop down under the top bar. While closed they can't be reached with Tab.
function showSettings(open) {
  document.body.classList.toggle("show-settings", open);
  $("settings-toggle").setAttribute("aria-expanded", open);
  $("pickers").inert = !open;
}

// ---------------------------------------------------------------- light and dark
// Light or dark (13 Nov 2026, owner). The page starts in the phone's own mode (index.html sets it before the
// first paint); a choice here is remembered. The new mode spreads out in a circle from the button pressed
// (View Transitions); the map and the wind streaks are recoloured, and the logo's colours are inverted by CSS.
// Reduced motion: it simply switches. Browsers without View Transitions: the colours fade.
function setTheme(next, from) {
  store.set("theme", next);
  if (calm()) { applyTheme(next); return; }
  if (!document.startViewTransition) {
    document.documentElement.classList.add("theme-fade");
    applyTheme(next);
    setTimeout(() => document.documentElement.classList.remove("theme-fade"), 600);
    return;
  }
  const r = (from || $("settings-toggle")).getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const end = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  const vt = document.startViewTransition(() => { applyTheme(next); return mapRepainted(); });
  vt.ready.then(() => document.documentElement.animate(
    { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${end}px at ${x}px ${y}px)`] },
    { duration: 700, easing: "cubic-bezier(.23, 1, .32, 1)", pseudoElement: "::view-transition-new(root)" })).catch(() => {});
}
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", getComputedStyle(document.documentElement).getPropertyValue("--deep").trim());
  if (S.map) { try { paintSea(); } catch (e) { console.warn(e); } }
  if (S.wind && S.wind.setTheme) S.wind.setTheme();
  if ($("theme") && S.tr) renderTheme();
}
// The new map colours are drawn on the next frame: wait for it (at most a quarter second) so the circle
// reveals the recoloured map, not the old one.
const mapRepainted = () => !S.map ? Promise.resolve()
  : Promise.race([new Promise((r) => S.map.once("render", () => requestAnimationFrame(r))), new Promise((r) => setTimeout(r, 250))]);
function renderTheme() {
  const cur = document.documentElement.dataset.theme;
  $("theme").innerHTML = [["dark", "moon", "ui.theme_dark"], ["light", "sun", "ui.theme_light"]].map(([v, ic, key]) =>
    `<button type="button" role="radio" aria-checked="${v === cur}" data-v="${v}">${icon(ic)}<span>${esc(t(key))}</span></button>`).join("");
  $("theme").querySelectorAll("button").forEach((b) => b.onclick = () => {
    if (b.dataset.v !== document.documentElement.dataset.theme) setTheme(b.dataset.v, b);
  });
}

function seg(el, options, value, onPick) {
  el.innerHTML = options.map(([v, label]) =>
    `<button type="button" role="radio" aria-checked="${v === value}" data-v="${esc(v)}">${esc(label)}</button>`).join("");
  el.querySelectorAll("button").forEach((b) => b.onclick = () => { if (b.dataset.v !== value) onPick(b.dataset.v); });
}

async function startClock() {
  S.clock = await api(`/api/clock?region=${S.region}&mode=${S.mode}`);
  S.departure = S.mode === "live" ? S.clock.now : S.clock.default_departure;
  S.pickOpen = false; S.tl = null;
  renderDepartures();
}

// ---------------------------------------------------------------- when: departure and trip length
// Big buttons instead of a 48-item list: Now, This evening, Tomorrow 5 am, or Pick a time.
// The slider on the map sets the same departure hour.
function quickDepartures() {
  const now = S.clock.now, first = S.mode === "live" ? now : S.clock.default_departure;
  const day = now.slice(0, 10), hour = +now.slice(11, 13);
  // before 04:00 "tomorrow" is the coming morning (same rule as app/tools.py)
  const base = hour < 4 ? isoOf(new Date(utc(day).getTime() - 864e5)).slice(0, 10) : day;
  const evening = `${day}T17:00`, tomorrow = `${isoOf(new Date(utc(base).getTime() + 864e5)).slice(0, 10)}T05:00`;
  const ok = (iso) => iso >= now && iso < S.clock.window_end;
  return [["now", first], ["evening", ok(evening) && evening !== first ? evening : null],
          ["tomorrow", ok(tomorrow) && tomorrow !== first ? tomorrow : null]].filter(([, iso]) => iso);
}

function renderDepartures() {
  if (!S.clock) return;
  // Pick a time: the 48 hours, one group per day, each hour a small button
  const days = [];
  for (let d = utc(S.clock.now), end = utc(S.clock.window_end); d < end; d = new Date(d.getTime() + 3600e3)) {
    const iso = isoOf(d), day = onDate(iso);
    if (!days.length || days[days.length - 1].label !== day) days.push({ label: day, items: [] });
    days[days.length - 1].items.push([iso, iso.slice(11, 16), when(iso)]);
  }
  menu($("departure"), days, S.departure, (v) => { stopPlay(); setDeparture(v); });
  const quick = quickDepartures();
  const matched = quick.some(([, iso]) => iso === S.departure);
  const picking = S.pickOpen || !matched;
  $("dep-chips").innerHTML = quick.map(([k, iso]) =>
    `<button type="button" class="chip" role="radio" aria-checked="${!picking && iso === S.departure}" data-iso="${iso}">${esc(t("ui.dep_" + k))}</button>`).join("")
    + `<button type="button" class="chip" role="radio" aria-checked="${picking}" data-pick="1">${esc(t("ui.dep_pick"))}</button>`;
  $("dep-chips").querySelectorAll(".chip").forEach((b) => b.onclick = () => {
    stopPlay();
    if (b.dataset.pick) { S.pickOpen = true; renderDepartures(); openMenu($("departure")); return; }
    S.pickOpen = false; setDeparture(b.dataset.iso);
  });
  $("departure").hidden = !picking;
}

function setDeparture(iso) { S.departure = iso; renderDepartures(); refreshAll(); }

function renderTripChips() {
  $("trip-chips").innerHTML = S.cfg.trip.quick_choices.map((h) =>
    `<button type="button" class="chip" role="radio" aria-checked="${h === S.tripHours}" data-h="${h}">${esc(t("ui.hours_short", { hours: h }))}</button>`).join("");
  $("trip-chips").querySelectorAll(".chip").forEach((b) => b.onclick = () => {
    S.tripHours = Number(b.dataset.h); S.tripGiven = true; saveUsual({ hours: S.tripHours });
    renderTripChips(); refreshAll();
  });
}

function renderExamples() {
  const usual = getUsual().place, hs = regionCfg().harbours;           // the remembered harbour, else the first one
  const first = hs.find((h) => h.id === usual) || hs[0];
  const qs = [1, 4].map((i) => t(`ui.example.${i}`, { from_place: first ? t(`place_from.${first.id}`) : "" }));
  $("examples").innerHTML = qs.map((q) => `<button type="button" class="chip">${esc(q)}</button>`).join("");
  $("examples").querySelectorAll(".chip").forEach((b) => b.onclick = () => sendChat(b.textContent));
  $("examples").setAttribute("aria-label", t("ui.examples"));
}

// ---------------------------------------------------------------- map
// MapLibre draws a free vector map (OpenFreeMap). We recolour it so the sea carries the light and
// the land is a dark shape: this is a page about the sea. Roads and buildings are switched off.
function initMap() {
  if (!window.maplibregl) return;                       // map library did not load: the answer and the voice still work
  try {
    S.map = new maplibregl.Map({ container: "map", style: S.cfg.map_style, center: [64, 19.5], zoom: 3.3,
      minZoom: 2.5, maxZoom: 12, attributionControl: false, dragRotate: false, pitchWithRotate: false });
  } catch (e) { console.error(e); S.map = null; return; }
  S.map.touchZoomRotate.disableRotation();
  S.map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
  S.map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
  S.map.on("style.load", paintSea);
  S.map.on("click", (e) => selectPoint(e.lngLat.lat, e.lngLat.lng));
  S.map.on("resize", () => { if (S.fitPending) flyToRegion(); });          // the map was hidden when the region was chosen
  S.map.on("load", () => {
    if (!S.cfg.wind_picture || !S.cfg.wind_picture.enabled || typeof WindPicture === "undefined") return;
    S.wind = new WindPicture(S.map, S.cfg.wind_picture);
    S.wind.setOn(S.windOn);
    renderWindToggle();
    loadWind();
  });
}

function paintSea() {
  const css = getComputedStyle(document.documentElement), v = (name) => css.getPropertyValue(name).trim();
  const land = v("--land"), sea = v("--sea");             // light or dark: every colour comes from the theme
  const quiet = /^(highway|railway|tunnel|aeroway|building|landuse|road_|park|landcover|waterway|place_other|place_suburb|place_village)/;
  const set = (id, prop, value) => { try { S.map.setPaintProperty(id, prop, value); } catch { /* layer not in this style */ } };
  for (const layer of S.map.getStyle().layers) {
    if (quiet.test(layer.id)) S.map.setLayoutProperty(layer.id, "visibility", "none");
    else if (layer.type === "symbol") {
      set(layer.id, "text-color", layer.id === "water_name" ? v("--map-water-label") : v("--map-label"));
      set(layer.id, "text-halo-color", layer.id === "water_name" ? sea : land);
      set(layer.id, "text-halo-width", 1.2);
    } else if (layer.id.startsWith("boundary")) set(layer.id, "line-color", v("--map-border"));
  }
  set("background", "background-color", land);
  set("water", "fill-color", sea);
  if (!S.map.getLayer("shore")) {                      // a thin line of light where the sea meets the land
    S.map.addLayer({ id: "shore", type: "line", source: "openmaptiles", "source-layer": "water",
      paint: { "line-color": v("--map-shore"), "line-width": 1, "line-blur": 0.4 } }, S.map.getLayer("water_name") ? "water_name" : undefined);
  } else set("shore", "line-color", v("--map-shore"));
}

// Bring every harbour of the region into view. On the first load and on a region switch the camera
// flies there; with reduced motion it simply jumps (MapLibre does that for non-essential moves).
function flyToRegion() {
  if (!S.map) return;
  const box = S.map.getContainer();
  if (!box.clientWidth || !box.clientHeight) { S.fitPending = true; return; }   // map tab not open yet (phone)
  S.fitPending = false;
  const r = regionCfg(), b = new maplibregl.LngLatBounds();
  r.harbours.forEach((h) => b.extend([h.lon, h.lat]));
  const side = Math.min(110, box.clientWidth * 0.14);
  const cam = r.harbours.length && S.map.cameraForBounds(b, { padding: { top: 76, bottom: 150, left: side, right: side }, maxZoom: 8.6 });
  if (!cam) { S.map.jumpTo({ center: [r.map.center[1], r.map.center[0]], zoom: r.map.zoom - 1 }); return; }
  S.map.flyTo({ ...cam, duration: 2800, curve: 1.35, essential: false });
}

function buildPins() {
  if (S.pointMarker) { S.pointMarker.remove(); S.pointMarker = null; }
  Object.values(S.pins).forEach((p) => p.marker.remove());
  S.pins = {}; S.pinsLit = false;
  if (!S.map) return;
  regionCfg().harbours.forEach((h, i) => {
    const el = document.createElement("button");
    el.type = "button"; el.className = "pin loading"; el.style.setProperty("--wait", `${i * 90}ms`);
    el.innerHTML = shape() + '<span class="pin-name"></span>';
    el.onclick = (e) => { e.stopPropagation(); selectHarbour(h.id); };       // a pin is not a tap on the sea
    const holder = document.createElement("div");      // MapLibre positions the holder; the pin keeps its own classes
    holder.appendChild(el);
    const marker = new maplibregl.Marker({ element: holder, anchor: "center" }).setLngLat([h.lon, h.lat]).addTo(S.map);
    S.pins[h.id] = { el, marker, verdict: null };
  });
}

// Pins show the verdict as a shape and a colour; the name and the word are in the label for
// screen readers and appear beside the pin on hover or when it is the chosen harbour.
function renderPins(lit) {
  for (const [id, p] of Object.entries(S.pins)) {
    const v = p.verdict, picked = S.place && S.place.id === id;
    p.el.className = `pin ${v ? "v-" + v : "loading"}${picked ? " picked" : ""}${lit && v ? " lit" : ""}`;
    p.marker.getElement().style.zIndex = picked ? 3 : "";                    // the chosen harbour sits on top of its neighbours
    p.el.querySelector(".shape").innerHTML = SHAPES[v] || SHAPES.SAFE;
    p.el.querySelector(".pin-name").textContent = t(`place.${id}`);
    p.el.setAttribute("aria-label", t(`place.${id}`) + (v ? ` — ${t("verdict." + v)}` : ""));
  }
}

const tlKey = () => `${S.region}|${S.mode}|${S.tripHours}|${S.clock ? S.clock.now : ""}`;

// The trip verdict of every harbour for every departure hour, in one request. With it the pins and
// the slider answer at once while the fisher drags through the hours.
async function loadTimeline() {
  const key = tlKey();
  if (S.tl && S.tl.key === key) return;
  const my = ++S.seq.tl;
  const res = await api("/api/timeline", { region: S.region, trip_hours: S.tripHours, mode: S.mode })
    .catch((e) => { console.error(e); S.lastFail = e; return null; });
  if (my !== S.seq.tl) return;
  S.tl = res && res.ok ? { ...res, key } : null;
}

async function refreshPins() {
  const my = ++S.seq.pins;
  $("map-status").hidden = true;
  S.lastFail = null;                         // only this refresh's own failure decides the message
  if (!S.tl || S.tl.key !== tlKey()) {
    Object.values(S.pins).forEach((p) => { p.verdict = null; });
    renderPins();
    await loadTimeline();
    if (my !== S.seq.pins) return;           // settings changed while waiting: a newer request owns the pins
  }
  const i = S.tl ? S.tl.hours.indexOf(S.departure) : -1;
  if (i >= 0) {
    for (const [id, row] of Object.entries(S.tl.harbours)) if (S.pins[id]) S.pins[id].verdict = row[i];
  } else {                                   // no timeline (or an hour outside it): ask for this one hour
    let res = null;
    try {
      res = await api("/api/assess_region", { region: S.region, departure_local: S.departure,
                                             trip_hours: S.tripHours, mode: S.mode });
    } catch (e) { console.error(e); S.lastFail = e; }
    if (my !== S.seq.pins) return;
    if (!res || !res.ok) { $("map-status").hidden = false; $("map-status").textContent = failText(S.lastFail); }
    else for (const [id, v] of Object.entries(res.harbours)) if (S.pins[id]) S.pins[id].verdict = v.verdict;
  }
  const first = !S.pinsLit;                  // the first verdicts of a region light the coast up, pin by pin
  S.pinsLit = true;
  renderPins(first);
  renderTimeline();
  if (S.wind) S.wind.setHour(S.departure);
}

function selectHarbour(id) {
  S.place = { kind: "harbour", id };
  saveUsual({ place: id });
  if (S.pointMarker) { S.pointMarker.remove(); S.pointMarker = null; }
  renderPins(); renderTimeline(); syncWelcome();
  answerOnMap();
}

function selectPoint(lat, lon) {
  S.place = { kind: "map_point", id: "map_point", lat, lon };
  if (S.pointMarker) S.pointMarker.setLngLat([lon, lat]);
  else {
    const el = document.createElement("div"); el.className = "point-pin";
    S.pointMarker = new maplibregl.Marker({ element: el, anchor: "center" }).setLngLat([lon, lat]).addTo(S.map);
  }
  renderPins(); renderTimeline(); syncWelcome();
  answerOnMap();
}

// A harbour (or a point at sea) was tapped (13 Nov 2026, owner): the answer opens on the map side, in the
// sheet, for the time on the slider and the trip length the pins use (the fisher's own if the chat knows it;
// otherwise the standard one, and the card says it was assumed). Nothing is posted in the chat: the chat
// stays the fisher's own conversation. A problem is shown where the pins' problems are shown.
async function answerOnMap() {
  if (!S.place) return;
  stopPlay();
  const my = ++S.seq.card, opener = document.activeElement;
  if (sheetOpen()) $("card").classList.add("waiting");
  $("map-status").hidden = true;
  try {
    const res = await api("/api/assess", {
      region: S.region, place: S.place.id, departure_local: S.departure, trip_hours: S.tripHours,
      trip_length_given_by_user: S.tripGiven, mode: S.mode, lang: S.lang,
      map_point: S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null });
    if (my !== S.seq.card) return;           // a newer tap won
    if (!res.ok) throw Object.assign(new Error(res.message || "assess failed"), { message_for_fisher: res.message });
    saveLast(res.view);
    openSheet(res.view, opener && opener !== document.body ? opener : null);
  } catch (e) {
    if (my !== S.seq.card) return;
    console.error(e);
    $("card").classList.remove("waiting");
    $("map-status").hidden = false;
    $("map-status").textContent = e.message_for_fisher || failText(e);
  }
}

// quiet = true: the same trip is only being refreshed (clock tick, playing the hours), so the card
// updates in place without its entrance.
async function refreshAll(quiet) {
  await Promise.all([refreshPins(), S.place && S.view ? assessSelected(quiet === true) : Promise.resolve()]).catch(console.error);
}

// ---------------------------------------------------------------- the 48 hours ahead
// One slider over the whole forecast window. Dragging it changes the departure hour: the pins
// recolour at once from the timeline, the wind moves to that hour, and the card follows.
function renderTimeline() {
  const tl = S.tl, box = $("timeline");
  box.hidden = !tl || !tl.hours.length || !S.map;
  if (box.hidden) return;
  const n = tl.hours.length, i = Math.max(0, tl.hours.indexOf(S.departure)), range = $("tl-range");
  range.max = n - 1; range.value = i;
  range.setAttribute("aria-label", t("ui.departure"));
  range.setAttribute("aria-valuetext", when(tl.hours[i]));
  $("tl-when").textContent = when(tl.hours[i]);
  // the ribbon: the chosen harbour's verdict for leaving at each hour
  const row = S.place && S.place.kind === "harbour" ? tl.harbours[S.place.id] : null;
  $("tl-ribbon").innerHTML = tl.hours.map((_, k) => `<i class="${row ? "v-" + row[k] : ""}"></i>`).join("");
  // the sky: daylight between sunrise and sunset; the days: a mark at each midnight
  const start = utc(tl.hours[0]).getTime();
  const at = (iso) => Math.max(0, Math.min(100, ((utc(iso).getTime() - start) / 3600e3 + 0.5) / n * 100));
  $("tl-sky").innerHTML = Object.entries(tl.sun).filter(([, s]) => s).map(([day, s]) => {
    const a = at(`${day}T${s[0]}`), b = at(`${day}T${s[1]}`);
    return b > a ? `<i style="inset-inline-start:${a.toFixed(2)}%;width:${(b - a).toFixed(2)}%"></i>` : "";
  }).join("");
  const dayName = (iso) => { const d = utc(iso); return `${t(`weekday.${(d.getUTCDay() + 6) % 7}`)} ${d.getUTCDate()}`; };
  const marks = Object.keys(tl.sun).map((day) => [at(`${day}T00:00`), dayName(day)]).filter(([x]) => x > 0 && x < 92);
  if (!marks.length || marks[0][0] > 14) marks.unshift([0, dayName(tl.hours[0])]);
  $("tl-days").innerHTML = marks.map(([x, label]) => `<span style="inset-inline-start:${x.toFixed(2)}%">${esc(label)}</span>`).join("");
  renderPlay();
  if (S.wind) S.wind.setHour(S.departure);
}

// While dragging: show the hour at once (label, pins, wind); ask for the card when the hand rests.
function previewHour(i) {
  const tl = S.tl; if (!tl || !tl.hours[i]) return;
  S.departure = tl.hours[i]; S.pickOpen = false;
  $("tl-when").textContent = when(S.departure);
  $("tl-range").setAttribute("aria-valuetext", when(S.departure));
  for (const [id, row] of Object.entries(tl.harbours)) if (S.pins[id]) S.pins[id].verdict = row[i];
  renderPins();
  if (S.wind) S.wind.setHour(S.departure);
  clearTimeout(S.commit);
  S.commit = setTimeout(() => { renderDepartures(); refreshAll(true); }, 220);   // quiet: the slider never posts a message
}

// Play: step through the hours one by one, like watching the day go by. Any touch stops it.
function startPlay() {
  if (!S.tl) return;
  const step = () => {
    const i = S.tl ? S.tl.hours.indexOf(S.departure) : -1;
    if (i < 0 || i >= S.tl.hours.length - 1) { stopPlay(); return; }
    S.departure = S.tl.hours[i + 1]; S.pickOpen = false;
    renderDepartures(); refreshAll(true);
  };
  S.play = setInterval(step, 1100);
  renderPlay(); step();
}
function stopPlay() { if (S.play) { clearInterval(S.play); S.play = null; renderPlay(); } }
function renderPlay() {
  const b = $("tl-play");
  b.innerHTML = icon(S.play ? "pause" : "play");
  b.setAttribute("aria-label", t(S.play ? "ui.pause" : "ui.play"));
}

// ---------------------------------------------------------------- the wind picture (display only)
async function loadWind() {
  if (!S.wind) return;
  const my = ++S.seq.wind;
  S.wind.setField(null);
  const res = await api(`/api/wind?region=${S.region}&mode=${S.mode}`).catch(() => null);
  if (my !== S.seq.wind) return;
  S.wind.setField(res);
  S.wind.setHour(S.departure);
}
function renderWindToggle() {
  const b = $("wind-toggle");
  b.hidden = !S.wind;
  b.setAttribute("aria-pressed", S.windOn);
  b.title = t("map.wind_note");
  if (S.wind) S.wind.setOn(S.windOn);
}

// ---------------------------------------------------------------- the answer card
async function assessSelected(quiet) {
  if (!S.place) return;
  const my = ++S.seq.card;
  const card = $("card");
  if (sheetOpen() && !quiet) card.classList.add("waiting");                 // keep the old answer, dimmed, until the new one is in
  const wait = quiet ? null : addMsg("bot wait", t("ui.checking"));
  try {
    const res = await api("/api/assess", {
      region: S.region, place: S.place.id, departure_local: S.departure, trip_hours: S.tripHours,
      trip_length_given_by_user: S.tripGiven, mode: S.mode, lang: S.lang,
      map_point: S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null });
    if (wait) wait.remove();
    if (my !== S.seq.card) return;           // a newer check was started: never show an older answer
    if (!res.ok) { if (!quiet) { card.classList.remove("waiting"); closeSheet(); showError(res.message); } return; }
    renderCard(res.view, !quiet && sheetOpen() && !calm());     // in the sheet if it is open, else kept ready
    saveLast(res.view);
    // the conversation follows what the card shows (a slider move, a safer time)
    S.context = { place: S.place.id, departure: S.departure, trip_hours: S.tripHours, given: !!S.tripGiven };
    if (!quiet) postAnswer(res.view);
  } catch (e) {
    if (wait) wait.remove();
    if (my !== S.seq.card) return;
    console.error(e);
    if (quiet) return;                       // a slider move or a clock tick never posts a message
    card.classList.remove("waiting"); closeSheet();      // the message goes in the chat, so show the chat
    if (!navigator.onLine) showSaved(); else showError(failText(e));
  }
}

// A problem with a check is said in the conversation, like any answer.
function showError(msg) { addMsg("bot", msg); }

// One gauge: the worst value of the trip on a line that runs from calm to dangerous, with the
// caution and unsafe lines marked. The striped part before the caution line is our own 10% rule.
// The length of the line is our choice for the picture only: a quarter past the unsafe line.
function gaugeHtml(g, n) {
  const name = `<span class="g-name">${icon(PICON[g.param])}${esc(g.label)}</span>`;
  const word = `<span class="sr">${esc(g.level_word)}</span>`;
  if (g.direction === "codes")               // a thunderstorm is forecast or it is not: a shape, no line
    return `<div class="gauge flat v-${g.level}">${name}<span class="g-val">${shape(g.level)}${word}</span></div>`;
  const max = g.direction === "above" ? (g.unsafe ?? g.caution * 1.6) * 1.25 : g.caution * 4;
  const frac = (x) => (g.direction === "above" ? x / max : 1 - Math.min(x, max) / max);   // visibility: lower is worse
  const pct = (x) => (Math.max(0, Math.min(1, frac(x))) * 100).toFixed(1) + "%";
  const cau = pct(g.caution), uns = g.unsafe == null ? "100%" : pct(g.unsafe);
  return `<div class="gauge v-${g.level}${g.unsafe == null ? " no-unsafe" : ""}" style="--near:${pct(g.near)};--caution-at:${cau};--unsafe-at:${uns};--pos:${g.value == null ? "0%" : pct(g.value)};--n:${n}">
      ${name}
      <div class="g-track"><i class="z z-near"></i><i class="z z-caution"></i><i class="z z-unsafe"></i>
        <span class="g-tick" style="inset-inline-start:${cau}">${esc(g.caution_text)}</span>
        ${g.unsafe == null ? "" : `<span class="g-tick after" style="inset-inline-start:${uns}">${esc(g.unsafe_text)}</span>`}
        ${g.value == null ? "" : '<div class="g-run"><b class="g-mark"></b></div>'}
      </div>
      <span class="g-val">${esc(g.text)}${word}</span>
    </div>`;
}

// Hour by hour: one bar per trip hour. Height = how close that hour comes to a caution line (the
// dashed line), colour and shape = that hour's verdict. An hour with no data is drawn striped.
function hoursHtml(v) {
  const bars = v.hours.map((h, i) => `<div class="bar v-${h.verdict}${h.closeness == null ? " none" : ""}" style="--h:${Math.min(h.closeness ?? 1.3, 1.3)};--i:${i}" title="${esc(h.label)}: ${esc(h.verdict_word)}"><i></i></div>`).join("");
  const foot = v.hours.map((h) => `<span class="v-${h.verdict}">${shape(h.verdict)}${esc(h.time.slice(11, 16))}<span class="sr">${esc(h.verdict_word)}</span></span>`).join("");
  return `<div class="hours">
      <div class="hours-head"><strong>${esc(t("ui.hour_by_hour"))}</strong><span>${esc(v.bars_note)}</span></div>
      <div class="table-wrap"><div style="min-width:${v.hours.length * 38}px">
        <div class="bars" aria-hidden="true">${bars}<div class="boat">${icon("boat")}</div></div>
        <div class="bars-foot">${foot}</div>
      </div></div>
    </div>`;
}

// "Trip understood": the trip exactly as it was checked - harbour, leaving, back, length - with a tag that
// says whether the length is the fisher's own or our assumption (feature 1). The Change buttons were removed
// (owner, 13 Nov 2026): the trip is changed by tapping another harbour, moving the slider, or in the chat.
function tripHtml(v) {
  const f = v.trip_fields;
  if (!f) return `<h2>${esc(v.place)}</h2>`;
  const row = (label, value, extra = "") => `<div class="trip-row"><dt>${esc(label)}</dt><dd><span class="val">${value}${extra}</span></dd></div>`;
  const tag = `<span class="tag ${f.given ? "said" : "assumed"}">${esc(t(f.given ? "trip.said_tag" : "trip.assumed_tag"))}</span>`;
  return `<section class="trip-sum" aria-label="${esc(t("trip.understood"))}">
      <h3>${esc(t("trip.understood"))}</h3>
      <dl>
        ${row(t("trip.harbour"), `<strong>${esc(v.place)}</strong>`)}
        ${row(t("trip.leaves"), esc(when(f.departure)))}
        ${row(t("trip.back"), esc(when(f.return)))}
        ${row(t("trip.length"), esc(t("trip.hours", { hours: f.hours })), tag)}
      </dl>
      <p class="small boat-line">${icon("boat")}<span>${esc(v.boat_class)}</span></p>
    </section>`;
}

// Compact answer (feature 3): the verdict, the main reason and the trip first; then what the fisher can do
// (safer times, share); then the other reasons, gauges and hours. The disclaimer, official warnings,
// times and the Open-Meteo credit always stay on the card.
function renderCard(v, reveal = true) {
  const cols = ["wave_height", "wave_period", "wave_direction", "wind_speed", "wind_gusts", "wind_direction", "visibility",
                "weather_code", "rain", "air_temperature", "sea_temperature"];
  const card = $("card"), f = v.trip_fields || {};
  S.view = v;
  card.hidden = false;
  card.className = "card" + (reveal ? " reveal" : "") + (v._saved ? " saved" : "");
  const risky = v.verdict !== "SAFE", rest = v.reasons.slice(1);
  card.innerHTML = `
    <div class="hero v-${v.verdict}">
      ${shape(v.verdict)}
      <div class="hero-text"><div class="word">${esc(v.verdict_word)}</div><p class="advice">${esc(v.advice)}</p></div>
      <button type="button" class="icon-btn listen" ${voiceOn() ? "" : "hidden"} onclick="listenCard(this)" aria-label="${esc(t("ui.listen"))}" title="${esc(t("ui.listen"))}">${icon("volume")}</button>
    </div>
    <div class="card-body">
      <p id="saved-note" class="note warn" ${v._saved ? "" : "hidden"}>${v._saved ? `${icon("hourglass")}<span>${esc(v._saved)}</span>` : ""}</p>
      <p class="main-reason">${icon(PICON[v.reason_icons[0]])}<span>${esc(v.reasons[0] || "")}</span></p>
      ${tripHtml(v)}
      <div class="actions">
        ${risky ? `<button type="button" class="btn primary online-only" data-act="safer">${icon("clock")}<span>${esc(t("safer.button"))}</span></button>` : ""}
        <button type="button" class="btn" data-act="share">${icon("share")}<span>${esc(t("share.button"))}</span></button>
        ${f.live ? `<button type="button" class="btn online-only" data-act="watch" aria-pressed="${!!watchingId(f)}">${icon("bell")}<span>${esc(t(watchingId(f) ? "watch.stop" : "watch.button"))}</span></button>` : ""}
      </div>
      <p id="act-note" class="small" role="status" hidden></p>
      ${f.live ? `<form id="watch-form" class="watch-form" hidden>
        <label for="watch-email">${esc(t("watch.email_label"))}</label>
        <div class="watch-form-row">
          <input id="watch-email" type="email" inputmode="email" autocomplete="email" maxlength="254" placeholder="you@example.com">
          <button type="submit" class="btn primary">${icon("bell")}<span>${esc(t("watch.start"))}</span></button>
        </div>
      </form>` : ""}
      <p id="watch-note" class="note watch-note" role="status" hidden></p>
      <div id="safer" class="safer" aria-live="polite" hidden></div>
      ${rest.length ? `<ul class="reasons">${rest.map((r, i) => `<li>${icon(PICON[v.reason_icons[i + 1]])}<span>${esc(r)}</span></li>`).join("")}</ul>` : ""}
      ${v.gauges ? `<div class="gauges">${v.gauges.map(gaugeHtml).join("")}</div>` : ""}
      ${hoursHtml(v)}
      ${v.sea_cell && v.sea_cell_far ? `<p class="note">${icon("pin")}<span>${esc(v.sea_cell)}</span></p>` : ""}
      ${v.fetch_note ? `<p class="note warn">${icon("hourglass")}<span>${esc(v.fetch_note)}</span></p>` : ""}
      <div class="footer">
        <p class="disclaimer">${esc(v.disclaimer)}</p>
        <p class="warnings">${esc(t("ui.official_warnings"))}:
          ${v.warnings.map((w) => `<a href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.name)}</a>`).join("")}</p>
        <p class="small">${esc(v.data_line)} <a href="https://open-meteo.com/" target="_blank" rel="noopener">${esc(v.attribution)}</a></p>
      </div>
      <details><summary>${esc(t("ui.more_details"))}</summary>
        <p class="small">${esc(v.model_line)}${v.sea_cell && !v.sea_cell_far ? " " + esc(v.sea_cell) : ""}</p>
        ${v.sun ? `<p class="small">${esc(v.sun)}</p>` : ""}
        <div class="table-wrap"><table>
          <tr><th></th>${cols.map((c) => `<th>${esc(t("param." + c))}</th>`).join("")}</tr>
          ${v.hours.map((h) => `<tr><th>${esc(h.time.slice(11, 16))}</th>${cols.map((c) => `<td>${esc(h.values[c] ?? "–")}</td>`).join("")}</tr>`).join("")}
        </table></div>
      </details>
      <button type="button" class="btn to-chat" data-act="tochat">${icon("down")}<span>${esc(t("ui.to_chat"))}</span></button>
    </div>`;
  card.querySelectorAll(".card-body > *").forEach((el, i) => el.style.setProperty("--n", i));
  card.querySelectorAll("[data-act]").forEach((b) => { b.onclick = () => cardAction(b.dataset.act, b); });
  if (f.live && watchingId(f)) { const w = watchList()[watchKey(f)]; watchNote(watchingHead(w), watchingSub(w)); }
  const wf = card.querySelector("#watch-form");
  if (wf) wf.onsubmit = (e) => { e.preventDefault(); startWatch(card.querySelector("[data-act=watch]"), $("watch-email").value.trim()); };
  renderOnline();
  syncWelcome();
}

function cardAction(act, btn) {
  if (act === "safer") checkSafer(btn);
  else if (act === "share") shareTrip(btn);
  else if (act === "watch") toggleWatch(btn);
  else if (act === "tochat") toChat();
}

// "Back to chat": from the bottom of a long card straight to the newest message, ready to type.
function toChat() {
  closeSheet();
  const sc = $("scroll");
  sc.scrollTo({ top: sc.scrollHeight, behavior: calm() ? "auto" : "smooth" });
  $("chat-input").focus({ preventScroll: true });
}

function note(id, text, ic) {
  const el = $(id); if (!el) return;
  el.hidden = !text;
  el.innerHTML = text ? (ic ? `${icon(ic)}<span>${esc(text)}</span>` : esc(text)) : "";
}

// "Check safer departure times" (feature 2): the same place and the same trip length, every departure hour
// left in the forecast window, answered by the existing safest-time check (windows, never one "best" hour).
// It says plainly when there is no SAFE departure, and what not to do. A SAFE window can be checked in one tap.
async function checkSafer(btn) {
  const v = S.view, f = v && v.trip_fields;
  if (!f || !S.place || !S.clock) return;
  const box = $("safer");
  box.hidden = false; box.innerHTML = `<p class="small">${esc(t("ui.checking"))}</p>`;
  btn.disabled = true;
  try {
    const res = await api("/api/safest", {
      region: S.region, place: S.place.id, search_from_local: S.clock.now,
      search_to_local: addHours(S.clock.window_end, -1), trip_hours: f.hours, trip_length_given_by_user: f.given,
      mode: S.mode, lang: S.lang, map_point: S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null });
    if (!res.ok) { box.innerHTML = `<p>${esc(res.message)}</p>`; return; }
    const picks = res.result.safe_windows.slice(0, 4).map(([a]) =>
      `<button type="button" class="chip pick" data-iso="${esc(a)}">${shape("SAFE")}<span>${esc(t("safer.pick", { time: when(a) }))}</span></button>`).join("");
    box.innerHTML = `<p class="small">${esc(t("safer.title", { hours: S.cfg.forecast.window_hours, trip: f.hours }))}</p>
      <p class="safer-line">${esc(res.line)}</p>${picks ? `<div class="chips">${picks}</div>` : ""}`;
    box.querySelectorAll(".pick").forEach((b) => b.onclick = () => {
      stopPlay(); S.tripHours = f.hours; S.tripGiven = f.given; renderTripChips(); S.pickOpen = false; setDeparture(b.dataset.iso);
    });
  } catch (e) { console.error(e); box.innerHTML = `<p>${esc(failText(e))}</p>`; }
  finally { btn.disabled = false; }
}

// Share (feature 7): only when the fisher taps it. The text carries the place, departure and return, the
// verdict, the main reason, the replay label, the disclaimer, the data source and fetch time, and when it
// was checked. The phone's own share sheet is used; nothing is ever sent to anyone automatically.
function shareText(v) {
  const f = v.trip_fields || {};
  const locale = { kn: "kn-IN", ar: "ar-AE-u-nu-latn" }[S.lang] || "en-GB";
  return [`${t("app.title")}: ${v.place} - ${v.verdict_word}`, v.advice,
    f.departure ? `${t("trip.leaves")}: ${when(f.departure)}. ${t("trip.back")}: ${when(f.return)}. ${t("trip.hours", { hours: f.hours })} (${t(f.given ? "trip.said_tag" : "trip.assumed_tag")}).` : v.trip,
    v.reasons[0], v.disclaimer, `${v.data_line} ${v.attribution}`,
    t("share.checked", { time: new Date().toLocaleString(locale, { dateStyle: "medium", timeStyle: "short" }) })]
    .filter(Boolean).join("\n");
}
// ---------------------------------------------------------------- watch this trip (server + notifications)
// Watch this trip (13 Nov 2026, owner): the server checks the trip every 15 minutes until departure and sends a
// phone notification only when the verdict changes, so it works with the page closed (app/watch.py). The page
// only starts and stops it, and remembers which trips this phone is watching (until their departure).
const watchKey = (f) => `${S.region}|${f.place_id}|${f.departure}|${f.hours}`;
function watchList() { try { return JSON.parse(store.get("watches") || "{}"); } catch { return {}; } }
function watchingId(f) { const w = f && watchList()[watchKey(f)]; return w && w.until > Date.now() ? w.id : null; }
const b64urlBytes = (s) => Uint8Array.from(atob((s + "===".slice((s.length + 3) % 4)).replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));

// The watch's note under the buttons: the bell in its own column, a short line in bold, then (when watching)
// the reminder that a notification can be late. An empty text hides it.
function watchNote(text, sub) {
  const el = $("watch-note"); if (!el) return;
  el.hidden = !text;
  el.innerHTML = text ? `${icon("bell")}<span><strong>${esc(text)}</strong>${sub ? `<span class="note-sub">${esc(sub)}</span>` : ""}</span>` : "";
}

// The line under "Watching this trip...": the reminder, and where emails go (or that they can't).
function watchingSub(w, extra = []) {
  const parts = [...extra, t("watch.on_note")];
  if (w && w.email) parts.push(t("watch.on_email", { email: w.email }));
  return parts.join(" ");
}
// The bold line names how the fisher will be told: a notification, an email, or both.
function watchingHead(w) {
  const push = !w || w.push !== false;
  return t(push && w && w.email ? "watch.on_both" : push ? "watch.on" : "watch.on_by_email");
}
function setWatchButton(btn, f) {
  if (!btn) return;
  const on = !!watchingId(f);
  btn.setAttribute("aria-pressed", on);
  btn.querySelector("span").textContent = t(on ? "watch.stop" : "watch.button");
}

// "Watch this trip": not watching yet -> open the form (email optional, the last one filled in);
// watching -> stop.
async function toggleWatch(btn) {
  const f = S.view && S.view.trip_fields;
  if (!f) return;
  const id = watchingId(f);
  if (!id) {
    const form = $("watch-form");
    if (!form) return;
    form.hidden = !form.hidden;
    if (!form.hidden) { const box = $("watch-email"); box.value = store.get("watch_email") || ""; box.focus(); }
    return;
  }
  btn.disabled = true;
  try {
    await api("/api/watch/stop", { id });
    const all = watchList(); delete all[watchKey(f)]; store.set("watches", JSON.stringify(all));
    watchNote("");
  } catch (e) { console.error(e); watchNote(t("watch.failed")); }
  finally { btn.disabled = false; setWatchButton(btn, f); }
}

// Start watching: phone notifications when this browser can have them, and email when one is given. Either is
// enough, so an iPhone without the Home Screen app can still watch by email (13 Nov 2026).
async function startWatch(btn, email) {
  const f = S.view && S.view.trip_fields;
  if (!f) return;
  const form = $("watch-form"), go = form && form.querySelector("button");
  if (go) go.disabled = true;
  let sub = null, why = "";
  try {
    if (email) store.set("watch_email", email);          // kept on this phone only, to fill the box next time
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) why = t("watch.unsupported");
      else if (await Notification.requestPermission() !== "granted") why = t("watch.denied");
      else {
        const k = await api("/api/push/key");
        if (!k.ok) throw new Error("no push key");
        const reg = await navigator.serviceWorker.ready;
        sub = (await reg.pushManager.getSubscription())
          || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64urlBytes(k.key) });
      }
    } catch (e) { console.warn(e); why = t("watch.failed"); sub = null; }
    if (!sub && !email) { watchNote(why || t("watch.failed")); return; }
    const point = f.place_id === "map_point" && S.place && S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null;
    const res = await api("/api/watch", { subscription: sub ? sub.toJSON() : null, email: email || null, region: S.region,
      place: f.place_id, departure_local: f.departure, trip_hours: f.hours, trip_length_given_by_user: !!f.given,
      lang: S.lang, map_point: point });
    if (!res.ok) { watchNote(res.message || t("watch.failed")); return; }
    const all = watchList();
    const w = { id: res.id, until: new Date(f.departure).getTime() + 3600e3,   // the server watches through the departure hour
                email: res.email ? email : null, push: !!sub };
    all[watchKey(f)] = w; store.set("watches", JSON.stringify(all));
    if (form) form.hidden = true;
    const extra = [];
    if (email && !res.email) extra.push(t("watch.email_off"));
    watchNote(watchingHead(w), watchingSub(w, extra));
  } catch (e) { console.error(e); watchNote(t("watch.failed")); }
  finally { if (go) go.disabled = false; setWatchButton(btn, f); }
}

async function shareTrip() {
  const text = shareText(S.view);
  try {
    if (navigator.share) { await navigator.share({ title: t("app.title"), text }); return; }
  } catch (e) { if (e.name === "AbortError") return; }
  try { await navigator.clipboard.writeText(text); note("act-note", t("share.copied")); setTimeout(() => note("act-note", ""), 5000); }
  catch {                                    // no share sheet and no clipboard: show the text to copy by hand
    const el = $("act-note"); el.hidden = false;
    el.innerHTML = `<textarea class="share-text" readonly>${esc(text)}</textarea>`;
    el.querySelector("textarea").select();
  }
}

// ---------------------------------------------------------------- offline (feature 6)
// The page itself, its text and the last answer are kept on the phone. Offline, the last answer is shown
// with its age in a warning box; if it is older than the stale limit (6 hours) it is not shown at all,
// the same rule the verdict code uses for old data. Chat, voice, the map and new checks are switched off.
const LAST = "last-answer";
function saveLast(view) {
  try { store.set(LAST, JSON.stringify({ view, region: S.region, mode: S.mode, lang: S.lang, saved: Date.now() })); } catch { /* full */ }
}
function showSaved() {
  let last = null;
  try { last = JSON.parse(store.get(LAST) || "null"); } catch { last = null; }
  if (!last || last.region !== S.region) { showError(t("offline.none")); return; }
  const minutes = Math.round((Date.now() - last.saved) / 60000), limit = (S.cfg.forecast.stale_after_hours || 6);
  if (minutes > limit * 60) { showError(t("offline.too_old", { hours: limit })); return; }
  const saved = new Date(last.saved).toTimeString().slice(0, 5);
  const view = { ...last.view, _saved: t("offline.saved", { time: saved, minutes }) };
  renderCard(view, false);
  postAnswer(view, view._saved);
}
function renderOnline() {
  const off = !navigator.onLine;
  const tape = $("offline-tape");
  if (tape) { tape.hidden = !off; tape.textContent = off ? t("offline.banner") : ""; }
  document.body.classList.toggle("offline", off);
  const send = $("chat-form") && $("chat-form").querySelector("button[type=submit]");
  if (send && !S.asking) send.disabled = off;
  document.querySelectorAll(".online-only, .listen").forEach((b) => { b.disabled = off; });
}

// ---------------------------------------------------------------- conversation
// One question at a time (typed or spoken): a second question waits until the first is answered, so an
// older answer can never arrive last and replace a newer card and context (audit 13 Nov 2026, item 6).
function setAsking(on) {
  S.asking = on;
  document.body.classList.toggle("asking", on);
  const send = $("chat-form").querySelector("button[type=submit]");
  if (send) send.disabled = on;
  $("examples").querySelectorAll(".chip").forEach((b) => { b.disabled = on; });
}

async function sendChat(text) {
  text = (text || "").trim(); if (!text) return;
  if (S.asking || S.voice.busy || S.voice.rec || !navigator.onLine) return;   // still answering, or offline
  setAsking(true);
  $("chat-input").value = ""; syncComposer();
  addMsg("user", text);
  S.history.push({ role: "user", content: text });
  const wait = addMsg("bot wait", t("ui.checking"));
  const my = S.seq.chat;                     // changes only when the region or mode is switched
  try {
    const res = await api("/api/chat", { history: S.history, lang: S.lang, region: S.region, mode: S.mode,
      map_point: S.place && S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null, context: S.context,
      page: pageState() });
    wait.remove();
    if (my !== S.seq.chat) return;           // region or mode switched while waiting: this answer is out of date
    showAnswer(res);
    S.history.push({ role: "assistant", content: res.reply });
  } catch (e) { wait.remove(); if (my === S.seq.chat) addMsg("bot", e.offline ? t("error.server_down") : t("chat.llm_unavailable")); console.error(e); }
  finally { setAsking(false); }
}

// One answer in the conversation: a coloured badge and the short spoken version.
// The full answer (reasons, times, sources) is the card above.
function showAnswer(res, note) {
  const card = res.cards && res.cards[res.cards.length - 1];
  // With a card on screen the chat shows the short spoken answer; the card holds the details.
  // A single trip: short bullet points. Lists (all harbours, safer times) and talk: as spoken.
  const text = (res.chat_text || (card || res.region ? res.spoken : res.reply)) + (note ? "\n\n" + note : "");
  // safer times: no badge, because the card is an example trip, not the one the fisher planned
  addMsg("bot", text, card && !res.no_badge ? card.result.verdict : null, res.provider, card ? card.view : res.region || null);
  if (res.context !== undefined) S.context = res.context;
  if (card) showChatCard(card); else if (res.region) showRegionCard(res.region);
  // "Want me to watch this trip?" stays open for the next message only. When the fisher gives the email, the
  // server starts the watch itself and confirms; the page only remembers it (button and note on the card).
  S.watchOffer = res.watch_offer || null;
  if (res.watch_offer && !S.watchSkip.includes(res.watch_offer.key)) S.watchSkip.push(res.watch_offer.key);
  if (res.watching) rememberWatch(res.watching);
}

// A watch the conversation started (13 Nov 2026): kept like one started from the card's button.
function rememberWatch(w) {
  const [place_id, departure, hours] = w.key.split("|");
  const f = { place_id, departure, hours: Number(hours) };
  store.set("watch_email", w.email);
  const all = watchList();
  all[watchKey(f)] = { id: w.id, until: new Date(departure).getTime() + 3600e3, email: w.email, push: false };
  store.set("watches", JSON.stringify(all));
  const open = S.view && S.view.trip_fields;
  if (open && watchKey(open) === watchKey(f)) {
    setWatchButton(document.querySelector("[data-act=watch]"), open);
    watchNote(watchingHead(all[watchKey(f)]), watchingSub(all[watchKey(f)]));
  }
}

// "Which harbours are safe at 2 pm?": every harbour by verdict. The map pins move to the same time;
// the list opens in the sheet; tapping a harbour there checks it.
function showRegionCard(v) {
  stopPlay();
  S.departure = v.departure; S.tripHours = v.trip_hours; S.tripGiven = v.trip_length_given_by_user;
  renderDepartures(); renderTripChips();
  S.seq.card++;                              // an older single-harbour card in flight must not replace this one
  if (sheetOpen()) renderRegion(v);
  refreshPins();
  if (isPhone()) setTab("answer");
}
function renderRegion(v) {
  const card = $("card");
  card.hidden = false; card.className = "card" + (calm() ? "" : " reveal");
  card.innerHTML = `
    <div class="card-body region-card">
      <h2>${esc(v.heading)}</h2>
      ${v.groups.map((g) => `<div class="rgroup">
        <span class="badge v-${g.verdict}">${shape(g.verdict)}${esc(g.word)}</span>
        <div class="chips">${g.places.map((p) => `<button type="button" class="chip" data-id="${esc(p.id)}">${esc(p.name)}</button>`).join("")}</div>
      </div>`).join("")}
      <p class="small">${esc(t("ui.region_tap"))}</p>
      <div class="footer">
        <p class="disclaimer">${esc(v.disclaimer)}</p>
        <p class="warnings">${esc(t("ui.official_warnings"))}:
          ${v.warnings.map((w) => `<a href="${esc(w.url)}" target="_blank" rel="noopener">${esc(w.name)}</a>`).join("")}</p>
        <p class="small">${esc(v.data_line)} <a href="https://open-meteo.com/" target="_blank" rel="noopener">${esc(v.attribution)}</a></p>
      </div>
      <details><summary>${esc(t("ui.more_details"))}</summary><p class="small">${esc(v.model_line)}</p></details>
      <button type="button" class="btn to-chat">${icon("down")}<span>${esc(t("ui.to_chat"))}</span></button>
    </div>`;
  card.querySelectorAll(".card-body > *").forEach((el, i) => el.style.setProperty("--n", i));
  card.querySelectorAll(".rgroup .chip").forEach((b) => b.onclick = () => { closeSheet(); selectHarbour(b.dataset.id); });
  card.querySelector(".to-chat").onclick = toChat;
}

// The chat's answer becomes the page's selection: place, departure and trip length move to match,
// so the card, the pins and the controls always describe the same trip.
function showChatCard(card) {
  const r = card.result;
  stopPlay();
  if (r.place.kind === "harbour") {
    S.place = { kind: "harbour", id: r.place.id };
    if (S.pointMarker) { S.pointMarker.remove(); S.pointMarker = null; }
    saveUsual({ place: r.place.id });
  }
  if (r.trip_length_given_by_user) saveUsual({ hours: r.trip_hours });
  S.departure = r.departure; S.tripHours = r.trip_hours; S.tripGiven = r.trip_length_given_by_user;
  renderDepartures(); renderTripChips();
  S.seq.card++;                              // any older card request in flight must not replace this one
  renderCard(card.view, sheetOpen() && !calm());   // ready for "See the full answer"; shown now only if open
  saveLast(card.view);
  if (isPhone()) setTab("answer");
  refreshPins();
}

// The way into the full answer (13 Nov 2026, owner's pick): one small bar per trip hour, coloured by that
// hour's verdict and as tall as the hour comes to a caution line (the card's own hour bars, in small), the
// trip's times, and "Why CAUTION? ›". At a glance it shows where in the trip the risk is. A list of all
// harbours, or a safer-time answer (no verdict of its own), says "Full answer ›".
function answerLink(view, verdict) {
  const label = verdict ? t("chat.why", { verdict: t("verdict." + verdict) }) : t("ui.full_answer");
  const go = `<span class="peek-go">${esc(label)}<span class="peek-chev" aria-hidden="true">›</span></span>`;
  const f = view.trip_fields;
  if (!view.hours || !view.hours.length || !f) return `<button type="button" class="see-card peek">${go}</button>`;
  const bars = view.hours.map((h) => `<i class="v-${h.verdict}${h.closeness == null ? " none" : ""}" style="--h:${Math.min(h.closeness ?? 1.3, 1.3)}"></i>`).join("");
  const times = `${f.departure.slice(11, 16)} → ${f.return.slice(11, 16)}`;
  return `<button type="button" class="see-card peek" aria-label="${esc(label)} ${esc(times)}">` +
    `<span class="peek-bars" aria-hidden="true">${bars}</span><span class="peek-time" aria-hidden="true">${esc(times)}</span>${go}</button>`;
}

// One message in the thread. cls: "user", "user voice" (said into the mic), "bot", or "bot wait"
// (the three dots while the answer is worked out). An answer with a card gets the verdict badge and
// the hour strip that opens the full answer, where the reasons and the numbers are.
function addMsg(cls, text, verdict, provider, view) {
  const mine = cls.startsWith("user"), wait = cls.includes("wait");
  const div = document.createElement("div");
  div.className = `row ${mine ? "user" : "bot"}${wait ? " typing" : ""}`;
  const clock = new Date().toTimeString().slice(0, 5);
  const body = wait
    ? `<span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><span class="sr">${esc(text)}</span>`
    : (verdict ? `<span class="badge v-${verdict}">${shape(verdict)}${esc(t("verdict." + verdict))}</span>` : "") +
      `<span class="text">${cls.includes("voice") ? icon("mic") : ""}${esc(text)}</span>` +
      (view ? answerLink(view, verdict) : "") + `<span class="meta"><time>${clock}</time></span>`;
  div.innerHTML = (mine ? "" : `<span class="avatar" aria-hidden="true">${avatarHtml()}</span>`) + `<div class="bubble">${body}</div>`;
  const see = div.querySelector(".see-card");
  if (see) see.onclick = () => openSheet(view, see);      // each bubble opens its own answer
  if (provider) div.title = t("ui.answered_by", { provider });   // for the team, not in the way of fishers
  $("chat-log").appendChild(div);
  syncWelcome();
  const sc = $("scroll");                    // bring the new message into view inside the panel (never scroll the page)
  if (div.offsetTop + div.offsetHeight > sc.scrollTop + sc.clientHeight || div.offsetTop < sc.scrollTop)
    sc.scrollTo({ top: div.offsetTop + div.offsetHeight - sc.clientHeight + 16, behavior: calm() ? "auto" : "smooth" });
  return div;
}

// The bot's picture in the thread: the app's own mark.
function avatarHtml() { return '<img src="/static/img/logo.svg" alt="" width="28" height="28">'; }


// What is selected on screen; the chat uses it for anything the question leaves out.
function pageState() {
  // watch_*: the conversation can offer to watch a trip (13 Nov 2026). The server needs the trip it offered, the
  // email this phone remembers from an earlier watch, and the trips not to offer again (offered, or watched).
  const watched = Object.entries(watchList()).filter(([, w]) => w.until > Date.now())
    .map(([k]) => k.split("|").slice(1).join("|"));
  return { place: S.place && S.place.kind === "harbour" ? S.place.id : null,
           watch_offer: S.watchOffer, watch_email: store.get("watch_email") || null,
           watch_skip: [...S.watchSkip, ...watched] };
}

// ---------------------------------------------------------------- voice
// Tap the mic, speak, tap again. ElevenLabs turns speech into text; the same chat and code answer;
// the voice reads the reviewed spoken template. The card and the short answer always appear too.
const voiceOn = () => !!(S.voice.status && S.voice.status.available && S.voice.status.languages.includes(S.lang)
  && navigator.mediaDevices && window.MediaRecorder);

function renderMic() {
  const b = $("mic"); if (!b) return;
  b.hidden = !voiceOn();
  const state = S.voice.rec ? "rec" : S.voice.busy ? "busy" : S.voice.speaking ? "speaking" : "";
  b.className = `mic ${state}${S.voice.metered ? "" : " flat"}`;
  const label = t({ rec: "ui.mic_stop", busy: "ui.checking", speaking: "ui.speaking" }[state] || "ui.mic_start");
  b.querySelector(".mic-label").textContent = label;
  b.setAttribute("aria-label", label); b.title = label;
  document.querySelectorAll(".listen").forEach((x) => { x.hidden = !voiceOn(); });
  syncComposer(state);
}

// Empty input: the round voice button. Text in it: the send arrow. While listening or speaking, the
// voice button stays (tap to stop) and the input says what is happening.
function syncComposer(state) {
  const input = $("chat-input"), mic = $("mic"), send = $("chat-form").querySelector(".send");
  if (state === undefined) state = S.voice.rec ? "rec" : S.voice.busy ? "busy" : S.voice.speaking ? "speaking" : "";
  const typed = !!input.value.trim();
  mic.hidden = !voiceOn() || (typed && !state);
  send.hidden = !mic.hidden;
  input.placeholder = t({ rec: "ui.mic_stop", busy: "ui.voice_working", speaking: "ui.speaking" }[state] || "ui.ask_placeholder");
}

// The orb and the five bars move with the real sound: the fisher's voice while recording, the
// answer while it is spoken. If the browser cannot measure the sound, the orb just breathes.
function audioCtx() {
  try {
    S.voice.ctx = S.voice.ctx || new (window.AudioContext || window.webkitAudioContext)();
    if (S.voice.ctx.state === "suspended") S.voice.ctx.resume();
  } catch { S.voice.ctx = null; }
  return S.voice.ctx;
}
function watchLevel(source) {
  const an = S.voice.ctx.createAnalyser(); an.fftSize = 64; an.smoothingTimeConstant = 0.72;
  source.connect(an);
  const data = new Uint8Array(an.frequencyBinCount), mic = $("mic"), bars = [...mic.querySelectorAll(".mic-bars i")];
  const bins = [2, 4, 6, 9, 13], my = ++S.voice.meter;
  S.voice.metered = true; mic.classList.remove("flat");
  (function tick() {
    if (my !== S.voice.meter) return;
    an.getByteFrequencyData(data);
    let sum = 0; for (let i = 1; i < 16; i++) sum += data[i];
    mic.style.setProperty("--lvl", Math.min(1, sum / 15 / 150).toFixed(3));
    bars.forEach((el, k) => el.style.setProperty("--b", Math.max(0.15, Math.min(1, data[bins[k]] / 200)).toFixed(3)));
    requestAnimationFrame(tick);
  })();
}
function stopLevel() {
  S.voice.meter++; S.voice.metered = false;
  const mic = $("mic"); if (!mic) return;
  mic.style.setProperty("--lvl", 0);
  mic.querySelectorAll(".mic-bars i").forEach((el) => el.style.removeProperty("--b"));
}

function onMic() {
  if (S.voice.busy || S.asking || !navigator.onLine) return;   // still answering, or no connection
  if (S.voice.speaking) { stopAudio(); return; }
  toggleMic();
}

async function toggleMic() {
  if (S.voice.rec) { S.voice.rec.stop(); return; }
  stopAudio();
  const ctx = audioCtx();                    // made on this tap, so the browser lets it run
  // Open the server's connections to ElevenLabs and the model while the fisher speaks (saves ~1 s).
  fetch("/api/voice/warm", { method: "POST" }).catch(() => {});
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch (e) { addMsg("bot", t("voice.mic_denied")); return; }
  const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((x) => MediaRecorder.isTypeSupported(x)) || "";
  const rec = new MediaRecorder(stream, type ? { mimeType: type } : {});
  const chunks = [];
  rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  rec.onstop = () => {
    stream.getTracks().forEach((tr) => tr.stop());
    clearTimeout(S.voice.timer);
    stopLevel();
    S.voice.rec = null; renderMic();
    sendVoice(new Blob(chunks, { type: rec.mimeType || "audio/webm" }));
  };
  S.voice.rec = rec;
  rec.start();
  if (ctx) { try { watchLevel(ctx.createMediaStreamSource(stream)); } catch (e) { console.warn(e); } }
  S.voice.timer = setTimeout(() => { if (rec.state === "recording") rec.stop(); }, (S.voice.status.max_record_seconds || 20) * 1000);
  renderMic();
}

async function sendVoice(blob) {
  const epoch = S.seq.chat;
  const wait = addMsg("bot wait", t("ui.voice_working"));
  S.voice.busy = true; renderMic();
  const fd = new FormData();
  fd.append("audio", blob, blob.type.includes("mp4") ? "question.mp4" : "question.webm");
  fd.append("region", S.region); fd.append("lang", S.lang); fd.append("mode", S.mode);
  fd.append("history", JSON.stringify(S.history)); fd.append("context", JSON.stringify(S.context));
  fd.append("map_point", JSON.stringify(S.place && S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null));
  fd.append("page", JSON.stringify(pageState()));
  try {
    const res = await (await fetch("/api/voice/ask", { method: "POST", body: fd })).json();
    wait.remove();
    if (epoch !== S.seq.chat) return;        // region or mode switched while waiting
    if (!res.ok) { addMsg("bot", res.message); return; }
    if (res.transcript) {
      addMsg("user voice", res.transcript);
      S.history.push({ role: "user", content: res.transcript }, { role: "assistant", content: res.reply });
    }
    showAnswer(res, res.voice_error);
    if (res.audio_url) playAudio(res.audio_url);
  } catch (e) { wait.remove(); addMsg("bot", t("voice.unavailable")); console.error(e); }
  finally { S.voice.busy = false; renderMic(); }
}

// "Listen" on the card: the server works the answer out again and reads its spoken template.
async function listenCard(btn) {
  if (!S.place) return;
  stopAudio();
  audioCtx();
  btn.disabled = true;
  try {
    const res = await api("/api/voice/say", {
      region: S.region, place: S.place.id, departure_local: S.departure, trip_hours: S.tripHours,
      trip_length_given_by_user: S.tripGiven, mode: S.mode, lang: S.lang,
      map_point: S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null });
    if (res.audio_url) playAudio(res.audio_url); else addMsg("bot", res.message || t("voice.unavailable"));
  } catch (e) { addMsg("bot", t("voice.unavailable")); console.error(e); }
  finally { btn.disabled = false; }
}

// The audio streams: it starts as soon as the first part arrives from ElevenLabs.
function playAudio(url) {
  stopAudio();
  const a = new Audio(url);
  const done = () => { if (S.voice.audio === a) { S.voice.audio = null; S.voice.speaking = false; stopLevel(); renderMic(); } };
  a.onplaying = () => { if (S.voice.audio === a) { S.voice.speaking = true; renderMic(); } };
  a.onended = done;
  a.onerror = () => { if (S.voice.audio === a) { done(); addMsg("bot", t("voice.unavailable")); } };
  S.voice.audio = a;
  // Measure the sound for the orb only when the audio engine is really running; otherwise the
  // answer plays the ordinary way, so the voice is never lost for the sake of a picture.
  const ctx = S.voice.ctx;
  if (ctx && ctx.state === "running") {
    try { const src = ctx.createMediaElementSource(a); src.connect(ctx.destination); watchLevel(src); } catch (e) { console.warn(e); }
  }
  a.play().catch((e) => { if (e.name !== "AbortError") console.error(e); });
}

function stopAudio() {
  if (S.voice.audio) { S.voice.audio.pause(); S.voice.audio = null; }
  S.voice.speaking = false;
  if (!S.voice.rec) stopLevel();
  renderMic();
}

// ---------------------------------------------------------------- how we decide
async function openHow() {
  const h = await api(`/api/how?lang=${S.lang}`);
  $("how-body").innerHTML = `
    <p><strong>${esc(h.intro)}</strong></p>
    <p>${esc(h.boat)}</p>
    <div class="table-wrap"><table>
      <tr><th>${esc(t("how.table_param"))}</th><th>${esc(t("how.table_caution"))}</th><th>${esc(t("how.table_unsafe"))}</th><th>${esc(t("how.table_source"))}</th></tr>
      ${h.rows.map((r) => `<tr><td><strong>${esc(r.param)}</strong></td><td>${esc(r.caution)}</td><td>${esc(r.unsafe)}</td>
        <td>${r.sources.map((s) => `<div><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>
          <div class="src">${esc(s.where)} — ${esc(s.note)}</div></div>`).join("")}</td></tr>`).join("")}
    </table></div>
    <h3>${esc(t("how.rules_title"))}</h3>
    <ul>${h.rules.map((r, i) => `<li>${h.own_rules[i] ? '<span class="own">★</span>' : ""}${esc(r)}</li>`).join("")}</ul>
    <p class="small">${esc(t("map.wind_note"))}</p>`;
  $("how").showModal();
}

init().catch((e) => { console.error(e); document.body.insertAdjacentHTML("afterbegin", `<p class="card-error">Could not start: ${esc(e.message)}</p>`); });
