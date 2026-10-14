"use strict";
const $ = (id) => document.getElementById(id),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
let project = null,
  mode = "photo",
  selected = null,
  busy = false,
  audio = null,
  playing = false,
  sources = [],
  socket = null,
  playStart = 0,
  playTimer = null,
  nativeTools = {},
  nativeCapabilities = {},
  playbackToken = 0,
  terminal = null,
  terminalFit = null,
  terminalObserver = null;
const assetURL = (path) =>
  "/api/creative/asset?path=" + encodeURIComponent(path);
function status(text, error = false) {
  $("message").textContent = text;
  $("message").style.color = error ? "#f3a99c" : "";
}
async function request(url, body) {
  const r = await fetch(
    url,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : {},
  );
  const d = await r.json();
  if (!r.ok || d.ok === false) throw Error(d.error || d.detail || r.statusText);
  return d;
}
async function act(action, params = {}, id = project?.id) {
  if (busy) throw Error("An action is still saving. Please try again.");
  busy = true;
  $("saved").textContent = "Saving…";
  try {
    const d = await request("/api/creative/action", {
      action,
      params,
      ...(id ? { project_id: id } : {}),
    });
    if (d.result?.id && Array.isArray(d.result.layers)) {
      project = d.result;
      render();
    }
    if (action === "project.create" || action === "project.rename")
      await listProjects();
    $("saved").textContent = project ? "Saved · r" + project.revision : "Ready";
    return d.result;
  } finally {
    busy = false;
  }
}
function safely(fn) {
  return (...args) => {
    if (args[0]?.type === "submit") args[0].preventDefault();
    return Promise.resolve()
      .then(() => fn(...args))
      .catch((e) => {
        status(e.message, true);
        $("saved").textContent = "Action failed";
      });
  };
}
async function listProjects() {
  const d = await request("/api/creative/action", {
    action: "project.list",
    params: {},
  });
  const list = Array.isArray(d.result) ? d.result : d.result?.projects || [];
  $("projects").innerHTML =
    '<option value="">Choose a project</option>' +
    list
      .map((p) => `<option value="${esc(p.id)}">${esc(p.name)}</option>`)
      .join("");
  if (project) $("projects").value = project.id;
  return list;
}
function empty(title, body) {
  return `<div class="empty"><div class="symbol">✳</div><h2>${title}</h2><p>${body}</p><button class="primary" onclick="document.getElementById('${project ? "import" : "new"}').click()">${project ? "Import media" : "Create a project"}</button></div>`;
}
function render() {
  stop();
  $("projects").value = project?.id || "";
  if (project) {
    const option = Array.from($("projects").options).find(
      (o) => o.value === project.id,
    );
    if (option) option.textContent = project.name;
  }
  $("dimensions").textContent = project
    ? `${project.width} × ${project.height} · ${project.fps} fps`
    : "";
  $("bpm").value = project?.bpm || 120;
  $("brand-name").value = project?.brand?.name || "";
  const bc = project?.brand?.accent;
  if (/^#[0-9a-f]{6}$/i.test(bc || "")) $("brand-color").value = bc;
  $("export").disabled = !project;
  $("undo").disabled = !project;
  $("redo").disabled = !project;
  $("assets").innerHTML = project?.assets?.length
    ? project.assets
        .map(
          (a) =>
            `<div class="asset-group"><button class="asset" data-asset="${esc(a.id)}" title="Add ${esc(a.name)} to composition"><span class="icon">${{ image: "◈", video: "▣", audio: "♫", blender: "◇" }[a.kind] || "□"}</span><span>${esc(a.name)}<small>${esc(a.kind)} · click to insert</small></span></button>${a.kind === "video" ? `<div class="asset-actions"><button data-auto="${esc(a.id)}" ${nativeCapabilities.auto_cut ? "" : "disabled"} title="FFmpeg visual scene detection; creates editable clips">Auto scene cut</button></div>` : a.kind === "blender" ? `<div class="asset-actions"><button data-blend="${esc(a.id)}" ${nativeCapabilities.blender_render ? "" : "disabled"}>Render 3D clip</button></div>` : ""}</div>`,
        )
        .join("")
    : '<p class="empty">Import images, video or sound. Your originals stay in the project library.</p>';
  $("assets")
    .querySelectorAll("[data-asset]")
    .forEach(
      (el) => (el.onclick = safely(() => insertAsset(el.dataset.asset))),
    );
  $("assets")
    .querySelectorAll("[data-auto]")
    .forEach((el) => (el.onclick = safely(() => autoCut(el.dataset.auto))));
  $("assets")
    .querySelectorAll("[data-blend]")
    .forEach(
      (el) => (el.onclick = safely(() => renderBlender(el.dataset.blend))),
    );
  $("workspace-title").textContent = {
    photo: "Design canvas",
    video: "Video · selected source preview",
    audio: "Piano roll · click to add notes",
  }[mode];
  $("tools").innerHTML =
    mode === "photo"
      ? '<button data-tool="rect">＋ Shape</button><button data-tool="text">＋ Text</button>'
      : mode === "video"
        ? '<button data-tool="split">Split selected</button>'
        : '<button data-tool="note">＋ Note</button><button data-tool="lmms-render">Render with LMMS</button><button data-tool="lmms-open">Open in LMMS</button>';
  $("tools")
    .querySelectorAll("button")
    .forEach((el) => {
      el.disabled = !project;
      if (el.dataset.tool.startsWith("lmms-")) {
        el.disabled =
          !project ||
          !nativeTools.lmms?.available ||
          !project.notes.length ||
          project.clips.length > 0;
        el.title =
          "LMMS note-only engine · imported clips use the shared mixer. Add notes and remove clips to enable.";
      }
      el.onclick = safely(() => tool(el.dataset.tool));
    });
  $("stage").innerHTML = "";
  $("sequence").innerHTML = "";
  if (!project)
    $("stage").innerHTML = empty(
      "Make something yours.",
      "A shared space for design, film and sound. Create a project to start editing.",
    );
  else if (mode === "photo") drawPhoto();
  else if (mode === "video") drawVideo();
  else drawAudio();
  renderEntities();
  renderInspector();
}
async function insertAsset(id) {
  if (!project) throw Error("Create a project first.");
  const a = project.assets.find((x) => x.id === id);
  if (mode === "photo") {
    if (a.kind !== "image")
      throw Error("Only image assets can be added to the image canvas.");
    await act("layer.add", {
      name: a.name,
      kind: "image",
      path: a.path,
      x: 0,
      y: 0,
      width: project.width,
      height: project.height,
    });
    selected = { type: "layer", id: project.layers.at(-1).id };
  } else {
    if (!["audio", "video", "image"].includes(a.kind))
      throw Error(
        "This asset needs an external Blender render before insertion.",
      );
    if (mode === "audio" && a.kind !== "audio")
      throw Error("Add sound assets to K-DAW.");
    const duration =
      a.kind === "image" ? 5 : await mediaDuration(a.path, a.kind);
    await act("clip.add", {
      asset_id: id,
      track: Math.max(-1, ...project.clips.map((c) => c.track)) + 1,
      start: 0,
      duration,
      source_start: 0,
      volume: 1,
    });
    selected = { type: "clip", id: project.clips.at(-1).id };
  }
  render();
}
async function tool(kind) {
  if (kind === "lmms-render" || kind === "lmms-open")
    return runLmms(kind === "lmms-render");
  if (kind === "rect" || kind === "text") {
    await act("layer.add", {
      kind,
      name: kind === "text" ? "Title" : "Shape",
      x: Math.round(project.width * 0.1),
      y: Math.round(project.height * 0.15),
      width: Math.round(project.width * 0.55),
      height: Math.round(project.height * 0.25),
      color: project.brand?.accent || "#95dbb8",
      text: kind === "text" ? "Your next idea." : "",
      opacity: 1,
    });
    selected = { type: "layer", id: project.layers.at(-1).id };
  } else if (kind === "note") {
    await act("note.add", {
      pitch: 60,
      start: 0,
      duration: 1,
      velocity: 0.75,
      track: 0,
    });
    selected = { type: "note", id: project.notes.at(-1).id };
  } else {
    const c = current();
    if (selected?.type !== "clip" || !c) throw Error("Select a clip first.");
    await act("clip.split", { id: c.id, at: c.start + c.duration / 2 });
  }
  render();
}
async function mediaDuration(path, kind) {
  const media =
    kind === "video" ? document.createElement("video") : new Audio();
  media.preload = "metadata";
  media.src = assetURL(path);
  return await new Promise((resolve, reject) => {
    const timer = setTimeout(
      () => reject(Error("Media metadata timed out.")),
      15000,
    );
    media.onloadedmetadata = () => {
      clearTimeout(timer);
      Number.isFinite(media.duration) && media.duration > 0
        ? resolve(media.duration)
        : reject(Error("Media has no finite duration."));
    };
    media.onerror = () => {
      clearTimeout(timer);
      reject(Error("This media format cannot be previewed by the browser."));
    };
  });
}
function current() {
  return project && selected
    ? project[
        { layer: "layers", clip: "clips", note: "notes" }[selected.type]
      ]?.find((x) => x.id === selected.id)
    : null;
}
function renderEntities() {
  const key = { photo: "layers", video: "clips", audio: "notes" }[mode],
    type = { photo: "layer", video: "clip", audio: "note" }[mode];
  $("entities").innerHTML =
    (project?.[key] || [])
      .map(
        (e) =>
          `<button class="entity ${selected?.id === e.id ? "selected" : ""}" data-id="${esc(e.id)}"><span>${esc(e.name || (type === "note" ? "Note " + e.pitch : project.assets.find((a) => a.id === e.asset_id)?.name || "Clip"))}<small>${type === "layer" ? esc(e.kind) : type === "note" ? `${e.start} beats · ${e.duration} beats` : `${e.start}s · ${e.duration}s`}</small></span></button>`,
      )
      .join("") || "<p>No elements yet.</p>";
  $("entities")
    .querySelectorAll("button")
    .forEach(
      (el) =>
        (el.onclick = () => {
          selected = { type, id: el.dataset.id };
          render();
        }),
    );
}
function field(name, value, type = "number", extra = "") {
  return `<label>${esc(name)}<input data-field="${esc(name)}" type="${type}" value="${esc(value)}" ${extra}></label>`;
}
function renderInspector() {
  const e = current();
  if (!project) {
    $("inspector").innerHTML =
      "<p>Create a project to access composition settings.</p>";
    return;
  }
  if (!e) {
    $("inspector").innerHTML =
      "<p>Select a layer, clip or note to edit its properties. Changes save automatically.</p>" +
      field("width", project.width) +
      field("height", project.height);
    $("inspector")
      .querySelectorAll("[data-field]")
      .forEach(
        (el) =>
          (el.onchange = safely(() =>
            act("project.settings", { [el.dataset.field]: Number(el.value) }),
          )),
      );
    return;
  }
  let fields = "";
  if (selected.type === "layer")
    fields =
      field("name", e.name, "text") +
      `<div class="field-row">${field("x", e.x)}${field("y", e.y)}${field("width", e.width)}${field("height", e.height)}</div>` +
      field("opacity", e.opacity, "number", 'min="0" max="1" step="0.05"') +
      (e.kind === "text" ? field("text", e.text, "text") : "") +
      (e.kind !== "image" ? field("color", e.color || "#95dbb8", "color") : "");
  else if (selected.type === "clip")
    fields =
      field("start", e.start, "number", 'min="0" step="0.1"') +
      field("duration", e.duration, "number", 'min="0.1" step="0.1"') +
      field(
        "source_start",
        e.source_start || 0,
        "number",
        'min="0" step="0.1"',
      ) +
      field("track", e.track) +
      field("volume", e.volume ?? 1, "number", 'min="0" max="2" step="0.05"');
  else
    fields =
      field("pitch", e.pitch, "number", 'min="0" max="127"') +
      field("start", e.start, "number", 'min="0" step="0.25"') +
      field("duration", e.duration, "number", 'min="0.25" step="0.25"') +
      field(
        "velocity",
        e.velocity ?? 0.75,
        "number",
        'min="0" max="1" step="0.05"',
      );
  $("inspector").innerHTML =
    fields +
    '<button class="danger" id="remove">Delete ' +
    selected.type +
    "</button>";
  $("inspector")
    .querySelectorAll("[data-field]")
    .forEach(
      (el) =>
        (el.onchange = safely(() =>
          act(selected.type + ".update", {
            id: e.id,
            [el.dataset.field]:
              el.type === "number" ? Number(el.value) : el.value,
          }),
        )),
    );
  $("remove").onclick = safely(async () => {
    await act(selected.type + ".remove", { id: e.id });
    selected = null;
    render();
  });
}
function drawPhoto() {
  const c = document.createElement("canvas");
  c.width = project.width;
  c.height = project.height;
  $("stage").append(c);
  const ctx = c.getContext("2d");
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, c.width, c.height);
  const revision = project.revision;
  const layers = [...project.layers];
  async function paint() {
    for (const l of layers) {
      ctx.save();
      ctx.globalAlpha = l.opacity ?? 1;
      if (l.kind === "image" && l.path) {
        const img = new Image();
        img.src = assetURL(l.path);
        try {
          await img.decode();
          if (project.revision !== revision || mode !== "photo") return;
          ctx.drawImage(img, l.x, l.y, l.width, l.height);
        } catch {
          status("Image preview unavailable: " + l.name, true);
        }
      } else if (l.kind === "text") {
        ctx.fillStyle = l.color || "#111";
        const fontSize = Math.max(14, Math.round(l.height * 0.65));
        ctx.font = `700 ${fontSize}px sans-serif`;
        ctx.textBaseline = "top";
        ctx.fillText(l.text || "", l.x, l.y, l.width);
      } else {
        ctx.fillStyle = l.color || "#95dbb8";
        ctx.fillRect(l.x, l.y, l.width, l.height);
      }
      ctx.restore();
      if (selected?.id === l.id) {
        ctx.save();
        ctx.strokeStyle = "#56b78a";
        ctx.lineWidth = Math.max(2, c.width / 500);
        ctx.strokeRect(l.x, l.y, l.width, l.height);
        ctx.restore();
      }
    }
  }
  paint();
  c.onclick = (ev) => {
    const r = c.getBoundingClientRect();
    const x = ((ev.clientX - r.left) * c.width) / r.width,
      y = ((ev.clientY - r.top) * c.height) / r.height;
    const l = [...project.layers]
      .reverse()
      .find(
        (l) =>
          x >= l.x && x <= l.x + l.width && y >= l.y && y <= l.y + l.height,
      );
    selected = l ? { type: "layer", id: l.id } : null;
    render();
  };
  if (!layers.length) {
    const tip = document.createElement("div");
    tip.textContent = "Add a shape, text or an imported image";
    tip.style.cssText =
      "position:absolute;bottom:12px;color:#a3afaa;font-size:10px";
    $("stage").append(tip);
  }
}
function timeline() {
  const clips = project.clips,
    duration = Math.max(10, ...clips.map((c) => c.start + c.duration)),
    tracks = [...new Set(clips.map((c) => c.track))].sort((a, b) => a - b);
  $("sequence").innerHTML =
    `<div class="timeline"><div class="ruler">${Array.from({ length: 11 }, (_, i) => `<span>${((duration * i) / 10).toFixed(1)}s</span>`).join("")}</div>${tracks
      .map(
        (t) =>
          `<div class="track"><span class="track-label">TRACK ${t + 1}</span>${clips
            .filter((c) => c.track === t)
            .map(
              (c) =>
                `<button class="clip ${selected?.id === c.id ? "selected" : ""}" data-clip="${esc(c.id)}" style="left:${(c.start / duration) * 100}%;width:${(c.duration / duration) * 100}%">${esc(project.assets.find((a) => a.id === c.asset_id)?.name || "Clip")}</button>`,
            )
            .join("")}</div>`,
      )
      .join("")}</div>`;
  $("sequence")
    .querySelectorAll("[data-clip]")
    .forEach(
      (el) =>
        (el.onclick = () => {
          selected = { type: "clip", id: el.dataset.clip };
          render();
        }),
    );
}
function drawVideo() {
  const c =
    selected?.type === "clip"
      ? current()
      : project.clips.find(
          (c) =>
            project.assets.find((a) => a.id === c.asset_id)?.kind === "video",
        );
  const a = c && project.assets.find((a) => a.id === c.asset_id);
  if (a?.kind === "video") {
    const v = document.createElement("video");
    v.id = "preview-video";
    v.src = assetURL(a.path);
    v.controls = true;
    v.preload = "metadata";
    v.onloadedmetadata = () => {
      v.currentTime = c.source_start || 0;
    };
    v.volume = Math.min(1, c.volume ?? 1);
    v.ontimeupdate = () => {
      if (v.currentTime >= (c.source_start || 0) + c.duration) v.pause();
      $("time").textContent =
        (c.start + v.currentTime - (c.source_start || 0)).toFixed(2) + " s";
    };
    $("stage").append(v);
  } else if (a?.kind === "image") {
    const img = document.createElement("img");
    img.src = assetURL(a.path);
    img.style.cssText = "max-width:100%;max-height:100%";
    $("stage").append(img);
  } else
    $("stage").innerHTML = empty(
      "A story starts with a frame.",
      "Import footage, images or audio, then click a library asset to place it on the timeline. Preview shows the selected source clip; export renders the full composition.",
    );
  timeline();
}
function drawAudio() {
  const notes = project.notes;
  const duration = Math.max(8, ...notes.map((n) => n.start + n.duration));
  $("stage").innerHTML =
    `<div class="piano"><div class="keys">${Array.from({ length: 25 }, (_, i) => `<div>${72 - i}</div>`).join("")}</div><div class="note-grid" id="note-grid">${notes
      .filter((n) => n.pitch >= 48 && n.pitch <= 72)
      .map(
        (n) =>
          `<button class="note ${selected?.id === n.id ? "selected" : ""}" title="Note ${n.pitch}" data-note="${esc(n.id)}" style="left:${(n.start / duration) * 100}%;width:${(n.duration / duration) * 100}%;top:${(72 - n.pitch) * 12}px"></button>`,
      )
      .join("")}</div></div>`;
  $("note-grid").onclick = safely(async (ev) => {
    if (ev.target.dataset.note) {
      selected = { type: "note", id: ev.target.dataset.note };
      render();
      return;
    }
    const r = ev.currentTarget.getBoundingClientRect(),
      start = Math.floor(((ev.clientX - r.left) / r.width) * duration * 4) / 4,
      pitch = 72 - Math.floor((ev.clientY - r.top) / 12);
    await act("note.add", {
      pitch: Math.max(48, Math.min(72, pitch)),
      start,
      duration: 0.5,
      velocity: 0.75,
      track: 0,
    });
    selected = { type: "note", id: project.notes.at(-1).id };
    render();
  });
  if (project.clips.length) timeline();
}
function stop() {
  playbackToken++;
  sources.forEach((s) => {
    try {
      s.stop ? s.stop() : s.pause();
    } catch {}
  });
  sources = [];
  playing = false;
  clearInterval(playTimer);
  $("play").textContent = "▶ Play";
  $("preview-video")?.pause();
}
async function play() {
  if (!project) return;
  if (playing) {
    stop();
    return;
  }
  if (mode === "photo") {
    status("Switch to K-DAW or K-Video for playback.");
    return;
  }
  if (mode === "video") {
    const v = $("preview-video");
    if (v) {
      await v.play();
      playing = true;
      $("play").textContent = "Ⅱ Pause";
    } else status("Select a video clip to preview it.");
    return;
  }
  audio ??= new (window.AudioContext || window.webkitAudioContext)();
  await audio.resume();
  playing = true;
  $("play").textContent = "Ⅱ Pause";
  const token = ++playbackToken,
    snapshot = project;
  let decoded;
  try {
    decoded = await Promise.all(
      snapshot.clips.map(async (c) => {
        const a = snapshot.assets.find((a) => a.id === c.asset_id);
        if (a?.kind !== "audio") return null;
        const r = await fetch(assetURL(a.path));
        if (!r.ok) throw Error("Cannot load audio: " + a.name);
        return {
          clip: c,
          buffer: await audio.decodeAudioData(await r.arrayBuffer()),
        };
      }),
    );
  } catch (e) {
    stop();
    throw e;
  }
  if (!playing || token !== playbackToken || project.id !== snapshot.id) return;
  const now = audio.currentTime + 0.1,
    beat = 60 / snapshot.bpm;
  for (const n of snapshot.notes) {
    const osc = audio.createOscillator(),
      gain = audio.createGain();
    osc.type = "triangle";
    osc.frequency.value = 440 * 2 ** ((n.pitch - 69) / 12);
    gain.gain.setValueAtTime(0, now + n.start * beat);
    gain.gain.linearRampToValueAtTime(
      (n.velocity ?? 0.75) * 0.15,
      now + n.start * beat + 0.01,
    );
    gain.gain.setValueAtTime(
      (n.velocity ?? 0.75) * 0.15,
      now + (n.start + n.duration) * beat,
    );
    gain.gain.linearRampToValueAtTime(
      0,
      now + (n.start + n.duration) * beat + 0.06,
    );
    osc.connect(gain).connect(audio.destination);
    osc.start(now + n.start * beat);
    osc.stop(now + (n.start + n.duration) * beat + 0.07);
    sources.push(osc);
  }
  for (const item of decoded.filter(Boolean)) {
    const c = item.clip,
      src = audio.createBufferSource(),
      g = audio.createGain();
    src.buffer = item.buffer;
    g.gain.value = c.volume ?? 1;
    src.connect(g).connect(audio.destination);
    src.start(now + c.start, c.source_start || 0, c.duration);
    sources.push(src);
  }
  playStart = performance.now();
  const end = Math.max(
    1,
    ...snapshot.notes.map((n) => (n.start + n.duration) * beat + 0.2),
    ...snapshot.clips.map((c) => c.start + c.duration),
  );
  playTimer = setInterval(() => {
    const t = (performance.now() - playStart) / 1000;
    $("time").textContent = t.toFixed(2) + " s";
    if (t > end) stop();
  }, 50);
}
async function exportProject() {
  if (!project) return;
  status("Starting " + mode + " export…");
  const j = await request("/api/creative/export", {
    project_id: project.id,
    kind: mode,
  });
  $("export").disabled = true;
  try {
    let result = j;
    for (let i = 0; i < 600; i++) {
      if (
        ["done", "completed", "complete", "succeeded", "success"].includes(
          result.status,
        )
      ) {
        const path = result.output?.path || result.output;
        if (!path) throw Error("Export completed without an output path.");
        $("message").innerHTML =
          `Export ready · <a download href="${assetURL(path)}">Download ${esc(mode)}</a>`;
        return;
      }
      if (["failed", "error"].includes(result.status))
        throw Error(result.error || "Export failed");
      await new Promise((r) => setTimeout(r, 500));
      result = await request("/api/creative/jobs/" + encodeURIComponent(j.id));
      status("Rendering " + mode + " · " + result.status);
    }
    throw Error("Export is still running. Job ID: " + j.id);
  } finally {
    $("export").disabled = false;
  }
}
$("new").onclick = () => {
  $("new-dialog").showModal();
  $("project-name").focus();
};
$("cancel-new").onclick = () => $("new-dialog").close();
$("new-form").onsubmit = safely(async (ev) => {
  ev.preventDefault();
  const [width, height] = $("project-size").value.split(",").map(Number);
  await act("project.create", {
    name: $("project-name").value.trim(),
    width,
    height,
  });
  selected = null;
  $("new-dialog").close();
  render();
  status("Project created. Import media or add your first element.");
});
$("projects").onchange = safely(async () => {
  if (!$("projects").value) return;
  selected = null;
  await act("project.get", {}, $("projects").value);
});
$("import").onclick = () => {
  if (!project) {
    $("new").click();
    return;
  }
  $("file").click();
};
$("file").onchange = safely(async () => {
  const file = $("file").files[0];
  if (!file) return;
  const kind = file.type.startsWith("image/")
    ? "image"
    : file.type.startsWith("video/")
      ? "video"
      : file.type.startsWith("audio/")
        ? "audio"
        : file.name.endsWith(".blend")
          ? "blender"
          : null;
  if (!kind) throw Error("Unsupported media type.");
  status("Importing " + file.name + "…");
  const form = new FormData();
  form.append("file", file);
  const r = await fetch("/api/creative/upload", { method: "POST", body: form }),
    d = await r.json();
  if (!r.ok || !d.ok) throw Error(d.error || d.detail || "Upload failed");
  await act("asset.add", {
    path: d.result.path,
    name: d.result.name || file.name,
    kind,
  });
  $("file").value = "";
  status("Imported " + file.name);
});
document.querySelectorAll("[data-mode]").forEach(
  (el) =>
    (el.onclick = () => {
      mode = el.dataset.mode;
      selected = null;
      document
        .querySelectorAll("[data-mode]")
        .forEach((b) => b.classList.toggle("active", b === el));
      render();
    }),
);
$("undo").onclick = safely(() => act("history.undo"));
$("redo").onclick = safely(() => act("history.redo"));
$("export").onclick = safely(exportProject);
$("play").onclick = safely(play);
$("stop").onclick = stop;
$("bpm").onchange = safely(
  () => project && act("project.settings", { bpm: Number($("bpm").value) }),
);
$("brand-save").onclick = safely(() => {
  if (!project) throw Error("Create a project first.");
  return act("brand.update", {
    brand: {
      ...project.brand,
      name: $("brand-name").value,
      accent: $("brand-color").value,
    },
  });
});
$("console-toggle").onclick = () => {
  $("console").hidden = !$("console").hidden;
  if (!$("console").hidden) {
    ensureTerminal();
    requestAnimationFrame(fitTerminal);
  }
};
$("action-run").onclick = safely(async () => {
  const cmd = JSON.parse($("action-json").value);
  const result = await act(
    cmd.action,
    cmd.params || {},
    cmd.project_id || project?.id,
  );
  $("action-log").textContent = JSON.stringify(result, null, 2);
});
function terminalSend(text) {
  if (socket?.readyState !== WebSocket.OPEN) return;
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  socket.send(JSON.stringify({ type: "input", data: btoa(binary) }));
}
function fitTerminal() {
  if (!terminal || $("console").hidden || !$("terminal-output").clientWidth)
    return;
  terminalFit.fit();
  if (socket?.readyState === WebSocket.OPEN)
    socket.send(
      JSON.stringify({
        type: "resize",
        cols: terminal.cols,
        rows: terminal.rows,
      }),
    );
}
function ensureTerminal() {
  if (terminal) return;
  terminal = new Terminal({
    cursorBlink: true,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
    fontSize: 12,
    scrollback: 3000,
    convertEol: false,
    theme: {
      background: "#0c110f",
      foreground: "#c8dfd0",
      cursor: "#95dbb8",
      selectionBackground: "#426753",
      black: "#161d19",
      red: "#e89c95",
      green: "#95dbb8",
      yellow: "#e6cf8c",
      blue: "#92b7e6",
      magenta: "#cba4db",
      cyan: "#9dd5d5",
      white: "#e6ece9",
    },
  });
  terminalFit = new FitAddon.FitAddon();
  terminal.loadAddon(terminalFit);
  terminal.open($("terminal-output"));
  terminal.onData(terminalSend);
  terminal.onBinary((data) => {
    if (socket?.readyState === WebSocket.OPEN)
      socket.send(JSON.stringify({ type: "input", data: btoa(data) }));
  });
  terminal.writeln("K-Creative · interactive local terminal");
  terminal.writeln("Select Shell, Codex or Claude, then connect.");
  terminalObserver = new ResizeObserver(() =>
    requestAnimationFrame(fitTerminal),
  );
  terminalObserver.observe($("terminal-output"));
  requestAnimationFrame(fitTerminal);
}
$("terminal-connect").onclick = () => {
  if (
    socket?.readyState === WebSocket.OPEN ||
    socket?.readyState === WebSocket.CONNECTING
  )
    return;
  $("console").hidden = false;
  ensureTerminal();
  terminal.reset();
  terminal.writeln("Connecting…");
  const agent = $("terminal-agent").value,
    session = agent === "shell" ? "global" : "agent-" + agent;
  const ws = new WebSocket(
    (location.protocol === "https:" ? "wss://" : "ws://") +
      location.host +
      "/ws/terminal/" +
      session,
  );
  socket = ws;
  $("terminal-connect").disabled = true;
  ws.onopen = () => {
    $("terminal-disconnect").disabled = false;
    fitTerminal();
  };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "ready") {
      $("terminal-connect").textContent =
        agent === "shell" ? "Shell connected" : agent + " connected";
      terminal.writeln("Connected · " + (msg.cwd || "Creative workspace"));
      fitTerminal();
      terminal.focus();
    }
    if (msg.type === "output")
      terminal.write(Uint8Array.from(atob(msg.data), (c) => c.charCodeAt(0)));
    if (msg.type === "error") {
      terminal.writeln(
        "Error: " + (msg.message || msg.error || "Session unavailable"),
      );
      status(msg.message || msg.error || "Terminal session unavailable.", true);
    }
  };
  ws.onclose = () => {
    if (socket !== ws) return;
    $("terminal-connect").textContent = "Reconnect";
    $("terminal-connect").disabled = false;
    $("terminal-disconnect").disabled = true;
    terminal.writeln("\r\nSession disconnected.");
  };
  ws.onerror = () =>
    status("Terminal unavailable. Check the local CLI installation.", true);
};
$("terminal-disconnect").onclick = () => socket?.close();
$("terminal-agent").onchange = () => {
  socket?.close();
  socket = null;
  $("terminal-connect").disabled = false;
  $("terminal-connect").textContent = "Connect " + $("terminal-agent").value;
  $("terminal-disconnect").disabled = true;
  if (terminal) {
    terminal.reset();
    terminal.writeln("Ready to start " + $("terminal-agent").value + ".");
  }
};
$("terminal-form").onsubmit = (ev) => {
  ev.preventDefault();
  if (socket?.readyState !== WebSocket.OPEN) {
    status("Connect a terminal session first.", true);
    return;
  }
  terminalSend($("terminal-input").value + "\r");
  $("terminal-input").value = "";
  terminal.focus();
};
window.addEventListener("resize", () => requestAnimationFrame(fitTerminal));
(async () => {
  try {
    const d = await request("/api/creative/agents"),
      agents = d.result || {};
    for (const name of ["codex", "claude"]) {
      const option = $("terminal-agent").querySelector(
        '[value="' + name + '"]',
      );
      option.disabled = !agents[name];
      option.textContent =
        name[0].toUpperCase() +
        name.slice(1) +
        (agents[name] ? "" : " · not installed");
    }
  } catch {
    for (const option of $("terminal-agent").options)
      if (option.value !== "shell")
        option.textContent = option.value + " · unavailable";
  }
})();

