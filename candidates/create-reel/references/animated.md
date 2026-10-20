## PIPELINE — MODUS A

### Schritt 1: Storyboard schreiben

```python
SCRIPT_JSON = {
  "title": "Thema in 100 Sekunden",
  "scenes": [
    {
      "id": 0,
      "type": "hook",            # hook / fact / explanation / warning / tip / takeaway
      "headline": "SHOCKING FACT IN CAPS",
      "subtext": "Ein klarer Satz.",
      "emoji": "📊",
      "spoken": "Gesprochener Text für TTS...",
      "accent_hex": "#FF4444"
      # optional: "viz": { ... }  ← nur wenn Partial geladen + Typ bekannt
    }
  ]
}
```

**Regeln:**
- 5–8 Szenen, je 8–18 Sekunden, total ~240–280 Wörter
- Hook (Szene 0): kontraintuitiver Fakt oder kühne Behauptung
- `viz`-Feld nur setzen wenn das passende Partial geladen wurde

**Accent-Farben:**
| type | hex |
|------|-----|
| hook | #FF4444 |
| fact | #FFD700 |
| explanation | #4FC3F7 |
| warning | #FF7043 |
| tip | #66BB6A |
| takeaway | #CE93D8 |

### Schritt 2: run_reel.py schreiben + starten

> **WICHTIG:** Niemals `create_short` aus `pipeline.py` verwenden — das ruft die Anthropic API auf und schlägt ohne API-Key fehl. Immer die drei Module direkt importieren: `voice` (`synthesize`), `frame_render`, `video_assemble`.

```python
#!/usr/bin/env python3
import sys, json, os, tempfile, time
from pathlib import Path

# Use an interpreter with the required media dependencies; do not inject unrelated site-packages.
sys.path.insert(0, "/home/raphael/K-Dev/Projekte/K-Creative-Cloud/video-shorts-mcp")

from voice import synthesize  # lokal; channel=<Kanal-ID> bindet die Persona-Stimme
from frame_render import render_scene_frame
from video_assemble import assemble_video

OUTPUT_DIR = Path.home() / "renders" / "shorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCRIPT = { ... }  # Vollständiges Storyboard von Schritt 1 hier einfügen

scenes = SCRIPT["scenes"]
CHANNEL = "mein-kanal"   # Kanal-ID → Persona → fixierte DE/EN-Stimme (voice-data/channels/)
output_name = "thema.mp4"
# Sprache wird je Segment erkannt; englische Fachbegriffe aus voice-data/lexicon.json oder {en:Begriff}.
# Deutsch → Piper (lokal), Englisch → Kokoro (lokal). Alles offline.

t_start = time.time()
tmpdir = tempfile.mkdtemp(prefix="kcloud_short_")

print(f"[1/3] TTS (Kanal {CHANNEL}, lokal)...")
for i, scene in enumerate(scenes):
    audio_path = os.path.join(tmpdir, f"audio_{i:03d}.wav")
    duration = synthesize(scene["spoken"], audio_path, channel=CHANNEL)["duration"]
    scene["_audio_path"] = audio_path
    scene["_duration"] = duration
    print(f"      Scene {i}: {duration:.1f}s — {scene['headline'][:40]}")

total_audio = sum(s["_duration"] for s in scenes)
print(f"      Total: {total_audio:.1f}s")

print(f"[2/3] Frames rendern...")
for i, scene in enumerate(scenes):
    frame_path = os.path.join(tmpdir, f"frame_{i:03d}.png")
    render_scene_frame(scene, frame_path, i, len(scenes), format="portrait")
    scene["_frame_path"] = frame_path

print(f"[3/3] Video zusammenbauen...")
output_path = str(OUTPUT_DIR / output_name)
scene_data = [
    {"frame": s["_frame_path"], "audio": s["_audio_path"], "duration": s["_duration"]}
    for s in scenes
]
assemble_video(scene_data, output_path)

elapsed = time.time() - t_start
print(f"\nFertig in {elapsed:.0f}s → {output_path}")
print(json.dumps({"output": output_path, "scenes": len(scenes),
                  "total_duration_s": round(total_audio, 1),
                  "render_time_s": round(elapsed, 1)}, indent=2))
```

Ausführen: `/storage/projekte/ki_pipeline_env_312/bin/python3 /tmp/reel_pipeline/run_reel.py`
(Stimmen rein lokal: Piper DE + Kokoro EN; Venv mit `piper-tts`, `kokoro-onnx`, `langid`.)

### Schritt 3: Bereitstellung

Dem gemeinsamen Upload-Vertrag im create-reel-Einstieg folgen. Keine fest kodierten Kurs-Deploy-Scripts oder automatischen git pushes für andere Inhalte verwenden.

