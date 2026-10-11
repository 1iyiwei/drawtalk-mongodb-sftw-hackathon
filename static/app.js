// DrawTalk Harness front end: capture vector strokes, name characters, send commands, play keyframes.
const SVGNS = "http://www.w3.org/2000/svg";
const FPS = 30;
const $ = (id) => document.getElementById(id);
const canvas = $("canvas");

const app = {
  project: null, scenes: [], sceneId: null, entities: {}, behaviors: [],
  mode: "ink", inkStrokes: [], motionStroke: null, playing: false, lastResult: null,
};

// ------------------------------------------------------------------ api
async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {});
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

function status(text, kind = "") { const s = $("status"); s.textContent = text; s.className = "status " + kind; }

function toast(text) {
  let t = document.querySelector(".toast");
  if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.append(t); }
  t.textContent = text; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 3500);
}

// ------------------------------------------------------------------ state
const scene = () => app.scenes.find((s) => s._id === app.sceneId);
const DEFAULT = { rot: 0, sx: 1, sy: 1, op: 1 };

function endStates(sc) {
  const states = {};
  for (const [id, s] of Object.entries(sc.start_state || {})) states[id] = { ...DEFAULT, ...s };
  [...(sc.timeline || [])].sort((a, b) => a.start + a.duration - (b.start + b.duration)).forEach((c) => (states[c.actor] = c.end_state));
  return states;
}

async function load(projectName) {
  const st = await api(`/api/state?project=${encodeURIComponent(projectName)}`);
  app.project = st.project; app.scenes = st.scenes; app.behaviors = st.behaviors;
  app.entities = Object.fromEntries(st.entities.map((e) => [e._id, e]));
  if (!app.sceneId || !scene()) app.sceneId = app.scenes[app.scenes.length - 1]._id;
  $("project-name").textContent = app.project.name;
  renderAll();
}

// ------------------------------------------------------------------ rendering
function el(tag, attrs = {}, parent) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (parent) parent.append(n);
  return n;
}

function pathD(pts) {
  if (!pts.length) return "";
  if (pts.length < 3) return "M" + pts.map((p) => `${p[0]},${p[1]}`).join(" L");
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2;
    d += ` Q${pts[i][0]},${pts[i][1]} ${mx},${my}`;
  }
  const l = pts[pts.length - 1];
  return d + ` L${l[0]},${l[1]}`;
}

function setTransform(g, s) {
  g.setAttribute("transform", `translate(${s.x},${s.y}) rotate(${s.rot || 0}) scale(${s.sx ?? 1},${s.sy ?? 1})`);
  g.setAttribute("opacity", s.op ?? 1);
}

function renderEntities(states) {
  const layer = $("entities-layer"); layer.replaceChildren();
  const labels = $("labels-layer"); labels.replaceChildren();
  for (const [id, s] of Object.entries(states)) {
    const e = app.entities[id]; if (!e) continue;
    const g = el("g", { id: "g-" + id, class: "entity" }, layer);
    for (const st of e.strokes) el("path", { d: pathD(st), class: "ink" }, g);
    setTransform(g, s);
    // name label below the character; kept outside the animated group so it never flips or rotates
    const lb = el("text", { x: s.x, y: s.y + e.bbox[3] * Math.abs(s.sy ?? 1) + 16, class: "label" }, labels);
    lb.textContent = e.name;
  }
}

function flash(id) {
  const g = $("g-" + id); if (!g) return;
  g.classList.add("flash"); setTimeout(() => g.classList.remove("flash"), 900);
}

function clipNumbers(timeline) {
  const starts = [...new Set(timeline.map((c) => c.start.toFixed(3)))].sort((a, b) => a - b);
  const seen = {};
  return timeline.map((c) => {
    const n = starts.indexOf(c.start.toFixed(3)) + 1;
    seen[n] = (seen[n] || 0) + 1;
    return n + "′".repeat(seen[n] - 1);
  });
}

function renderPaths(sc) {
  const layer = $("paths-layer"); layer.replaceChildren();
  const nums = clipNumbers(sc.timeline || []);
  (sc.timeline || []).forEach((c, i) => {
    const pts = c.path?.points || [];
    if (pts.length > 1) el("path", { d: pathD(pts), class: "clip-path" }, layer);
    const p = pts[0] || [c.end_state.x, c.end_state.y];
    const b = el("g", { class: "badge", transform: `translate(${p[0] - 18 + (nums[i].length > 1 ? 12 : 0)},${p[1] - 26})` }, layer);
    el("circle", { r: 10 }, b);
    el("text", {}, b).textContent = nums[i];
  });
}