document.addEventListener("keydown", (ev) => {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(ev.target.tagName)) return;
  if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") {
    ev.preventDefault();
    if (project)
      safely(() => act(ev.shiftKey ? "history.redo" : "history.undo"))();
  }
  if (ev.code === "Space") {
    ev.preventDefault();
    safely(play)();
  }
  if (ev.key === "Delete" && current())
    safely(async () => {
      await act(selected.type + ".remove", { id: selected.id });
      selected = null;
      render();
    })();
});
(async () => {
  render();
  try {
    const list = await listProjects();
    if (list.length) await act("project.get", {}, list[0].id);
    const cap = await request("/api/creative/capabilities");
    const engines = cap.media || cap.result || cap;
    $("capabilities").textContent =
      "Engines · " +
      ["photo", "audio", "video"]
        .map((k) => k + ": " + (engines[k] ? "ready" : "unavailable"))
        .join(" · ");
    $("speech-create").disabled = !engines.tts?.kokoro;
    $("speech-info").textContent = engines.tts?.kokoro
      ? "Kokoro · local neural speech. English voices; German unavailable."
      : "Local Kokoro model unavailable. Install the model to generate speech.";
    $("saved").textContent = project ? "Saved · r" + project.revision : "Ready";
    status("Workspace ready");
  } catch (e) {
    status(e.message, true);
    $("saved").textContent = "Unavailable";
  }
})();

