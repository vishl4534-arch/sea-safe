// The wind picture: thin streaks that drift over the sea the way the forecast wind blows.
// DISPLAY ONLY. It reads /api/wind (a grid of wind speed and direction) and draws; it never
// touches a verdict. The streaks change colour at the same three lines the verdict uses for wind.
//
// How it works, in four steps:
//   1. Each streak is a point on the map (longitude, latitude).
//   2. Every frame we look up the wind at that point (between the four nearest grid values),
//      move the point a little that way, and draw a short line from the old place to the new one.
//   3. Old lines fade a little every frame, so each point leaves a tail.
//   4. A streak that is old, off the screen, or over land starts again somewhere on the sea.
class WindPicture {
  constructor(map, lines) {
    this.map = map;
    this.lines = lines;                 // {near, caution, unsafe} in km/h, from /api/config
    this.field = null;                  // the grid from /api/wind
    this.hour = 0;                      // which hour of the grid is shown
    this.on = true;
    this.still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.parts = [];
    this.sea = null;                    // coarse grid of the screen: 1 = sea, 0 = land
    this.cell = 24;                     // size of one sea-grid square, in pixels
    this.clearNext = true;
    this.slow = 0;
    this.last = 0;

    this.canvas = document.createElement("canvas");
    this.canvas.className = "wind-canvas";
    this.canvas.setAttribute("aria-hidden", "true");
    const box = map.getCanvasContainer();
    box.insertBefore(this.canvas, map.getCanvas().nextSibling);   // above the map, below the harbour pins
    this.ctx = this.canvas.getContext("2d");
    this.setTheme();

    map.on("move", () => { this.clearNext = true; });
    map.on("resize", () => this.resize());
    map.on("idle", () => { this.readSea(); if (this.still) this.drawStill(); });
    document.addEventListener("visibilitychange", () => { if (!document.hidden) this.kick(); });
    this.resize();
    this.kick();
  }

  setField(field) { this.field = field && field.ok ? field : null; this.parts = []; this.clearNext = true; this.afterChange(); }
  setHour(iso) {
    if (!this.field) return;
    const i = this.field.hours.indexOf(iso);
    if (i >= 0 && i !== this.hour) { this.hour = i; this.afterChange(); }
  }
  setOn(on) { this.on = on; this.clearNext = true; this.canvas.style.opacity = on ? "1" : "0"; this.afterChange(); }
  afterChange() { if (this.still) this.drawStill(); else this.kick(); }

  resize() {
    const box = this.map.getContainer(), dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    this.w = box.clientWidth; this.h = box.clientHeight;
    this.canvas.width = Math.round(this.w * dpr); this.canvas.height = Math.round(this.h * dpr);
    this.canvas.style.width = this.w + "px"; this.canvas.style.height = this.h + "px";
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // fewer streaks on a small or modest phone, so the map stays smooth
    const modest = this.w < 700 || (navigator.hardwareConcurrency || 8) <= 4;
    this.count = Math.round(Math.min(modest ? 420 : 1300, (this.w * this.h) / (modest ? 1500 : 800)));
    this.parts = []; this.clearNext = true; this.sea = null;
  }

  // Which parts of the screen are sea? Ask the map on a coarse grid, once each time it comes to rest.
  readSea() {
    if (!this.map.getLayer("water")) return;
    const t0 = performance.now(), c = this.cell;
    const cols = Math.ceil(this.w / c), rows = Math.ceil(this.h / c), grid = new Uint8Array(cols * rows);
    for (let r = 0; r < rows; r++) for (let q = 0; q < cols; q++) {
      const hit = this.map.queryRenderedFeatures([q * c + c / 2, r * c + c / 2], { layers: ["water"] });
      grid[r * cols + q] = hit.length ? 1 : 0;
    }
    this.sea = { grid, cols, rows, cell: c };                         // the grid remembers the square size it was read with
    if (performance.now() - t0 > 180 && c < 48) this.cell = c * 2;   // slow device: a coarser grid next time
  }
  isSea(x, y) {
    if (!this.sea) return true;
    const q = Math.floor(x / this.sea.cell), r = Math.floor(y / this.sea.cell);
    if (q < 0 || r < 0 || q >= this.sea.cols || r >= this.sea.rows) return false;
    return this.sea.grid[r * this.sea.cols + q] === 1;
  }

  // Wind at a point: mix the four grid values around it by how close each one is.
  windAt(lon, lat) {
    const f = this.field;
    const gx = (lon - f.west) / (f.east - f.west) * (f.nx - 1), gy = (lat - f.south) / (f.north - f.south) * (f.ny - 1);
    if (gx < 0 || gy < 0 || gx > f.nx - 1 || gy > f.ny - 1) return null;
    const x0 = Math.min(Math.floor(gx), f.nx - 2), y0 = Math.min(Math.floor(gy), f.ny - 2), fx = gx - x0, fy = gy - y0;
    const U = f.u[this.hour], V = f.v[this.hour], i = y0 * f.nx + x0;
    const mix = (A) => {
      const a = A[i], b = A[i + 1], c = A[i + f.nx], d = A[i + f.nx + 1];
      if (a == null || b == null || c == null || d == null) return null;
      return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy;
    };
    const u = mix(U), v = mix(V);
    return u == null || v == null ? null : [u, v];
  }