K-Learning (aktueller Weg, getestet): `K-Creative-Cloud/video-shorts-mcp/publish_k_learning.py` — Upload in Bucket `videos`
(anon key darf nur INSERT, kein Überschreiben/x-upsert: neue Version = neuer Dateiname) und Registrierung über die RPC
`k_import_content` (p_kind=video). Env: `source /home/claude/.keys/tokens.env`, Import-Token über `K_IMPORT_TOKEN_FILE`.
Die alten `K-Learning/tools/reels/*_deploy.py` (feed-data.js unter /home/raphael/K-Learning, git push) sind veraltet.
`type` = `localvideo` setzen (alle bestehenden Zeilen; der Feed-Fallback filtert darauf).

---

## PIPELINE — MODUS C (Beat-Reels mit Formeln/Tabellen/Plots) — für Rechenstoff bevorzugt

`video-shorts-mcp/beat_reel.py`: Beat = ein gesprochener Satz + Elemente, die ab dann sichtbar werden (Mathtext-Formeln,
Tabellen, Callouts, Matplotlib-Plots). Bild/Ton synchron, SRT + Thumbnail inklusive. Beispiele: `K-Creative-Cloud/reels/om/*.py`.
Bauen: `cd K-Creative-Cloud/reels/om && REEL_OUT=~/renders/om /storage/projekte/ki_pipeline_env_312/bin/python3 build.py om_eoq --frames`
Zahlen im Reel immer im Skript berechnen und per `assert` gegen die Handrechnung/Formelsammlung prüfen.
Roboto hat keine Pfeile (→ ⇒): in Texten vermeiden. Zahlen/Abkürzungen ausgeschrieben bzw. buchstabiert sprechen lassen ("M A D").
Prüfen: Frames ansehen (`--frames`), ffprobe (1080x1920, h264+aac), volumedetect, Whisper-Transkript (`whisper x.mp4 --model base --language de`).

---

### Schritt 4: Ergebnis berichten

Output-Pfad · Renderdauer · Szenenanzahl · Deploy-Status

---

## PIPELINE — MODUS B (Remotion MCP)

Nur wenn `remotion-shorts` MCP aktiv:

```python
create_animated_reel(topic="[Thema]", voice="bm_george",
    extra_instructions="HSG Lernvideo. Prüfungsrelevant.")
```

Viz-Typen via `viz`-Feld: `latex`, `normal_dist`, `skewed_dist`, `histogram`, `bar_chart`

---

## STIMMEN & SPRACHE

Die Voice-Schicht wählt je Sprachsegment die Engine der Persona:

| Sprache | Engine | Stimme | Qualität |
|---------|--------|--------|----------|
| Deutsch | **Piper** (lokal) | z. B. `de_DE-thorsten-medium` | Natürlich, CPU-schnell |
| Englisch | **Kokoro ONNX** (lokal) | z. B. `am_adam` | Gut, offline |

**Mischsprache:** Satzsprache via langid, englische Begriffe aus dem Lexikon oder per `{en:…}` Markup werden englisch gesprochen.

**Stimmen** werden pro Persona in `voice-data/personas/<id>.json` festgelegt (z. B. `de_DE-kerstin-low` für weiblich Deutsch). Edge TTS wurde entfernt.

**Englische Kokoro-Stimmen:**
| Voice | Stil |
|-------|------|
| `am_adam` | Tief, autoritativ |
| `af_heart` | Warm, expressiv, weiblich |
| `af_nova` | Energetisch, jung |
| `bm_george` | Britisch, Professor-Stil |

---

## LOCATIONS

| Ressource | Pfad |
|---|---|
| Pipeline | `/home/raphael/K-Dev/Projekte/K-Creative-Cloud/video-shorts-mcp/` |
| Remotion | `/home/raphael/K-Dev/Projekte/K-Creative-Cloud/remotion-mcp/` |
| Stimmen | `voice-models/` (Piper), `kokoro-tts/` (Kokoro), `voice-data/` (Personas/Kanäle/Lexikon) |
| Python Venv | `/storage/projekte/ki_pipeline_env_312/bin/python3` |
| Output | `~/renders/shorts/` |
| Partials | `/home/raphael/K-AI/skills/partials-*/` |

---

## FALLBACK

1. Stimme fehlt: `ls voice-models/piper kokoro-tts` und `python -m voice.registry verify` (im Ordner video-shorts-mcp)
2. FFmpeg fehlt: `ffmpeg -version`
3. Pipeline test: `/storage/projekte/ki_pipeline_env_312/bin/python3 -c "import kokoro_onnx; print('ok')"`