$("speech-create").onclick = safely(async () => {
  if (!project) throw Error("Create a project first.");
  const pid = project.id;
  const text = $("speech-text").value.trim();
  if (!text) throw Error("Write the voiceover text first.");
  $("speech-create").disabled = true;
  try {
    const j = await request("/api/creative/tts", {
      text,
      provider: "kokoro",
      voice: $("speech-voice").value,
      language: $("speech-voice").value.startsWith("b") ? "en-gb" : "en-us",
      speed: 1,
    });
    for (let i = 0; i < 600; i++) {
      const r = await request("/api/creative/jobs/" + encodeURIComponent(j.id));
      if (r.status === "failed")
        throw Error(r.error || "Speech generation failed");
      if (r.status === "completed") {
        const path = r.output?.path || r.output || r.details?.path;
        if (!path) throw Error("Speech generation returned no output.");
        if (project?.id !== pid)
          throw Error(
            "Return to the original project to import this voiceover.",
          );
        await act("asset.add", {
          path,
          name: "Voiceover " + new Date().toLocaleTimeString(),
          kind: "audio",
        });
        const asset = project.assets.at(-1),
          media = new Audio(assetURL(path));
        const duration = await new Promise((resolve, reject) => {
          media.onloadedmetadata = () => resolve(media.duration);
          media.onerror = () =>
            reject(
              Error(
                "Voiceover generated, but metadata could not be loaded. It remains in the library.",
              ),
            );
        });
        await act("clip.add", {
          asset_id: asset.id,
          track: project.clips.length,
          start: 0,
          duration,
          source_start: 0,
          volume: 1,
        });
        status("Voiceover added to the library and composition.");
        return;
      }
      status("Generating local voiceover · " + r.status);
      await new Promise((r) => setTimeout(r, 500));
    }
    throw Error("Voiceover still running. Job ID: " + j.id);
  } finally {
    $("speech-create").disabled = false;
  }
});