function renderClipList(sc) {
  const ol = $("clip-list"); ol.replaceChildren();
  const nums = clipNumbers(sc.timeline || []);
  if (!sc.timeline?.length) { ol.innerHTML = '<li class="muted" style="border:0">No clips yet.</li>'; return; }
  sc.timeline.forEach((c, i) => {
    const li = document.createElement("li");
    const actor = app.entities[c.actor]?.name || "?";
    const target = c.target ? ` → ${app.entities[c.target]?.name}` : "";
    li.innerHTML = `<span class="num">${nums[i]}</span>${actor} · <b>${c.behavior_id}</b> v${c.behavior_version}${target}
      <span class="muted">(${c.duration.toFixed(1)} s)</span>`;
    const chips = document.createElement("div"); chips.className = "chips";
    for (const [k, v] of Object.entries(c.params || {})) {
      const ch = document.createElement("span"); ch.className = "chip";
      ch.textContent = `${k} ${+v.toFixed(1)}: ${c.param_sources?.[k] || "default"}`;
      chips.append(ch);
    }
    if (c.route === "fast") { const f = document.createElement("span"); f.className = "chip fast"; f.textContent = "⚡ no LLM"; chips.append(f); }
    const del = document.createElement("button"); del.className = "del"; del.title = "Delete clip (counts as a correction)"; del.textContent = "✕";
    del.onclick = async () => {
      await api("/api/clips/delete", { project_id: app.project._id, scene_id: sc._id, clip_id: c.clip_id });
      sc.timeline = sc.timeline.filter((x) => x.clip_id !== c.clip_id);
      status("clip deleted"); renderAll();
    };
    li.prepend(del); li.append(chips); ol.append(li);
  });
}

function renderScenes() {
  const strip = $("scene-strip"); strip.replaceChildren();
  for (const s of app.scenes) {
    const b = document.createElement("button");
    b.textContent = s.title; b.className = s._id === app.sceneId ? "on" : "";
    b.onclick = () => { app.sceneId = s._id; renderAll(); };
    strip.append(b);
  }
}

function renderEntityList(sc) {
  const ul = $("entity-list"); ul.replaceChildren();
  const ids = Object.keys(sc.start_state || {});
  if (!ids.length) { ul.innerHTML = '<li class="muted">Draw in Ink mode, then name it.</li>'; return; }
  for (const id of ids) {
    const e = app.entities[id]; if (!e) continue;
    const li = document.createElement("li");
    li.innerHTML = `<b>${e.name}</b> <span class="muted">${(e.traits || []).join(", ")}</span>`;
    const del = document.createElement("button"); del.className = "del"; del.textContent = "✕"; del.title = "Remove from this scene (and its clips)";
    del.onclick = async () => {
      if (!confirm(`Remove “${e.name}” and its clips from this scene?`)) return;
      await api("/api/scenes/remove-entity", { project_id: app.project._id, scene_id: sc._id, entity_id: id });
      delete sc.start_state[id]; sc.timeline = (sc.timeline || []).filter((c) => c.actor !== id);
      status(`removed “${e.name}”`); renderAll();
    };
    li.prepend(del); ul.append(li);
  }
}

function renderBehaviors() {
  const ul = $("behavior-list"); ul.replaceChildren();
  if (!app.behaviors.length) { ul.innerHTML = '<li class="muted">Empty: teach it by drawing and talking.</li>'; return; }
  for (const b of app.behaviors) {
    const li = document.createElement("li");
    const st = b.stats || {};
    li.innerHTML = `<b>${b.behavior_id}</b> v${b.version} <span class="muted">${b.description}</span>
      <div class="chips"><span class="chip">used ${st.uses || 0}</span><span class="chip">accepted ${st.accepted || 0}</span>${st.corrected ? `<span class="chip">corrected ${st.corrected}</span>` : ""}${b.version > 1 ? `<span class="chip new" title="${(b.diff || []).join("\n").replace(/"/g, "&quot;")}">v${b.version}: ${b.change_summary || b.reason}</span>` : ""}</div>`;
    ul.append(li);
  }
}