  spawn(p) {
    for (let tries = 0; tries < 6; tries++) {
      const x = Math.random() * this.w, y = Math.random() * this.h;
      if (!this.isSea(x, y)) continue;
      const ll = this.map.unproject([x, y]);
      p.lon = ll.lng; p.lat = ll.lat; p.age = 0; p.life = 50 + Math.random() * 70; p.ok = true;
      return;
    }
    p.ok = false;                       // no sea found this time; try again next frame
  }

  // One step for every streak. Lines are collected in three groups (calm, caution, unsafe) so each
  // colour is drawn in one go.
  step(scale) {
    const groups = [[], [], []], L = this.lines;
    for (const p of this.parts) {
      if (!p.ok || p.age++ > p.life) { this.spawn(p); continue; }
      const wind = this.windAt(p.lon, p.lat);
      if (!wind) { this.spawn(p); continue; }
      const a = this.map.project([p.lon, p.lat]);
      const x = a.x + wind[0] * scale, y = a.y - wind[1] * scale;        // screen y grows downward
      if (x < 0 || y < 0 || x > this.w || y > this.h || !this.isSea(x, y)) { this.spawn(p); continue; }
      const speed = Math.hypot(wind[0], wind[1]);
      groups[speed >= L.unsafe ? 2 : speed >= L.near ? 1 : 0].push(a.x, a.y, x, y);
      const ll = this.map.unproject([x, y]);
      p.lon = ll.lng; p.lat = ll.lat;
    }
    return groups;
  }

  // The streak colours come from the page's theme (calm, near the line, over it): light streaks on the dark
  // map, dark streaks on the light one (13 Nov 2026). Called again when the mode is switched.
  setTheme() {
    const css = getComputedStyle(document.documentElement);
    this.rgb = ["--wind-1", "--wind-2", "--wind-3"].map((n, i) => css.getPropertyValue(n).trim() || ["232,232,232", "242,189,58", "255,112,112"][i]);
    this.clearNext = true;
    if (this.still && this.field) this.drawStill();
  }

  paint(groups, alpha) {
    const ctx = this.ctx, colours = this.rgb.map((c) => `rgba(${c},${alpha})`);
    ctx.lineWidth = 1.15; ctx.lineCap = "round";
    groups.forEach((g, k) => {
      if (!g.length) return;
      ctx.strokeStyle = colours[k]; ctx.beginPath();
      for (let i = 0; i < g.length; i += 4) { ctx.moveTo(g[i], g[i + 1]); ctx.lineTo(g[i + 2], g[i + 3]); }
      ctx.stroke();
    });
  }

  fill() { while (this.parts.length < this.count) { const p = {}; this.spawn(p); p.age = Math.random() * 60; this.parts.push(p); } }
  speedScale() { return 0.05 * Math.pow(2, (this.map.getZoom() - 7) * 0.35); }   // pixels per frame for each km/h

  kick() { if (!this.running && !this.still) { this.running = true; requestAnimationFrame((t) => this.frame(t)); } }

  frame(now) {
    if (!this.on || !this.field || document.hidden) { this.ctx.clearRect(0, 0, this.w, this.h); this.running = false; return; }
    const ctx = this.ctx;
    if (this.clearNext) { ctx.clearRect(0, 0, this.w, this.h); this.clearNext = false; }
    else {                                                   // fade what is already drawn: this makes the tails
      ctx.globalCompositeOperation = "destination-in";
      ctx.fillStyle = "rgba(0,0,0,0.92)"; ctx.fillRect(0, 0, this.w, this.h);
      ctx.globalCompositeOperation = "source-over";
    }
    this.fill();
    this.paint(this.step(this.speedScale()), 0.7);
    // If frames are slow for a while, halve the streaks rather than let the page stutter.
    if (this.last && now - this.last > 40) { if (++this.slow > 90 && this.count > 150) { this.count = Math.round(this.count / 2); this.parts.length = this.count; this.slow = 0; } }
    else this.slow = Math.max(0, this.slow - 1);
    this.last = now;
    requestAnimationFrame((t) => this.frame(t));
  }

  // Reduced motion: no movement. Draw each streak once as a short still line.
  drawStill() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);
    if (!this.on || !this.field) return;
    const full = this.count;
    this.parts = []; this.count = Math.max(80, Math.round(full / 2)); this.fill(); this.count = full;
    const scale = this.speedScale();
    for (let i = 0; i < 26; i++) this.paint(this.step(scale), 0.55);
  }
}