setInterval(async () => {
  if (
    !project ||
    busy ||
    playing ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)
  )
    return;
  try {
    const d = await request("/api/creative/action", {
      action: "project.get",
      project_id: project.id,
      params: {},
    });
    if (
      !busy &&
      d.result?.id === project.id &&
      d.result.revision > project.revision
    ) {
      project = d.result;
      render();
      $("saved").textContent = "Synced · r" + project.revision;
      status("Project updated by another editor or MCP action.");
    }
  } catch {
    /* Foreground actions report server errors. */
  }
}, 3000);

async function awaitJob(job, label) {
  for (let i = 0; i < 1200; i++) {
    const r = await request("/api/creative/jobs/" + encodeURIComponent(job.id));
    if (r.status === "completed") return r;
    if (r.status === "failed") throw Error(r.error || label + " failed");
    status(label + " · " + r.status);
    await new Promise((r) => setTimeout(r, 500));
  }
  throw Error(label + " still running. Job ID: " + job.id);
}
async function autoCut(id) {
  const a = project.assets.find((a) => a.id === id);
  const pid = project.id;
  const job = await request("/api/creative/autocut", {
    path: a.path,
    threshold: 0.3,
  });
  const result = await awaitJob(job, "Detecting scene boundaries");
  if (project?.id !== pid)
    throw Error("Return to the original project to import these scene cuts.");
  const segments = result.details?.segments || result.segments;
  if (!segments?.length) throw Error("No usable scene segments returned.");
  const track = Math.max(-1, ...project.clips.map((c) => c.track)) + 1;
  for (const s of segments)
    await act("clip.add", {
      asset_id: id,
      track,
      start: s.start ?? s.source_start,
      duration: s.duration,
      source_start: s.source_start,
      volume: 1,
    });
  status("Added " + segments.length + " editable scene clips.");
}
async function renderBlender(id) {
  const a = project.assets.find((a) => a.id === id);
  const pid = project.id;
  const fps = project.fps;
  const job = await request("/api/creative/blender", {
    path: a.path,
    frame_start: 1,
    frame_end: 30,
    fps,
  });
  const result = await awaitJob(job, "Rendering Blender scene");
  if (project?.id !== pid)
    throw Error("Return to the original project to import this render.");
  const path = result.output?.path || result.output;
  await act("asset.add", { path, name: a.name + " · rendered", kind: "video" });
  const vid = project.assets.at(-1).id;
  await act("clip.add", {
    asset_id: vid,
    track: Math.max(-1, ...project.clips.map((c) => c.track)) + 1,
    start: 0,
    duration: result.details?.duration || 30 / fps,
    source_start: 0,
    volume: 1,
  });
  status("Blender render added. Original scene remains editable.");
}
(async () => {
  try {
    const d = await request("/api/creative/tools");
    nativeCapabilities = d.result || {};
    nativeTools = nativeCapabilities.tools || nativeCapabilities;
    $("native-tools").innerHTML = [
      "lmms",
      "ardour",
      "gimp",
      "kdenlive",
      "blender",
    ]
      .map(
        (tool) =>
          `<button data-native="${tool}" ${nativeTools[tool]?.available ? "" : "disabled"} title="${nativeTools[tool]?.available ? "Launch installed editor" : "Not installed"}">${tool === "lmms" ? "LMMS" : tool[0].toUpperCase() + tool.slice(1)} ↗</button>`,
      )
      .join("");
    $("native-tools")
      .querySelectorAll("button")
      .forEach(
        (el) =>
          (el.onclick = safely(async () => {
            await request("/api/creative/launch", { tool: el.dataset.native });
            status(
              "Launch requested for " + el.dataset.native + " desktop editor.",
            );
          })),
      );
    if (project) render();
  } catch {
    $("native-tools").textContent = "Native editor adapters unavailable.";
  }
})();