function renderTrace(res) {
  const t = $("trace"); t.classList.remove("muted");
  if (!res) { t.textContent = "Nothing yet."; t.classList.add("muted"); return; }
  const tr = res.trace;
  const route = tr.route === "fast" ? '<span class="chip fast">⚡ fast path, no LLM</span>' : `<span class="chip">LLM ${tr.llm?.model} · ${tr.llm?.latency_ms} ms</span>`;
  t.innerHTML = `<div class="msg">${res.message}</div><div class="chips">${route}<span class="chip">total ${tr.total_ms} ms</span></div>
    <ul>${tr.steps.map((s) => `<li>${s}</li>`).join("")}</ul>
    <div class="muted">Written to MongoDB:</div>
    <ul>${res.written.map((w) => `<li><code>${w.collection}</code> ${w.what}</li>`).join("")}</ul>
    <details><summary>raw decision</summary><pre>${JSON.stringify(tr.decision ?? tr, null, 1)}</pre></details>`;
}

function renderProposal(p) {
  const box = $("proposal");
  if (!p) { box.hidden = true; box.replaceChildren(); return; }
  const nPass = p.checks.filter((c) => c.pass).length;
  const who = p.actor ? `${p.actor}'s ` : "";
  box.hidden = false;
  box.innerHTML = `
    <div class="ptitle">Refine <b>${p.behavior_id}</b> v${p.from_version} → v${p.from_version + 1}: ${p.change_summary}</div>
    <pre class="diff">${p.diff.map((l) => l.replace(/&/g, "&amp;").replace(/</g, "&lt;")).join("\n") || "(no visible change)"}</pre>
    <div class="checks">Regression replay: <b>${nPass}/${p.checks.length}</b> existing clip(s) still end where the story needs them
      <ul>${p.checks.map((c) => `<li>${c.pass ? "✓" : "✗"} ${c.scene} · ${c.actor} (v${c.version}, ${c.outcome}) · ${c.duration_before}s → ${c.duration_after}s${c.pass ? "" : ` · end moved ${c.end_deviation_px}px, will stay on v${c.version}`}</li>`).join("")}</ul></div>
    <div class="scope">Scope guess: <span class="chip">${p.scope_guess === "behavior" ? "everywhere" : "only this time"}</span>
      <span class="muted">${p.scope_reason}</span></div>
    <div class="pbuttons">
      <button data-scope="behavior" class="${p.scope_guess === "behavior" ? "primary" : ""}">All ${who}${p.behavior_id} (v${p.from_version + 1})</button>
      <button data-scope="instance" class="${p.scope_guess === "instance" ? "primary" : ""}">Only this time</button>
      <button data-scope="cancel">Cancel</button>
    </div>`;
  box.querySelectorAll("button").forEach((b) => (b.onclick = () => decideProposal(p, b.dataset.scope)));
}

async function decideProposal(p, scope) {
  status("applying…", "busy");
  try {
    const r = await api("/api/refine/confirm", { proposal_id: p._id, scope });
    renderProposal(null);
    await load(app.project.name);
    if (scope === "cancel") return status("refinement cancelled");
    toast(scope === "behavior"
      ? `${p.behavior_id} v${r.version} saved · ${r.upgraded.length} clip(s) upgraded`
      : `applied to this clip only (${p.behavior_id} stays v${p.from_version})`);
    status(`${r.upgraded.length} clip(s) updated`);
    const ids = new Set(r.upgraded.filter((u) => u.scene_id === app.sceneId).map((u) => u.clip_id));
    if (ids.size) await play(scene().timeline || [], { fromStart: true });
    renderAll();
  } catch (err) { status(err.message, "err"); }
}

function renderAll() {
  const sc = scene();
  document.body.classList.toggle("motion", app.mode === "motion");
  renderScenes(); renderEntities(endStates(sc)); renderPaths(sc); renderClipList(sc); renderEntityList(sc); renderBehaviors();
  renderInk();
}

function renderInk() {
  const layer = $("ink-layer"); layer.replaceChildren();
  for (const s of app.inkStrokes) el("path", { d: pathD(s), class: "ink" }, layer);
  if (app.motionStroke) el("path", { d: pathD(app.motionStroke), class: "motion-stroke" }, layer);
  if (app.lasso) el("path", { d: pathD(app.lasso) + " Z", class: "lasso" }, layer);
}

