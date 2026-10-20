"use strict";
// Characters tab: mascots and figures with 3D viewer, expression sprites and voice preview.
// Figures are project independent, so nothing here reads `project`. Shared helpers ($, esc, request, assetURL, mode)
// come from app.js, which is loaded first. app.js calls drawCharacters() from render() when mode === "characters".
let charState = { status: "idle", list: [], selectedId: null, error: "", generation: 0 };
let charPreview = { busy: false, token: 0 };
async function charactersLoad() {
  const generation = ++charState.generation;
  charState.status = "loading";
  charState.error = "";
  try {
    const r = await fetch("/api/creative/characters");
    if (r.status === 404) throw Error("Characters API nicht erreichbar");
    const d = await r.json().catch(() => ({}));
    if (!r.ok || d.ok === false) throw Error(d.error || d.detail || r.statusText || "Characters API nicht erreichbar");
    if (!Array.isArray(d.characters)) throw Error("Unerwartete Antwort der Characters API");
    if (generation !== charState.generation) return;
    charState.list = d.characters;
    if (!charState.list.some((c) => c.id === charState.selectedId)) charState.selectedId = charState.list[0]?.id || null;
    charState.status = "ready";
  } catch (e) {
    if (generation !== charState.generation) return;
    charState.status = "error";
    charState.error = e instanceof TypeError ? "Characters API nicht erreichbar" : e.message;
  }
  if (mode === "characters") drawCharacters(true);
}
const charThumb = (c) => c.assets?.poster || c.assets?.overview || c.assets?.sprites?.[0]?.url || "";
function drawCharacters(cached = false) {
  const stage = $("stage");
  if (!stage) return;
  stage.innerHTML = "";
  if (charState.status === "idle" || (!cached && charState.status === "error")) {
    charState.status = "loading";
    charactersLoad();
  }
  const root = document.createElement("div");
  root.className = "characters";
  stage.append(root);
  if (charState.status === "loading" || charState.status === "idle") {
    root.innerHTML = '<p class="char-note" role="status">Figuren werden geladen…</p>';
    return;
  }
  if (charState.status === "error") {
    root.innerHTML = `<div class="char-note" role="alert"><strong>${esc(charState.error)}</strong><p>Die Figuren konnten nicht geladen werden.</p><button id="char-retry">Erneut versuchen</button></div>`;
    $("char-retry").onclick = () => {
      charState.status = "idle";
      drawCharacters();
    };
    return;
  }
  if (!charState.list.length) {
    root.innerHTML = '<p class="char-note" role="status">Noch keine Figuren vorhanden.</p>';
    return;
  }
  const c = charState.list.find((x) => x.id === charState.selectedId) || charState.list[0];
  root.innerHTML = `<div class="char-gallery" role="group" aria-label="Figuren">${charState.list
    .map(
      (x) =>
        `<button class="char-card" data-char="${esc(x.id)}" aria-pressed="${x.id === c.id}">${charThumb(x) ? `<img src="${esc(charThumb(x))}" alt="" loading="lazy" />` : '<span class="char-noimg" aria-hidden="true">◉</span>'}<span>${esc(x.name || x.id)}</span></button>`,
    )
    .join("")}</div>
    <div class="char-body"><section class="char-main" aria-label="${esc(c.name || c.id)}">${charMain(c)}</section>${charSide(c)}</div>`;
  root.querySelectorAll("[data-char]").forEach(
    (el) =>
      (el.onclick = () => {
        charState.selectedId = el.dataset.char;
        charPreview.token++;
        drawCharacters(true);
      }),
  );
  charBindMain(root, c);
  charBindSide(root, c);
}
function charMain(c) {
  const a = c.assets || {},
    actions = Array.isArray(c.actions) ? c.actions : [],
    sprites = Array.isArray(a.sprites) ? a.sprites : [];
  const viewer = a.model
    ? `<model-viewer id="char-viewer" src="${esc(a.model)}" alt="3D-Modell ${esc(c.name || c.id)}" camera-controls auto-rotate shadow-intensity="1" ${a.poster ? `poster="${esc(a.poster)}"` : ""} ${actions[0] ? `animation-name="${esc(actions[0])}" autoplay` : ""}></model-viewer>`
    : '<p class="char-note">Kein 3D-Modell vorhanden.</p>';
  const exprs = [...new Set([...(c.expressions || []), ...sprites.map((s) => s.expr)])];
  const grid = sprites.length
    ? exprs
        .map((ex) => {
          const own = sprites.filter((s) => s.expr === ex);
          return own.length
            ? `<div class="char-expr"><h3>${esc(ex)}</h3><div>${own.map((s) => `<button class="char-sprite" data-sprite="${esc(s.url)}" data-label="${esc(s.pose)} · ${esc(s.expr)}" aria-label="${esc(s.pose)}, ${esc(s.expr)}"><img src="${esc(s.url)}" alt="" loading="lazy" /><small>${esc(s.pose)}</small></button>`).join("")}</div></div>`
            : "";
        })
        .join("")
    : '<p class="char-note">Keine Sprites vorhanden.</p>';
  return `<div class="char-viewer-box">${viewer}</div>
    <div class="char-controls">
      <label>Aktion<select id="char-action" ${actions.length ? "" : "disabled"}>${actions.length ? actions.map((x) => `<option>${esc(x)}</option>`).join("") : "<option>Keine Aktionen</option>"}</select></label>
      <label class="char-check"><input id="char-rotate" type="checkbox" checked /> Auto-Rotate</label>
    </div>
    <p id="char-viewer-info" class="char-info" role="status"></p>
    <h3>Ausdrücke</h3>
    <div class="char-preview"><img id="char-sprite-big" alt="" hidden /><small id="char-sprite-label">Sprite anklicken für die Vorschau.</small></div>
    <div class="char-sprites">${grid}</div>
    ${a.idle_video ? `<h3>Idle</h3><video controls loop muted playsinline src="${esc(a.idle_video)}"${a.poster ? ` poster="${esc(a.poster)}"` : ""} aria-label="Idle-Animation"></video>` : ""}`;
}
function charBindMain(root, c) {
  const viewer = root.querySelector("#char-viewer");
  if (viewer) {
    viewer.addEventListener("error", () => ($("char-viewer-info").textContent = "3D-Modell konnte nicht geladen werden."));
    $("char-action").onchange = (e) => {
      viewer.setAttribute("animation-name", e.target.value);
      viewer.setAttribute("autoplay", "");
    };
    $("char-rotate").onchange = (e) => (e.target.checked ? viewer.setAttribute("auto-rotate", "") : viewer.removeAttribute("auto-rotate"));
  }
  root.querySelectorAll("[data-sprite]").forEach(
    (el) =>
      (el.onclick = () => {
        const big = $("char-sprite-big");
        big.src = el.dataset.sprite;
        big.alt = "Sprite " + el.dataset.label;
        big.hidden = false;
        $("char-sprite-label").textContent = el.dataset.label;
      }),
  );
}
function charSide(c) {
  const p = c.persona,
    v = c.voice || {},
    voices = p?.voices || {},
    channels = Array.isArray(c.channels) ? c.channels : [];
  const langs = ["de", "en"].map((l) => `<li><b>${l.toUpperCase()}</b> ${voices[l] ? esc(voices[l].engine) + " · " + esc(voices[l].voice) : "nicht gesetzt"}</li>`).join("");
  return `<aside class="char-side" aria-label="Stimme und Kanal"><div class="panel-title">Stimme & Kanal</div>
    ${c.description ? `<p>${esc(c.description)}</p>` : ""}
    <p><b>Persona</b><br />${p ? esc(p.name) + " · v" + esc(p.version) : "Keine Persona verknüpft"}</p>
    <ul class="char-voices" aria-label="Stimme je Sprache">${langs}</ul>
    <p><b>Kanäle</b></p>
    ${channels.length ? `<ul class="char-channels">${channels.map((k) => `<li>${esc(k)}</li>`).join("")}</ul>` : "<p>Keinem Kanal zugeordnet.</p>"}
    <label>Text für die Stimme<textarea id="char-text" rows="3" maxlength="500" placeholder="Hallo, ich bin ${esc(c.name || "deine Figur")}." ${v.available ? "" : "disabled"}></textarea></label>
    <button id="char-speak" class="primary" ${v.available ? "" : "disabled"}>Stimme anhören</button>
    <p id="char-voice-status" class="char-info" role="status" aria-live="polite">${v.available ? "" : esc(v.reason || "Stimme nicht verfügbar.")}</p>
    <audio id="char-audio" controls hidden aria-label="Stimmvorschau"></audio></aside>`;
}
function charBindSide(root, c) {
  const btn = $("char-speak");
  if (!btn || btn.disabled) return;
  const say = (text, error = false) => {
    const el = $("char-voice-status");
    if (!el) return;
    el.textContent = text;
    el.dataset.error = String(error);
  };
  btn.onclick = async () => {
    const text = $("char-text").value.trim();
    if (!text) return say("Bitte einen Text eingeben.", true);
    const token = ++charPreview.token;
    const alive = () => token === charPreview.token && $("char-speak") === btn;
    btn.disabled = true;
    $("char-audio").hidden = true;
    say("Stimme wird erzeugt…");
    try {
      const job = await request("/api/creative/characters/" + encodeURIComponent(c.id) + "/voice-preview", { text });
      for (let i = 0; i < 120; i++) {
        if (!alive()) return;
        const s = await request("/api/creative/jobs/" + encodeURIComponent(job.id));
        if (s.status === "failed") throw Error(s.error || "Die Stimme konnte nicht erzeugt werden.");
        if (s.status === "completed") {
          if (!s.output) throw Error("Der Auftrag lieferte keine Audiodatei.");
          const audioEl = $("char-audio");
          audioEl.src = assetURL(s.output);
          audioEl.hidden = false;
          return say("Fertig. Mit dem Player abspielen.");
        }
        say(s.status === "queued" ? "In der Warteschlange…" : "Stimme wird erzeugt…");
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      throw Error("Der Auftrag dauert zu lange. Bitte später erneut versuchen.");
    } catch (e) {
      if (alive()) say(e.message, true);
    } finally {
      if ($("char-speak") === btn) btn.disabled = false;
    }
  };
}