let imageGenerationReady = false;
(async () => {
  try {
    const d = await request("/api/creative/generators"),
      cap = d.result || {};
    const checkpoints = cap.checkpoints || [];
    imageGenerationReady = !!(cap.available && cap.image && checkpoints.length);
    $("image-checkpoint").innerHTML = checkpoints.length
      ? checkpoints
          .map(
            (c) =>
              `<option value="${esc(typeof c === "string" ? c : c.name)}">${esc(typeof c === "string" ? c : c.name)}</option>`,
          )
          .join("")
      : "<option>No model connected</option>";
    $("image-generate").disabled = !imageGenerationReady;
    $("image-generator-info").textContent = imageGenerationReady
      ? "Local ComfyUI · output becomes an editable image layer. Video generation requires a configured model workflow."
      : "Connect local ComfyUI and install an image checkpoint to enable generation. No image generator is currently ready.";
  } catch {
    $("image-generator-info").textContent =
      "Local image generation unavailable. Connect ComfyUI to enable it.";
  }
})();
$("image-generate").onclick = safely(async () => {
  if (!imageGenerationReady)
    throw Error("Connect a local ComfyUI image model first.");
  if (!project) throw Error("Create a project first.");
  const prompt = $("image-prompt").value.trim();
  if (!prompt) throw Error("Describe the image first.");
  const pid = project.id;
  const width = Math.max(
      64,
      Math.min(2048, Math.ceil(project.width / 64) * 64),
    ),
    height = Math.max(64, Math.min(2048, Math.ceil(project.height / 64) * 64));
  $("image-generate").disabled = true;
  try {
    const job = await request("/api/creative/generate/image", {
      prompt,
      checkpoint: $("image-checkpoint").value,
      width,
      height,
      steps: 20,
    });
    const result = await awaitJob(job, "Generating local AI image");
    if (project?.id !== pid)
      throw Error("Return to the original project to import this image.");
    const path = result.output?.path || result.output;
    if (!path) throw Error("Image generator returned no output path.");
    await act("asset.add", {
      path,
      name: "AI image · " + prompt.slice(0, 45),
      kind: "image",
    });
    await act("layer.add", {
      path,
      name: "AI image · " + prompt.slice(0, 45),
      kind: "image",
      x: 0,
      y: 0,
      width: project.width,
      height: project.height,
      opacity: 1,
    });
    selected = { type: "layer", id: project.layers.at(-1).id };
    mode = "photo";
    document
      .querySelectorAll("[data-mode]")
      .forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    render();
    status("Generated image added to the project library and canvas.");
  } finally {
    $("image-generate").disabled = !imageGenerationReady;
  }
});