// ------------------------------------------------------------------ playback
function play(clips, { fromStart = false } = {}) {
  return new Promise((resolve) => {
    const sc = scene();
    if (!clips.length) return resolve();
    const t0 = Math.min(...clips.map((c) => c.start));
    const tEnd = Math.max(...clips.map((c) => c.start + c.duration));
    if (fromStart) renderEntities(Object.fromEntries(Object.entries(sc.start_state).map(([k, v]) => [k, { ...DEFAULT, ...v }])));
    const fx = $("fx-layer"); fx.replaceChildren();
    const pending = clips.flatMap((c) => (c.events || []).map((e) => ({ ...e, t: e.t + c.start - t0 })));
    app.playing = true;
    document.body.classList.add("playing");
    const started = performance.now();
    function frame(now) {
      const t = (now - started) / 1000;
      for (const c of clips) {
        const g = $("g-" + c.actor); if (!g) continue;
        const local = t - (c.start - t0);
        if (local < 0) continue;
        const f = local * FPS, i = Math.min(Math.floor(f), c.frames.length - 1), j = Math.min(i + 1, c.frames.length - 1), u = f - Math.floor(f);
        const a = c.frames[i], b = c.frames[j];
        const v = a.map((x, k) => (i === j ? x : x + (b[k] - x) * u));
        setTransform(g, { x: v[0], y: v[1], rot: v[2], sx: v[3], sy: v[4], op: v[5] });
      }
      while (pending.length && pending[0].t <= t) spawnGlyph(pending.shift());
      pending.sort((a, b) => a.t - b.t);
      if (t < tEnd - t0 + 0.05) requestAnimationFrame(frame);
      else { app.playing = false; document.body.classList.remove("playing"); resolve(); }
    }
    pending.sort((a, b) => a.t - b.t);
    requestAnimationFrame(frame);
  });
}

function spawnGlyph(e) {
  const t = el("text", { x: e.x + 14, y: e.y - 20, class: "glyph" }, $("fx-layer"));
  t.textContent = e.glyph;
  t.animate([{ transform: "translate(0,0)", opacity: 1 }, { transform: `translate(8px,${-e.rise}px)`, opacity: 0 }],
    { duration: e.fade * 1000, easing: "ease-out", fill: "forwards" }).onfinish = () => t.remove();
}

// ------------------------------------------------------------------ input
function svgPoint(evt) {
  const pt = canvas.createSVGPoint(); pt.x = evt.clientX; pt.y = evt.clientY;
  const p = pt.matrixTransform(canvas.getScreenCTM().inverse());
  return [Math.round(p.x * 10) / 10, Math.round(p.y * 10) / 10];
}

let drawing = null, drawStart = 0;
canvas.addEventListener("pointerdown", (e) => {
  if (app.playing) return;
  canvas.setPointerCapture(e.pointerId);
  drawStart = performance.now();
  drawing = [[...svgPoint(e), 0]];
  if (app.mode === "motion") app.motionStroke = drawing;
  else if (app.mode === "erase") app.lasso = drawing;
  else app.inkStrokes.push(drawing);
  renderInk();
});
canvas.addEventListener("pointermove", (e) => {
  if (!drawing) return;
  const p = svgPoint(e), last = drawing[drawing.length - 1];
  if (Math.hypot(p[0] - last[0], p[1] - last[1]) < 2.5) return; // smooth mouse jitter
  drawing.push([...p, Math.round(performance.now() - drawStart)]);
  renderInk();
});
canvas.addEventListener("pointerup", () => {
  if (app.mode === "erase" && app.lasso) { const l = app.lasso; app.lasso = null; drawing = null; renderInk(); if (l.length > 2) eraseInside(l); return; }
  if (drawing && drawing.length < 2) { app.inkStrokes = app.inkStrokes.filter((s) => s !== drawing); if (app.motionStroke === drawing) app.motionStroke = null; }
  drawing = null; renderInk();
  if (app.mode === "motion" && app.motionStroke) $("command-input").focus();
});

function setMode(m) {
  app.mode = m;
  for (const k of ["ink", "motion", "erase"]) $("mode-" + k).classList.toggle("on", m === k);
  document.body.classList.toggle("motion", m === "motion");
  document.body.classList.toggle("erase", m === "erase");
}

function insidePoly(p, poly) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > p[1]) !== (yj > p[1]) && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}
const mostlyInside = (pts, poly) => pts.filter((p) => insidePoly(p, poly)).length >= Math.max(1, pts.length * 0.5);

