// Voice mode (13 Nov 2026): a hands-free conversation with Sea Safe, opened from the waveform button.
// You speak; it notices when you start and stop; your words go to ElevenLabs speech-to-text, then to the same
// chat as typing (the code still decides every verdict); the reviewed spoken answer is read aloud and the
// orb moves with her voice; then it listens again. The transcript shows above the orb, and the whole
// conversation, with its verdict cards, is in the chat when voice mode is closed.
//
// Background noise is kept out in four ways:
//   1. the browser's own noise suppression, echo cancellation and gain control on the microphone;
//   2. speech is detected in the voice band only (a 300-3400 Hz filter feeds the level meter);
//   3. the "room level" is learnt while nobody speaks, and speech must be clearly louder than it;
//   4. sound must last at least a quarter of a second to count, so a bang or a click is ignored.
// Talking over her (13 Nov 2026, owner; layered like the Jessa voice agent's barge-in): while she speaks the
// microphone is still measured. Speech clearly louder than usual (BARGE_OVER) for BARGE_MS stops her and is
// recorded. If it was short (NOISE_MS), or the server hears no words or only her own words coming back through
// the speaker, it was noise and she carries on from a second before where she stopped. Otherwise it is a new
// question. Echo cancellation keeps most of her voice out of the microphone; the server's echo check the rest.
//
// No dead air (13 Nov 2026, owner's choice; the idea comes from the Jessa voice agent's opener cache and
// thinking sounds): she greets you the moment voice mode opens, says "Okay." or "Right." the instant you stop
// talking, and "One moment." if the answer is not back after WAIT_MS. These are fixed reviewed lines, rendered
// once and served from the cache (/api/voice/lines), so they play without waiting for anything.
const VoiceMode = (() => {
  Object.assign(ICONS, {
    micoff: '<path d="m2 2 20 20"/><path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2"/><path d="M5 10v2a7 7 0 0 0 12 5"/><path d="M15 9.34V5a3 3 0 0 0-5.68-1.33"/><path d="M9 9v3a3 3 0 0 0 5.12 2.12"/><path d="M12 19v3"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  });

  const SPEECH_MS = 250;         // this long above the room level before it counts as speech
  const END_MS = 900;            // this long quiet after speech: the question is over
  const IDLE_RESTART_MS = 12000; // nothing said: start a fresh recording (keeps files small)
  const MIN_LEVEL = 0.012;       // never treat anything quieter than this as speech
  const OVER_ROOM = 3.2;         // speech must be this many times the learnt room level
  const WAIT_MS = 1500;          // no answer yet this long after the question: "One moment."
  const BARGE_MS = 300;          // talking over her this long stops her
  const BARGE_OVER = 2.2;        // ...and it must be this many times louder than ordinary speech detection
  const BARGE_MIN = 0.03;        // never stop her for anything quieter than this
  const NOISE_MS = 500;          // less speech than this after stopping her: a cough or a bang, she carries on
  const REWIND_S = 1;            // she carries on from this many seconds before where she stopped

  const V = { open: false, state: "idle", muted: false, stream: null, src: null, an: null, rec: null, chunks: [],
              floor: 0.008, speechMs: 0, quietMs: 0, heard: false, recStart: 0, last: 0, raf: 0,
              audio: null, outAn: null, epoch: 0, buf: null,
              lines: {}, ready: {}, clip: null, ackNext: 0,
              saying: "", bargeMs: 0, resume: null };
  let el = null;

  function build() {
    const panel = document.querySelector(".panel");
    panel.insertAdjacentHTML("beforeend", `
      <div id="vm" class="vm" role="dialog" aria-modal="true" hidden>
        <div id="vm-log" class="vm-log" aria-live="polite"></div>
        <div class="vm-stage">
          <div id="vm-orb" class="vm-orb" aria-hidden="true"><i></i><i></i></div>
          <p id="vm-state" class="vm-state" role="status"></p>
          <p id="vm-hint" class="vm-hint"></p>
        </div>
        <form id="vm-form" class="composer vm-bar">
          <input id="vm-input" autocomplete="off">
          <button type="button" id="vm-mute" class="vm-btn"></button>
          <button type="button" id="vm-close" class="vm-btn vm-x"></button>
        </form>
      </div>`);
    el = { root: $("vm"), log: $("vm-log"), orb: $("vm-orb"), state: $("vm-state"), hint: $("vm-hint"),
           form: $("vm-form"), input: $("vm-input"), mute: $("vm-mute"), close: $("vm-close") };
    el.close.onclick = close;
    el.mute.onclick = toggleMute;
    el.form.onsubmit = (e) => { e.preventDefault(); const q = el.input.value.trim(); if (q) { el.input.value = ""; ask({ text: q }); } };
    document.addEventListener("keydown", (e) => { if (V.open && e.key === "Escape") close(); });
  }

  function texts() {
    el.root.setAttribute("aria-label", t("vm.listening"));
    el.input.placeholder = t("vm.type");
    el.close.innerHTML = icon("x"); el.close.setAttribute("aria-label", t("vm.close")); el.close.title = t("vm.close");
    el.mute.innerHTML = icon(V.muted ? "micoff" : "mic");
    el.mute.setAttribute("aria-label", t(V.muted ? "vm.unmute" : "vm.mute")); el.mute.title = t(V.muted ? "vm.unmute" : "vm.mute");
    el.mute.classList.toggle("muted", V.muted);
    el.hint.textContent = el.log.children.length ? "" : t("vm.hint");
    setState(V.state);
  }

  function setState(s) {
    V.state = s;
    el.root.dataset.state = s;
    el.state.textContent = { listening: t("vm.listening"), thinking: t("vm.thinking"), speaking: t("vm.speaking"),
                             muted: t("vm.muted") }[s] || "";
  }

  // ---------------------------------------------------------------- open and close
  async function open() {
    if (!el) build();
    if (V.open) return;
    V.open = true; V.epoch++;
    if (isPhone()) setTab("answer");
    stopAudio();
    el.root.hidden = false;
    el.log.innerHTML = "";
    el.root.classList.remove("has-log");
    texts();
    setState("thinking");
    const lines = loadLines();                   // the greeting and the gap lines, rendered while the mic starts
    const ctx = audioCtx();                      // made on the tap itself, so the browser lets it run
    try {
      V.stream = await navigator.mediaDevices.getUserMedia({ audio: {
        echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
    } catch (e) {
      line("bot", t("voice.mic_denied"));
      V.muted = true; texts(); setState("muted");
      return;
    }
    if (ctx) {                                   // the level meter listens to the voice band only
      V.src = ctx.createMediaStreamSource(V.stream);
      const band = ctx.createBiquadFilter(); band.type = "bandpass"; band.frequency.value = 1000; band.Q.value = 0.6;
      V.an = ctx.createAnalyser(); V.an.fftSize = 1024;
      V.src.connect(band); band.connect(V.an);
      V.buf = new Float32Array(V.an.fftSize);
    }
    V.floor = 0.008; V.last = performance.now();
    V.raf = requestAnimationFrame(tick);
    if (V.muted) setMicOn(false);
    greet(lines, V.epoch);                       // then it listens (or shows "muted")
  }

  // ---------------------------------------------------------------- lines said without waiting
  // Asked for when voice mode opens, so the server renders them now and they play at once later.
  function loadLines() {
    const lang = S.lang;
    if (!V.lines[lang]) {
      V.lines[lang] = fetch(`/api/voice/lines?lang=${encodeURIComponent(lang)}`).then((r) => r.json())
        .then((L) => {
          if (!L || !L.ok) return null;
          [L.greeting, L.wait, ...L.acks].forEach((x) => { const a = new Audio(); a.preload = "auto"; a.src = x.url; });
          V.ready[lang] = L;
          return L;
        })
        .catch((e) => { console.warn(e); delete V.lines[lang]; return null; });
    }
    return V.lines[lang];
  }
  const within = (p, ms) => Promise.race([p, new Promise((r) => setTimeout(() => r(null), ms))]);

  // The greeting, said as voice mode opens. If it is not ready in time, she just listens.
  async function greet(lines, epoch) {
    const L = await within(lines, 2500);
    if (epoch !== V.epoch || !V.open || V.state !== "thinking") return;    // a typed question came first
    if (!L) { listen(); return; }
    line("bot", L.greeting.text);
    speak(L.greeting.url, epoch, L.greeting.text);   // listens again when she has finished
  }

  // Her voice moves the orb: the audio goes through an analyser on its way to the speakers.
  function hook(a) {
    const ctx = S.voice.ctx;
    if (!ctx || ctx.state !== "running") return null;
    try {
      const src = ctx.createMediaElementSource(a), an = ctx.createAnalyser(); an.fftSize = 1024;
      src.connect(an); an.connect(ctx.destination);
      return an;
    } catch (e) { console.warn(e); return null; }
  }

  // One short fixed line; resolves when it has finished (or could not play).
  function playClip(url, epoch) {
    return new Promise((resolve) => {
      if (epoch !== V.epoch || !V.open) { resolve(); return; }
      const a = new Audio(url);
      V.clip = a; V.outAn = hook(a);
      const end = () => { if (V.clip === a) { V.clip = null; V.outAn = null; } resolve(); };
      a.onended = end; a.onerror = end;
      a.play().catch(end);
    });
  }

  // The gap after a question: "Okay." or "Right." at once (they take turns, so never the same twice running),
  // then "One moment." if the answer is not back after WAIT_MS. Returns settle(): call it when the answer is
  // in; it cancels anything not yet started and resolves when the line playing now has finished, so the
  // answer never cuts a line off.
  function fillGap(epoch) {
    const L = V.ready[S.lang];
    if (!L) { loadLines(); return () => Promise.resolve(); }
    let over = false;
    let playing = playClip(L.acks[V.ackNext++ % L.acks.length].url, epoch);
    const timer = setTimeout(() => {
      if (!over) playing = playing.then(() => (over ? null : playClip(L.wait.url, epoch)));
    }, WAIT_MS);
    return () => { over = true; clearTimeout(timer); return playing; };
  }

  function close() {
    if (!V.open) return;
    V.open = false; V.epoch++;
    stopRecording(true);
    if (V.audio) { V.audio.pause(); V.audio = null; }
    if (V.resume) { V.resume.a.pause(); V.resume = null; }
    if (V.clip) { const c = V.clip; c.pause(); c.onended(); }
    if (V.stream) V.stream.getTracks().forEach((tr) => tr.stop());
    V.stream = null; V.an = null; V.outAn = null;
    cancelAnimationFrame(V.raf);
    el.root.hidden = true;
    S.voice.busy = false; renderMic();
    const sc = $("scroll"); sc.scrollTo({ top: sc.scrollHeight, behavior: "auto" });   // the conversation is in the chat
    $("mic").focus({ preventScroll: true });
  }

  function setMicOn(on) { if (V.stream) V.stream.getTracks().forEach((tr) => { tr.enabled = on; }); }

  function toggleMute() {
    V.muted = !V.muted;
    setMicOn(!V.muted);
    texts();
    if (V.muted) { stopRecording(true); if (V.state === "listening") setState("muted"); }
    else if (V.state === "muted" || V.state === "listening") listen();
  }

  // ---------------------------------------------------------------- listening
  function listen() {
    if (!V.open || V.muted || !V.stream || !window.MediaRecorder) { if (V.muted) setState("muted"); return; }
    stopRecording(true);
    const type = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((x) => MediaRecorder.isTypeSupported(x)) || "";
    const rec = new MediaRecorder(V.stream, type ? { mimeType: type } : {});
    V.rec = rec; V.chunks = []; V.heard = false; V.speechMs = 0; V.quietMs = 0; V.recStart = performance.now();
    rec.ondataavailable = (e) => { if (e.data.size) V.chunks.push(e.data); };
    rec.onstop = () => {
      if (V.rec === rec) V.rec = null;
      if (rec._discard || !V.open) return;
      if (V.heard && V.resume && V.speechMs < NOISE_MS) resumeSpeech();     // talked over her briefly: noise
      else if (V.heard) ask({ blob: new Blob(V.chunks, { type: rec.mimeType || "audio/webm" }),
                              interrupted: V.resume ? V.resume.text : "" });
      else if (V.resume) resumeSpeech();
      else listen();                             // nothing said: keep listening with a fresh recording
    };
    rec.start(250);
    setState("listening");
  }

  function stopRecording(discard) {
    const rec = V.rec; if (!rec) return;
    rec._discard = !!discard; V.rec = null;
    if (rec.state !== "inactive") rec.stop();
  }

  // Every frame: the level of the voice (yours while listening, hers while speaking) moves the orb; while
  // listening it also decides when a question starts and ends.
  function tick(now) {
    if (!V.open) return;
    const dt = Math.min(100, now - V.last); V.last = now;
    let level = 0;
    if (V.state === "speaking" && V.audio && V.an && !V.muted) {          // is the fisher talking over her?
      const r = rms(V.an);
      if (r > Math.max(BARGE_MIN, V.floor * OVER_ROOM * BARGE_OVER)) V.bargeMs += dt;
      else V.bargeMs = Math.max(0, V.bargeMs - dt * 2);
      if (V.bargeMs >= BARGE_MS) interrupt();
    }
    if (V.state === "speaking" && V.outAn) level = Math.min(1, rms(V.outAn) * 4.5);
    else if (V.clip && V.outAn) level = Math.min(1, rms(V.outAn) * 4.5);     // "Okay." / "One moment."
    else if (V.an && (V.state === "listening")) {
      const r = rms(V.an);
      const loud = r > Math.max(MIN_LEVEL, V.floor * OVER_ROOM);
      if (loud) { V.speechMs += dt; V.quietMs = 0; if (V.speechMs >= SPEECH_MS) V.heard = true; }
      else {
        if (V.heard) V.quietMs += dt;
        else {
          V.speechMs = Math.max(0, V.speechMs - dt * 2);
          V.floor = V.floor * 0.97 + Math.min(r, V.floor * 2) * 0.03;      // learn the room while nobody speaks
        }
      }
      level = V.heard ? Math.min(1, r * 6) * 0.6 : 0;
      const recFor = now - V.recStart;
      if (V.rec && V.heard && (V.quietMs >= END_MS || recFor > (S.voice.status.max_record_seconds || 20) * 1000)) stopRecording(false);
      else if (V.rec && !V.heard && recFor > IDLE_RESTART_MS) stopRecording(false);
    }
    const prev = parseFloat(el.orb.style.getPropertyValue("--lvl")) || 0;
    el.orb.style.setProperty("--lvl", (prev * 0.6 + level * 0.4).toFixed(3));
    V.raf = requestAnimationFrame(tick);
  }

  // She is stopped and the fisher's words are recorded (the speech so far already counts as heard). Her line is
  // kept, paused, in case it was only noise.
  function interrupt() {
    const a = V.audio; if (!a) return;
    V.bargeMs = 0;
    a.pause();
    V.resume = { a, an: V.outAn, text: V.saying, epoch: V.epoch };
    V.audio = null; V.outAn = null;
    listen();
    V.heard = true; V.speechMs = SPEECH_MS;
  }

  // It was noise: she carries on from a second before where she stopped.
  function resumeSpeech() {
    const r = V.resume; V.resume = null;
    if (!r || r.epoch !== V.epoch || !V.open) { listen(); return; }
    stopRecording(true);
    V.audio = r.a; V.outAn = r.an; V.bargeMs = 0;
    try { r.a.currentTime = Math.max(0, r.a.currentTime - REWIND_S); } catch (e) { /* not seekable: from here */ }
    r.a.play().catch(() => { if (V.audio === r.a) { V.audio = null; V.outAn = null; } listen(); });
  }

  function rms(an) {
    const buf = V.buf && V.buf.length === an.fftSize ? V.buf : (V.buf = new Float32Array(an.fftSize));
    an.getFloatTimeDomainData(buf);
    let sum = 0; for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
    return Math.sqrt(sum / buf.length);
  }

  // ---------------------------------------------------------------- one turn
  async function ask({ blob, text, interrupted = "" }) {
    const epoch = V.epoch;
    stopRecording(true);
    if (V.audio) { V.audio.pause(); V.audio = null; V.outAn = null; }      // a typed question during the greeting
    if (!interrupted && V.resume) { V.resume.a.pause(); V.resume = null; } // a typed question: her line is done
    setState("thinking");
    // no "Okay." after talking over her: it may only have been noise, and then she simply carries on
    const settle = interrupted ? () => Promise.resolve() : fillGap(epoch);
    S.voice.busy = true; renderMic();
    let res = null;
    try {
      if (blob) {
        const fd = new FormData();
        fd.append("audio", blob, blob.type.includes("mp4") ? "question.mp4" : "question.webm");
        fd.append("region", S.region); fd.append("lang", S.lang); fd.append("mode", S.mode);
        fd.append("history", JSON.stringify(S.history.slice(-12))); fd.append("context", JSON.stringify(S.context));
        fd.append("map_point", JSON.stringify(S.place && S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null));
        fd.append("page", JSON.stringify(pageState()));
        fd.append("interrupted", interrupted);
        res = await (await fetch("/api/voice/ask", { method: "POST", body: fd })).json();
      } else {
        res = await api("/api/voice/text", { question: text, region: S.region, lang: S.lang, mode: S.mode,
          history: S.history.slice(-12), context: S.context,
          map_point: S.place && S.place.kind === "map_point" ? [S.place.lat, S.place.lon] : null, page: pageState() });
      }
    } catch (e) { console.error(e); res = { ok: false, message: t("voice.unavailable") }; }
    S.voice.busy = false; renderMic();
    if (epoch !== V.epoch || !V.open) return;
    await settle();                              // let "Okay." / "One moment." finish first
    if (epoch !== V.epoch || !V.open) return;
    if (res.ok && res.resume) { resumeSpeech(); return; }   // no words, or her own words heard back: noise
    if (V.resume) { V.resume.a.pause(); V.resume = null; }  // a real question: her old line is not finished
    if (!res.ok) { line("bot", res.message || t("voice.unavailable")); listen(); return; }
    const card = res.cards && res.cards[res.cards.length - 1];
    if (res.transcript) {
      line("user", res.transcript);
      addMsg(blob ? "user voice" : "user", res.transcript);
      S.history.push({ role: "user", content: res.transcript }, { role: "assistant", content: res.reply });
    }
    line("bot", res.chat_text || res.spoken, card && !res.no_badge ? card.result.verdict : null,   // she says res.spoken
         card ? card.view : res.region || null);
    showAnswer(res, res.voice_error);            // the chat gets the answer and the card, as for typing
    if (res.audio_url) speak(res.audio_url, epoch, res.spoken); else listen();
  }

  function speak(url, epoch, saying = "") {
    const a = new Audio(url);
    V.audio = a; V.saying = saying; V.bargeMs = 0;
    V.outAn = hook(a);
    const done = () => { if (V.audio !== a) return; V.audio = null; V.outAn = null; if (epoch === V.epoch && V.open) listen(); };
    a.onplaying = () => { if (V.audio === a) setState("speaking"); };
    a.onended = done;
    a.onerror = () => { done(); };
    a.play().catch((e) => { console.warn(e); done(); });
  }

  // ---------------------------------------------------------------- the transcript above the orb
  function line(who, text, verdict, view) {
    if (!text) return;
    const div = document.createElement("div");
    div.className = `vm-line ${who}`;
    div.innerHTML = (verdict ? `<span class="badge v-${verdict}">${shape(verdict)}${esc(t("verdict." + verdict))}</span>` : "") +
      `<span>${esc(text)}</span>` + (view ? answerLink(view, verdict) : "");
    const see = div.querySelector(".see-card");
    if (see) see.onclick = () => openSheet(view, see);         // the sheet opens above voice mode
    el.log.appendChild(div);
    el.root.classList.add("has-log");
    el.hint.textContent = "";
    el.log.scrollTo({ top: el.log.scrollHeight, behavior: calm() ? "auto" : "smooth" });
  }

  return { open, close, get isOpen() { return V.open; }, _state: V };
})();