async function runLmms(renderAudio) {
  if (!project || !nativeTools.lmms?.available)
    throw Error("Create a project and install LMMS first.");
  if (!project.notes.length || project.clips.length)
    throw Error(
      "LMMS export currently supports notes only. Imported clips use the shared audio mixer.",
    );
  const pid = project.id,
    name = project.name;
  const job = await request("/api/creative/lmms", {
    project_id: pid,
    render: renderAudio,
  });
  const result = await awaitJob(
    job,
    renderAudio ? "Rendering with LMMS" : "Creating editable LMMS project",
  );
  const output = result.output?.path || result.output,
    source = result.details?.source || output;
  if (!renderAudio) {
    await request("/api/creative/launch", { tool: "lmms", path: source });
    $("message").innerHTML =
      `LMMS launch requested · <a download href="${assetURL(source)}">Download editable project</a>`;
    return;
  }
  $("message").innerHTML =
    `LMMS render ready · <a download href="${assetURL(output)}">WAV</a> · <a download href="${assetURL(source)}">Editable project</a> <button id="lmms-import">Import to library</button>`;
  $("lmms-import").onclick = safely(async () => {
    if (project?.id !== pid)
      throw Error("Return to the original project to import this render.");
    await act("asset.add", {
      path: output,
      name: name + " · LMMS render",
      kind: "audio",
    });
    status("LMMS render added to library. Existing notes remain unchanged.");
  });
}