async function eraseInside(lasso) {
  let n = 0;
  const before = app.inkStrokes.length;
  app.inkStrokes = app.inkStrokes.filter((s) => !mostlyInside(s, lasso));
  n += before - app.inkStrokes.length;
  if (app.motionStroke && mostlyInside(app.motionStroke, lasso)) { app.motionStroke = null; n++; }
  const sc = scene(), states = endStates(sc);
  for (const [id, st] of Object.entries(states)) {
    const e = app.entities[id]; if (!e) continue;
    const world = (p) => [st.x + p[0] * Math.abs(st.sx ?? 1), st.y + p[1] * Math.abs(st.sy ?? 1)];
    const hit = e.strokes.map((s, i) => (mostlyInside(s.map(world), lasso) ? i : -1)).filter((i) => i >= 0);
    if (!hit.length) continue;
    if (hit.length === e.strokes.length) {
      if (!confirm(`Erase all of “${e.name}”? This removes it and its clips from ${sc.title}.`)) continue;
      await api("/api/scenes/remove-entity", { project_id: app.project._id, scene_id: sc._id, entity_id: id });
      delete sc.start_state[id]; sc.timeline = (sc.timeline || []).filter((c) => c.actor !== id);
    } else {
      const r = await api("/api/entities/erase-strokes", { project_id: app.project._id, entity_id: id, stroke_indices: hit });
      e.strokes = r.strokes; e.bbox = r.bbox;
    }
    n += hit.length;
  }
  status(n ? `erased ${n} stroke(s)` : "nothing inside the lasso");
  renderAll();
}
$("mode-ink").onclick = () => setMode("ink");
$("mode-motion").onclick = () => setMode("motion");
$("mode-erase").onclick = () => setMode("erase");
document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT") return;
  if (e.key === "i") setMode("ink");
  if (e.key === "p" || e.key === "m") setMode("motion");
  if (e.key === "e") setMode("erase");
  if (e.key === "Escape") clearPending();
  if ((e.metaKey || e.ctrlKey) && e.key === "z") { e.preventDefault(); if (app.motionStroke) app.motionStroke = null; else app.inkStrokes.pop(); renderInk(); }
});
function clearPending() { app.inkStrokes = []; app.motionStroke = null; renderInk(); }
$("clear-ink").onclick = clearPending;

$("name-form").onsubmit = async (e) => {
  e.preventDefault();
  const name = $("name-input").value.trim();
  if (!name || !app.inkStrokes.length) return status("Draw something in Ink mode first, then name it.", "err");
  status("saving character…", "busy");
  try {
    const r = await api("/api/entities", { project_id: app.project._id, scene_id: app.sceneId, name, strokes: app.inkStrokes });
    app.entities[r.entity._id] = r.entity;
    scene().start_state[r.entity._id] = r.state;
    app.inkStrokes = []; $("name-input").value = "";
    status(`“${r.entity.name}” saved as a character`);
    renderAll(); flash(r.entity._id);
  } catch (err) { status(err.message, "err"); }
};

$("command-form").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("command-input").value.trim();
  const stroke = app.motionStroke;
  if (!text && !stroke) return;
  status("thinking…", "busy"); $("send").disabled = true;
  try {
    const res = await api("/api/command", { project_id: app.project._id, scene_id: app.sceneId, text, stroke });
    app.lastResult = res;
    renderTrace(res);
    renderProposal(res.proposal || null);
    app.motionStroke = null; renderInk();
    $("command-input").value = "";
    status(res.proposal ? "confirm the refinement above" : res.clips.length ? `${res.clips.length} clip(s)` : "nothing to animate");
    if (res.clips.length) {
      scene().timeline = [...(scene().timeline || []), ...res.clips];
      renderPaths(scene()); renderClipList(scene());
      await play(res.clips);
    }
    const st = await api(`/api/state?project=${encodeURIComponent(app.project.name)}`);
    app.behaviors = st.behaviors;
    renderAll();
  } catch (err) { status(err.message, "err"); }
  finally { $("send").disabled = false; }
};

$("clear-clips").onclick = async () => {
  const sc = scene();
  if (!sc.timeline?.length || !confirm(`Remove all ${sc.timeline.length} clip(s) from ${sc.title}?`)) return;
  await api("/api/scenes/clear", { project_id: app.project._id, scene_id: sc._id });
  sc.timeline = []; status("clips cleared"); renderAll();
};
$("play-scene").onclick = () => play(scene().timeline || [], { fromStart: true }).then(renderAll);
$("play-story").onclick = async () => {
  for (const s of app.scenes) { app.sceneId = s._id; renderAll(); await play(s.timeline || [], { fromStart: true }); }
  renderAll();
};
$("new-scene").onclick = async () => {
  const s = await api("/api/scenes", { project_id: app.project._id });
  app.scenes.push(s); app.sceneId = s._id;
  toast(`${s.title} starts where ${app.scenes[app.scenes.length - 2]?.title || "nothing"} ended`);
  renderAll();
};

const params = new URLSearchParams(location.search);
load(params.get("project") || "rehearsal").catch((e) => status(e.message, "err"));
