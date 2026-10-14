"use strict";
let assistantBusy = false, assistantPlan = null, assistantSketch = null,
  assistantProjectId = project?.id, assistantGeneration = 0, assistantRecording = null,
  assistantRecordStream = null, assistantRecordTimer = null, assistantSpeechReady = false;
const assistantChats = new Map();
function assistantProgress(message, error = false) {
  $("assistant-progress").textContent = message;
  $("assistant-progress").dataset.error = String(error);
}
function assistantHistory() {
  if (!assistantChats.has(assistantProjectId)) assistantChats.set(assistantProjectId, []);
  return assistantChats.get(assistantProjectId);
}
function assistantMessage(role, content, remember = true) {
  const row = document.createElement("div");
  row.className = "assistant-message " + role;
  const label = document.createElement("strong");
  label.textContent = role === "user" ? "Du" : "Creative Assistant";
  const text = document.createElement("span");
  text.textContent = content;
  row.append(label, text);
  $("assistant-messages").append(row);
  $("assistant-messages").scrollTop = $("assistant-messages").scrollHeight;
  if (remember) {
    assistantHistory().push({ role, content });
    if (assistantHistory().length > 16) assistantHistory().splice(0, assistantHistory().length - 16);
  }
}
function assistantSetBusy(value) {
  assistantBusy = value;
  $("assistant-send").disabled = value;
  $("assistant-apply").disabled = value || !assistantPlan || assistantPlan.kind !== "edit";
  $("assistant-record").disabled = value || !assistantSpeechReady;
  $("assistant-reset").disabled = value;
}
function assistantProjectChanged(id) {
  if (assistantProjectId === id) return;
  assistantGeneration++;
  assistantProjectId = id;
  assistantPlan = null;
  assistantSketch = null;
  $("assistant-attachment").hidden = true;
  $("assistant-input").value = "";
  $("assistant-messages").replaceChildren();
  for (const entry of assistantHistory()) assistantMessage(entry.role, entry.content, false);
  if (assistantRecording?.state === "recording") assistantRecording.stop();
  assistantSetBusy(false);
  assistantProgress(id ? "Bereit für dieses Projekt." : "Erstelle oder öffne zuerst ein Projekt.");
}
async function assistantWait(job, generation, pid) {
  for (let i = 0; i < 360; i++) {
    if (generation !== assistantGeneration || project?.id !== pid) throw Error("Projekt gewechselt; Ergebnis gehört zum vorherigen Projekt.");
    const state = await request("/api/creative/jobs/" + encodeURIComponent(job.id));
    if (state.status === "failed") throw Error(state.error || "Der Auftrag ist fehlgeschlagen.");
    if (state.status === "completed") return state.details;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw Error("Der Auftrag dauert zu lange. Prüfe den Job, bevor du ihn wiederholst.");
}
async function assistantApplyPlan(plan, generation, pid) {
  assistantProgress(plan.primitive === "none" ? "Änderungen werden angewendet…" : "Editierbares 3D-Objekt wird erstellt und gerendert…");
  const job = await request("/api/creative/assistant/apply", { plan_id: plan.id });
  const result = await assistantWait(job, generation, pid);
  if (generation !== assistantGeneration || project?.id !== pid) return;
  project = result.project;
  $("saved").textContent = "Saved · r" + project.revision;
  const editsLayers = plan.primitive !== "none" || plan.commands.some((command) => command.action.startsWith("layer."));
  if (editsLayers && project.layers.length) {
    const updated = plan.commands.find((command) => command.action === "layer.update");
    selected = { type: "layer", id: updated?.params.id || project.layers.at(-1).id };
    mode = "photo";
    document.querySelectorAll("[data-mode]").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  }
  render();
  assistantPlan = null;
  assistantMessage("assistant", "Angewendet. Du kannst die Änderungen mit einem Schritt rückgängig machen.");
  assistantProgress("Gespeichert · Revision " + project.revision);
}
$("assistant-form").onsubmit = async (event) => {
  event.preventDefault();
  if (assistantBusy) return;
  if (assistantRecording?.state === "recording") { assistantProgress("Beende zuerst die Aufnahme.", true); return; }
  const text = $("assistant-input").value.trim();
  if (!project || !text) {
    assistantProgress(!project ? "Erstelle zuerst ein Projekt." : "Beschreibe deinen Auftrag.", true);
    return;
  }
  const pid = project.id, generation = assistantGeneration;
  const history = assistantHistory().slice(-14);
  assistantMessage("user", text);
  $("assistant-input").value = "";
  assistantPlan = null;
  assistantSetBusy(true);
  assistantProgress("Auftrag wird verstanden…");
  try {
    const job = await request("/api/creative/assistant/plan", {
      project_id: pid, provider: $("assistant-provider").value, text, history,
      selected, sketch: assistantSketch,
    });
    const plan = await assistantWait(job, generation, pid);
    assistantPlan = plan;
    assistantMessage("assistant", plan.message);
    if (plan.kind === "edit") {
      if ($("assistant-preview-first").checked) {
        const preview = document.createElement("pre");
        preview.textContent = plan.primitive === "none" ? JSON.stringify(plan.commands, null, 2) : "3D: " + plan.primitive + " · " + plan.color + " · " + plan.size;
        $("assistant-messages").append(preview);
        assistantProgress("Entwurf bereit. Anwenden oder mit einem neuen Auftrag verfeinern.");
      } else await assistantApplyPlan(plan, generation, pid);
    } else assistantProgress(plan.kind === "clarify" ? "Deine Antwort wird benötigt. Das Projekt bleibt erhalten." : "Erklärung bereit.");
  } catch (error) {
    if (generation === assistantGeneration) {
      assistantMessage("assistant", error.message, false);
      assistantProgress(error.message, true);
    }
  } finally {
    if (generation === assistantGeneration) assistantSetBusy(false);
  }
};
$("assistant-apply").onclick = async () => {
  if (!assistantPlan || assistantBusy) return;
  const generation = assistantGeneration, pid = project?.id;
  assistantSetBusy(true);
  try { await assistantApplyPlan(assistantPlan, generation, pid); }
  catch (error) { assistantProgress(error.message, true); assistantPlan = null; }
  finally { if (generation === assistantGeneration) assistantSetBusy(false); }
};
$("assistant-undo").onclick = safely(async () => {
  if (assistantBusy) throw Error("Warte bis der Auftrag abgeschlossen ist.");
  await act("history.undo");
  assistantPlan = null;
  assistantSetBusy(false);
  assistantProgress("Letzte Änderung rückgängig gemacht.");
});
$("assistant-reset").onclick = () => {
  if (assistantBusy) return;
  assistantGeneration++;
  assistantChats.set(assistantProjectId, []);
  assistantPlan = null;
  assistantSketch = null;
  $("assistant-messages").replaceChildren();
  $("assistant-attachment").hidden = true;
  $("assistant-input").value = "";
  assistantSetBusy(false);
  assistantProgress("Neuer Dialog. Dein Projekt bleibt erhalten.");
};
function assistantToggle(open) {
  $("assistant-panel").hidden = !open;
  $("assistant-toggle").setAttribute("aria-expanded", String(open));
  if (open) $("assistant-input").focus();
  else {
    if (assistantRecording?.state === "recording") assistantRecording.stop();
    $("assistant-toggle").focus();
  }
}
$("assistant-toggle").onclick = () => assistantToggle($("assistant-panel").hidden);
$("assistant-close").onclick = () => assistantToggle(false);
$("assistant-panel").addEventListener("keydown", (event) => {
  if (event.key === "Escape") { event.stopPropagation(); assistantToggle(false); }
});
$("assistant-provider").onchange = () => {
  const provider = $("assistant-provider").value;
  request("/api/creative/assistant/capabilities").then(({ result }) => { $("assistant-provider-info").textContent = result.providers[provider]?.note || "Nicht verfügbar"; }).catch(() => {});
  $("assistant-privacy").textContent = provider === "builtin" ? "Lokale 3D-Befehle senden keine Daten an einen KI-Anbieter."
    : provider === "ollama" ? "Anfrage, Projektkontext und angehängte Bilder gehen an deinen konfigurierten Ollama-Server."
    : "Anfrage, Projektkontext und angehängte Bilder werden an den gewählten KI-Anbieter gesendet. Deine Konto-/API-Kosten gelten.";
};
async function assistantCapabilities() {
  const { result } = await request("/api/creative/assistant/capabilities");
  for (const option of $("assistant-provider").options) {
    const state = result.providers[option.value];
    option.disabled = !state?.available;
    option.title = state?.note || "Nicht verfügbar";
  }
  const state = result.providers[$("assistant-provider").value];
  $("assistant-provider-info").textContent = state?.note || "Nicht verfügbar";
  $("assistant-speech-info").textContent = result.speech.available ? "Whisper ist lokal verfügbar. Diktat bleibt vor dem Senden editierbar." : "Lokales Diktat benötigt ein Whisper-Modell. Du kannst jederzeit tippen.";
  assistantSpeechReady = result.speech.available && !!navigator.mediaDevices?.getUserMedia && !!window.MediaRecorder;
  assistantSetBusy(assistantBusy);
  assistantProgress(assistantSpeechReady ? "Bereit · Diktat wird lokal mit Whisper verarbeitet." : "Texteingabe bereit. Lokales Diktat benötigt Whisper-Modell und Mikrofonzugriff.");
}
$("assistant-config-save").onclick = async () => {
  try {
    await request("/api/creative/assistant/provider", {
      provider: $("assistant-config-provider").value, url: $("assistant-url").value,
      model: $("assistant-model").value, key: $("assistant-key").value,
    });
    $("assistant-key").value = "";
    await assistantCapabilities();
    $("assistant-provider").value = $("assistant-config-provider").value;
    $("assistant-provider").dispatchEvent(new Event("change"));
    assistantProgress("Verbindung konfiguriert. Modellzugriff wird beim nächsten Auftrag geprüft.");
  } catch (error) { assistantProgress(error.message, true); }
};

// Explicit attachments: draw or upload, then include only the selected reference.
const assistantCanvas = $("assistant-sketch"), assistantCtx = assistantCanvas.getContext("2d");
let assistantDrawing = false;
function assistantClearSketch() {
  assistantCtx.fillStyle = "#ffffff";
  assistantCtx.fillRect(0, 0, assistantCanvas.width, assistantCanvas.height);
  assistantCtx.strokeStyle = "#111111";
  assistantCtx.lineWidth = 5;
  assistantCtx.lineCap = "round";
  assistantCtx.lineJoin = "round";
}
function assistantPoint(event) {
  const rect = assistantCanvas.getBoundingClientRect();
  return [(event.clientX - rect.left) * assistantCanvas.width / rect.width,
    (event.clientY - rect.top) * assistantCanvas.height / rect.height];
}
assistantClearSketch();
assistantCanvas.onpointerdown = (event) => {
  assistantDrawing = true;
  assistantCanvas.setPointerCapture(event.pointerId);
  assistantCtx.beginPath();
  assistantCtx.moveTo(...assistantPoint(event));
};
assistantCanvas.onpointermove = (event) => {
  if (!assistantDrawing) return;
  assistantCtx.lineTo(...assistantPoint(event));
  assistantCtx.stroke();
};
assistantCanvas.onpointerup = assistantCanvas.onpointercancel = () => { assistantDrawing = false; };
$("assistant-sketch-clear").onclick = assistantClearSketch;
async function assistantAttach(file) {
  if (assistantBusy) return;
  if (!project) throw Error("Erstelle zuerst ein Projekt.");
  if (file.size > 16 * 1024 * 1024) throw Error("Skizze darf höchstens 16 MiB gross sein.");
  const generation = assistantGeneration;
  const data = new FormData(); data.append("file", file);
  const response = await fetch("/api/creative/upload", { method: "POST", body: data });
  const result = await response.json();
  if (!response.ok) throw Error(result.detail || "Skizze konnte nicht angehängt werden.");
  if (generation !== assistantGeneration) return;
  assistantSketch = result.result.path;
  $("assistant-reference").src = assetURL(assistantSketch);
  $("assistant-reference-name").textContent = file.name;
  $("assistant-attachment").hidden = false;
  assistantProgress("Skizze angehängt. Beschreibe das gewünschte Design.");
}
$("assistant-sketch-use").onclick = () => assistantCanvas.toBlob((blob) => {
  assistantAttach(new File([blob], "sketch.png", { type: "image/png" })).catch((error) => assistantProgress(error.message, true));
}, "image/png");
$("assistant-file-open").onclick = () => $("assistant-file").click();
$("assistant-file").onchange = async () => {
  const file = $("assistant-file").files[0];
  if (file) try { await assistantAttach(file); } catch (error) { assistantProgress(error.message, true); }
  $("assistant-file").value = "";
};
$("assistant-reference-remove").onclick = () => {
  assistantSketch = null;
  $("assistant-attachment").hidden = true;
};

// Recording is explicit, bounded and always releases the microphone.
$("assistant-record").onclick = async () => {
  if (assistantRecording?.state === "recording") { assistantRecording.stop(); return; }
  const generation = assistantGeneration;
  $("assistant-record").disabled = true;
  try {
    assistantRecordStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (generation !== assistantGeneration || $("assistant-panel").hidden) {
      assistantRecordStream.getTracks().forEach((track) => track.stop());
      assistantRecordStream = null;
      $("assistant-record").disabled = !assistantSpeechReady;
      return;
    }
    $("assistant-record").disabled = false;
    const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"].find((type) => MediaRecorder.isTypeSupported(type));
    assistantRecording = new MediaRecorder(assistantRecordStream, mime ? { mimeType: mime } : {});
    const chunks = [];
    assistantRecording.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
    assistantRecording.onstop = async () => {
      clearTimeout(assistantRecordTimer);
      assistantRecordStream?.getTracks().forEach((track) => track.stop());
      assistantRecordStream = null;
      $("assistant-record").textContent = "Mikrofon";
      $("assistant-record").setAttribute("aria-pressed", "false");
      if (generation !== assistantGeneration) return;
      assistantSetBusy(true);
      assistantProgress("Sprache wird lokal erkannt…");
      try {
        const type = assistantRecording.mimeType;
        const blob = new Blob(chunks, { type });
        const data = new FormData();
        data.append("file", blob, type.includes("mp4") ? "recording.m4a" : "recording.webm");
        const response = await fetch("/api/creative/assistant/transcribe?language=" + encodeURIComponent($("assistant-language").value), { method: "POST", body: data });
        const result = await response.json();
        if (!response.ok) throw Error(result.detail || "Spracherkennung fehlgeschlagen.");
        if (generation !== assistantGeneration) return;
        $("assistant-input").value = [$("assistant-input").value, result.result.text].filter(Boolean).join(" ");
        $("assistant-input").focus();
        assistantProgress("Diktat erkannt. Du kannst den Text bearbeiten und senden.");
      } catch (error) { assistantProgress(error.message, true); }
      finally { if (generation === assistantGeneration) assistantSetBusy(false); }
    };
    assistantRecording.start();
    assistantRecordTimer = setTimeout(() => { if (assistantRecording?.state === "recording") assistantRecording.stop(); }, 90000);
    $("assistant-record").textContent = "Aufnahme beenden";
    $("assistant-record").setAttribute("aria-pressed", "true");
    assistantProgress("Mikrofon nimmt auf · maximal 90 Sekunden.");
  } catch (error) {
    assistantRecordStream?.getTracks().forEach((track) => track.stop());
    assistantRecordStream = null;
    $("assistant-record").disabled = !assistantSpeechReady;
    assistantProgress("Mikrofon nicht verfügbar: " + error.message, true);
  }
};
window.addEventListener("beforeunload", () => assistantRecordStream?.getTracks().forEach((track) => track.stop()));
assistantCapabilities().catch((error) => assistantProgress(error.message, true));

// Brand identity uses the same native project and undo history as design edits.
function renderBrandIdentity() {
  $("brand-build").disabled = !project;
  $("brand-export").disabled = !project?.brand?.identity;
  $("brand-import").disabled = !project;
  $("brand-palette").replaceChildren();
  const identity = project?.brand?.identity;
  if (!identity) return;
  for (const role of ["primary", "secondary", "accent", "background", "surface", "text", "muted"]) {
    const color = identity.palette[role];
    const label = document.createElement("label");
    label.className = "brand-color-role";
    label.append(document.createTextNode(role));
    const input = document.createElement("input");
    input.type = "color"; input.value = color;
    input.setAttribute("aria-label", "Brand color " + role);
    const hex = document.createElement("span"); hex.textContent = color;
    label.append(input, hex);
    input.onchange = safely(async () => {
      const brand = structuredClone(project.brand);
      brand.identity.palette[role] = input.value;
      if (role === "accent") brand.accent = input.value;
      await act("brand.update", { brand });
    });
    $("brand-palette").append(label);
  }
}
$("brand-build").onclick = () => {
  if (!project) return;
  $("brand-project-name").value = project.brand?.name || project.name;
  $("brand-brief").value = project.brand?.identity?.brief || "";
  $("brand-audience").value = project.brand?.identity?.audience || "";
  $("brand-goal").value = project.brand?.identity?.goal || "";
  $("brand-dialog").showModal();
};
$("brand-cancel").onclick = () => $("brand-dialog").close();
$("brand-form").onsubmit = safely(async (event) => {
  event.preventDefault();
  if (!project) throw Error("Erstelle zuerst ein Projekt.");
  const pid = project.id;
  const response = await request("/api/creative/brand/create", {
    project_id: pid, preset: $("brand-preset").value, name: $("brand-project-name").value,
    brief: $("brand-brief").value, audience: $("brand-audience").value, goal: $("brand-goal").value,
  });
  $("brand-dialog").close();
  if (project?.id !== pid) throw Error("Die Brand wurde im ursprünglichen Projekt gespeichert.");
  project = response.result;
  $("saved").textContent = "Saved · r" + project.revision;
  render();
  status("Brand-Entwurf gespeichert. Farben sind editierbar; das Paket kann exportiert werden.");
});
$("brand-ai").onclick = () => {
  if (!project) return;
  const style = $("brand-preset").selectedOptions[0].text;
  const text = `Entwickle die Brand identity für «${$("brand-project-name").value}». Stilrichtung: ${style}. ${$("brand-brief").value}\nZielgruppe: ${$("brand-audience").value || "Für den ersten Entwurf als Annahme benennen"}. Ziel: ${$("brand-goal").value || "Wiedererkennbare Marke"}. Erstelle Farben, Typografie, Bildsprache, Tonalität und Social-Media-Vorgaben als editierbare Brand identity. Frage nach, wenn entscheidende Angaben unklar sind.`;
  $("brand-dialog").close();
  assistantToggle(true);
  $("assistant-input").value = text;
  assistantProgress("Brief vorbereitet. Wähle deinen KI-Anbieter und sende den Auftrag.");
};
$("brand-export").onclick = safely(async () => {
  if (!project?.brand?.identity) throw Error("Entwickle zuerst eine Brand identity.");
  const pid = project.id;
  $("brand-export").disabled = true;
  try {
    const job = await request("/api/creative/brand/export", { project_id: pid });
    const result = await awaitJob(job, "Brand-Paket wird erstellt");
    if (project?.id !== pid) throw Error("Das Paket wurde für das ursprüngliche Projekt erstellt.");
    const details = result.details;
    $("brand-package-info").replaceChildren();
    const link = document.createElement("a");
    link.href = assetURL(details.path); link.download = "brand-package.zip"; link.textContent = "Brand-Paket herunterladen";
    const path = document.createElement("span"); path.textContent = " · Projektordner: " + details.project_dir;
    $("brand-package-info").append(link, path);
    status("Brand, Design-Tokens und Social-Media-Brief liegen im gemeinsamen Projektordner.");
  } finally { renderBrandIdentity(); }
});
$("brand-import").onclick = () => $("brand-import-file").click();
$("brand-import-file").onchange = safely(async () => {
  const file = $("brand-import-file").files[0];
  $("brand-import-file").value = "";
  if (!file || !project) return;
  if (file.size > 100000) throw Error("Identity-Datei ist zu gross.");
  const pid = project.id, revision = project.revision;
  const brand = JSON.parse(await file.text());
  const response = await request("/api/creative/brand/import", { project_id: pid, expected_revision: revision, brand });
  if (project?.id !== pid) throw Error("Identity wurde im ursprünglichen Projekt importiert.");
  project = response.result;
  $("saved").textContent = "Saved · r" + project.revision;
  render();
  status("Brand identity importiert. Änderungen sind rückgängig machbar.");
});
renderBrandIdentity();
