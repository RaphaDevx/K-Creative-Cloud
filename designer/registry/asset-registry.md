# Asset Registry — K-Creative Designer
_Verbindliche Liste aller erstellten Brand-Assets. Nach jeder Erstellung updaten._

---

## Status-Übersicht

| Phase | Fortschritt |
|-------|-------------|
| Phase 1 — Fundament | 0/3 |
| Phase 2 — Digitale Präsenz | 0/4 |
| Phase 3 — Identität | 0/3 |
| Phase 4 — System | 0/2 |
| **Total** | **0/12** |

---

## Phase 1 — Fundament

| Asset | Status | Datei | Erstellt | Tool |
|-------|--------|-------|----------|------|
| Farb-Entscheid (LOCKED) | ⏳ offen | brand-research-log.md | — | k-creative-brand |
| Typografie-Entscheid | ⏳ offen | — | — | — |
| Wordmark / Logo | ⏳ offen | — | — | Inkscape |

---

## Phase 2 — Digitale Präsenz

| Asset | Status | Datei | Erstellt | Tool |
|-------|--------|-------|----------|------|
| App Icon (alle Grössen) | ⏳ offen | — | — | Inkscape |
| Favicon | ⏳ offen | — | — | Inkscape |
| Social Profilbild | ⏳ offen | — | — | Inkscape |
| Social Banner | ⏳ offen | — | — | Inkscape |

---

## Phase 3 — Identität

| Asset | Status | Datei | Erstellt | Tool |
|-------|--------|-------|----------|------|
| Sound Logo | ⏳ offen | — | — | LMMS |
| Motion Logo | ⏳ offen | — | — | Remotion |
| 3D Brand Mockup | ⏳ offen | — | — | Blender |

---

## Phase 4 — System

| Asset | Status | Datei | Erstellt | Tool |
|-------|--------|-------|----------|------|
| Font-Specimen | ⏳ offen | — | — | Inkscape |
| Brand Guidelines PDF | ⏳ offen | — | — | brand/build.sh |

---

## Piggy (brand/piggy — generiert, `bash brand/piggy/build.sh`)

| Asset | Status | Datei | Erstellt | Tool |
|-------|--------|-------|----------|------|
| Farb-System (Tokens v2, Schichten) | ✅ (Werte EXPLORING, siehe Research Log) | brand/tokens/piggy.json | 2026-09-29 | k-creative-brand / lib/tokens.js |
| Wordmark / Logo (horizontal, stacked, Signet) | ✅ | designer/assets/logo/piggy-*.svg/.png | 2026-09-29 | Node → Inkscape |
| App Icon 1024 (+ 16 Varianten in dist) | ✅ | designer/assets/icons/piggy-icon-1024.png | 2026-09-29 | Node → Inkscape |
| UI-Icon-Set (48 × 3 Modi) | ✅ | designer/assets/icons/piggy-uiicons-overview.png | 2026-09-29 | lib/icons.js |
| 3D-Maskottchen (Sprites, .glb, .blend) | ✅ | designer/assets/mockups/piggy-mascot-*.png | 2026-09-29 | Blender (Script) |
| Motion: Idle-Animation | ✅ | designer/assets/motion/piggy-mascot-idle.mp4 (gitignored *.mp4; Quelle dist/3d) | 2026-09-29 | Blender + ffmpeg |
| Favicon / Social / Sound Logo / Brand Guide PDF | ⏳ offen | — | — | — |

---

## Asset-Dateien (Verzeichnis)

```
/home/raphael/K-Creative-Cloud/designer/assets/
├── logo/         (leer)
├── icons/        (leer)
├── typography/   (leer)
├── sounds/       (leer)
├── motion/       (leer)
├── social/       (leer)
└── mockups/      (leer)
```

---

## Changelog

| Datum | Was | Asset |
|-------|-----|-------|
| 2026-08-13 | Registry erstellt | — |
| 2026-09-29 | Piggy-Brand-System: Logo, App-Icon + Varianten, UI-Icons, 3D-Maskottchen, Idle-Animation | Piggy |
