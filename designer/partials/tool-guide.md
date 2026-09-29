# Tool-Guide — K-Creative Designer

Detaillierter Leitfaden: welches Tool für welche Aufgabe, wie starten, typische Befehle.

---

## Inkscape — Vektoren, Logos, Icons

**Wann:** Logo, Icons, SVG-Assets, Illustrationen, Font-Specimens, Social Templates
**Vorteil:** Kein laufendes GUI nötig — arbeitet direkt auf SVG-Dateien
**MCP-Name:** `inkscape`

**Typische Workflow-Schritte:**
1. Neue SVG erstellen (Inkscape MCP: `create_document`)
2. Elemente hinzufügen (Rechteck, Text, Pfad)
3. Farben aus LOCKED-Palette setzen
4. Als SVG speichern + als PNG exportieren

**Export-Befehle (via MCP):**
```
"Exportiere logo.svg als PNG 1024x1024 nach assets/icons/app-icon-1024.png"
"Exportiere logo.svg als PNG 512x512 nach assets/icons/app-icon-512.png"
"Exportiere logo.svg als PNG 192x192 nach assets/icons/app-icon-192.png"
"Optimiere logo.svg mit scour"
```

**App Icon Grössen (alle auf einmal):**
- 1024×1024 (App Store / Play Store Master)
- 512×512
- 192×192 (Android)
- 180×180 (iOS @3x)
- 167×167 (iPad Pro)
- 152×152 (iPad)
- 120×120 (iPhone @2x)
- 32×32 (Favicon)
- 16×16 (Favicon small)

---

## GIMP — Raster, Foto, Texturen

**Wann:** Foto-Bearbeitung, Texturen, Hintergründe, PNG-Komposition mit Fotos
**Einschränkung:** GIMP muss laufen + MCP Server gestartet sein
**MCP-Name:** `gimp`

**GIMP starten:**
```bash
gimp   # snap-Version öffnet sich
# Dann: Tools > Start MCP Server
```

**Typische Befehle:**
```
"Öffne assets/mockups/phone.png und platziere das Logo mittig"
"Erstelle einen Glasmorphismus-Hintergrund: bg-gray-950 mit blur"
"Entferne den Hintergrund und exportiere als PNG mit Transparenz"
"Erstelle eine Textur: dunkles Leinen-Muster, 1920x1080"
```

**Wann GIMP statt Inkscape:**
- Du hast ein Foto als Basis
- Du brauchst Pixel-genaue Effekte (Blur, Rauschen, Gradient Maps)
- Du willst einen Gerät-Mockup mit echtem Screenshot zusammensetzen

---

## Blender — 3D Mockups, Produktrender

**Wann:** Gerät-Mockups (iPhone/MacBook mit App drauf), 3D Logo-Render, Animationen
**Einschränkung:** Blender Studio muss laufen
**MCP-Name:** `blender` (Port 9876)

**Blender Studio starten:**
```bash
~/K-Creative-Cloud/Blender/scripts/start-blender-studio.sh
# Browser: http://localhost:6080/vnc_lite.html
```

**Typische Brand-Aufgaben:**
```
"Erstelle einen iPhone 15 Mockup mit dem App-Screenshot auf dem Display"
"Render das Logo in 3D mit Glaseffekt auf dunklem Hintergrund"
"Animiere das Logo: von unten einfliegen, 60 Frames"
```

---

## LMMS — Sound Logo, Jingles

**Wann:** Sound Logo (2–4 Sek), kurzer Jingle, Hintergrundmusik für Videos
**Vorteil:** CLI-Rendering ohne GUI
**MCP-Name:** `lmms`

**Sound Logo Konzept:**
- Länge: 2–4 Sekunden
- Instrument: je nach Brand-Persönlichkeit
  - Synthwave-Arpeggio → modern, tech
  - Piano-Chord → premium, clean
  - Marimba-Motiv → freundlich, lernend
- Endet mit kurzer Auflösung (kein harter Cut)

**LMMS-Workflow:**
```
"Liste alle verfügbaren TripleOscillator Presets"
"Öffne LMMS und erstelle ein neues Projekt für den Sound Logo"
"Rendere das Projekt sound-logo.mmp als WAV nach assets/sounds/"
```

**Nach dem Render:**
- WAV = Master (lossless)
- MP3 = Distribution (via ffmpeg: `ffmpeg -i sound-logo.wav -q:a 2 sound-logo.mp3`)

---

## Kokoro TTS — Voiceover, Narration

**Wann:** App-Onboarding Narration, Reel-Voiceover, Brand-Film Sprache
**Script:** `/home/raphael/K-Creative-Cloud/kokoro-tts/generate_audio.py`
**Stimme:** `af_heart`, Speed 1.15x

**Direkt-Aufruf:**
```bash
cd /home/raphael/K-Creative-Cloud/kokoro-tts
python3 generate_audio.py "Willkommen bei K-Learning — dein smarter Lernbegleiter."
# Output: output.wav → umbenennen nach assets/sounds/[projekt]-voiceover.wav
```

---

## Remotion — Motion Logo, Animated Assets

**Wann:** Animiertes Logo (3–5 Sek), Social-Motion-Cards, Reel-Outro
**MCP-Name:** `remotion-shorts` (via video-shorts MCP)
**Alternativ:** `/create-reel` Skill für vollständige Reels

**Brand-Motion Konzept:**
- Motion Logo: 3–5 Sekunden, Logo baut sich auf
- Outro für Videos: "Powered by K-Creative" + Logo
- Animated Social Card: Stats oder Quotes mit Brand-Farben

---

## Kdenlive — Video-Schnitt, Brand-Film

**Wann:** Längerer Brand-Film (30s+), Zusammenschnitt von Mockup-Renders
**MCP-Name:** `kdenlive`
**Arbeitsweise:** MLT-XML Projekte + `melt` CLI für Rendering

**Kdenlive Workflow:**
```
"Erstelle ein neues Kdenlive-Projekt 1920x1080, 25fps"
"Füge assets/motion/logo-animation.mp4 als erstes Clip ein"
"Rendere das Projekt als MP4 H.264 nach assets/motion/brand-film.mp4"
```

---

## Font-Pairing — Typografie-Entscheid

**Kein MCP-Tool** — reine Research + Dokumentation

**Open-Source Font-Quellen:**
- Google Fonts (fonts.google.com) — kostenlos, self-hostbar
- Font Squirrel — freie Lizenzen
- Fontsource (npm) — für App-Integration

**Empfohlene Pairing-Strategie für K-Projekte:**
| Rolle | Empfehlung | Warum |
|-------|-----------|-------|
| Display/Headline | Inter, Geist, Plus Jakarta Sans | Modern, tech-lesbar |
| Body | Inter, DM Sans | Hohe Lesbarkeit, neutral |
| Mono/Code | JetBrains Mono, Fira Code | Erkennbar, Entwickler-Kontext |
| Akzent/Brand | Clash Display, Syne | Unverwechselbar, premium |

**Dokumentation:** Entscheid in Brand Research Log LOCKEN + Specimen in Inkscape erstellen