// Read-only shared workflow discovery; never executes an integration manifest.
let workflowRequest = 0;
async function loadWorkflows() {
  const sequence = ++workflowRequest;
  const kind = $("workflow-kind").value;
  $("workflow-info").textContent = "Discovering tools…";
  try {
    const { result } = await request(
      "/api/creative/workflows?kind=" + encodeURIComponent(kind),
    );
    if (sequence !== workflowRequest) return;
    const labels = {
      available_to_probe: "Found · check before use",
      unavailable: "Unavailable",
      review_required: "Candidate · review required",
    };
    $("workflow-tools").replaceChildren();
    for (const tool of result.tools) {
      const row = document.createElement("div");
      row.className = "workflow-tool";
      const name = document.createElement("strong");
      name.textContent = tool.id;
      const state = document.createElement("span");
      state.className = "tool-state " + tool.status;
      state.textContent = labels[tool.status] || "Unknown status";
      row.append(name, state);
      $("workflow-tools").append(row);
    }
    $("workflow-info").textContent = result.manifest_errors.length
      ? "Some integration metadata could not be read. Existing tools remain available."
      : "Tools share the Creative workflow. Found tools still need a runtime check; candidates are pending evaluation.";
  } catch (error) {
    if (sequence !== workflowRequest) return;
    $("workflow-tools").textContent = "Tool discovery unavailable.";
    $("workflow-info").textContent = error.message;
  }
}
$("workflow-kind").addEventListener("change", loadWorkflows);
loadWorkflows();
