---
name: K-Creative-Cloud
updated: 2026-09-29
---
## Ebene 1 — Idee
Eine selbst gehostete Creative Suite aus Open-Source-Werkzeugen (Inkscape, GIMP, Blender, LMMS, Kdenlive,
Kokoro TTS, Remotion), die Claude per MCP oder Script steuert, statt Adobe/Autodesk-Abos.
Brand-Arbeit für K-Projekte entsteht hier **reproduzierbar**: Tokens rein, Script laufen lassen, Assets raus,
per Sync in die Ziel-App.

- Single Source of Truth für Marken: `brand/tokens/<projekt>.json` (Schichten Primitive → Semantic → Component).
- Jedes Asset ist per Script erzeugbar; handgeklickte Dateien sind höchstens Zwischenstände.
- **Nie:** proprietäre Tools voraussetzen; generierte Dateien in Ziel-Apps ohne „generiert“-Markierung ablegen;
  Ziel-App-Screens stillschweigend umbauen.

## Ebene 2 — Architektur
- `brand/tokens/*.json` — Marken-Tokens. `brand/research/brand-research-log.md` — verbindliche Entscheidungen.
- `brand/piggy/` — Piggy-Brand-System (3D-Maskottchen, Logo + Varianten, Palette, Icon-Creator, Sync):
  - `lib/tokens.js` · `lib/art.js` · `lib/icons.js` — gemeinsamer Generator-Kern (Node **und** Browser).
  - `tools/build.js` (CLI), `tools/sync.js`, `tools/test.js`, `build.sh` (Orchestrierung inkl. Blender).
  - `3d/build_piggy.py` (Blender headless), `seasons/*.json` (Varianten-Daten), `icons/` (Quellen + Style),
    `creator/index.html` (Live-Editor), `dist/` (generiert, gitignored).
- `scripts/export-assets.sh` — sync-design-Pipeline (Targets ios/web/dmg/brand) in K-Dev-Projekte.
- `designer/` — Asset-Registry + Tool-Guide; `designer/assets/` hält Kopien der Kern-Assets.
- `Blender/`, `inkscape-mcp/`, `gimp-mcp/`, `lmms-mcp/`, `kdenlive-mcp/`, `remotion-mcp/` — Werkzeug-Anbindungen.
- Kopplungen: Resolver-Logik existiert in `lib/tokens.js` und generiert in `Piggy/src/brand/variants/variants.ts`
  (Parität per `tools/test.js`); Icon-Rollenlogik in `lib/icons.js` und generiert in `PiggyIcon.tsx`.
- Entscheidungen: `docs/adr/0001-varianten-als-datenschicht.md`.

## Idee-Historie
- 2026-09-29 — Workspace angelegt; Piggy-Brand-System mit fünf Partials (3D, Logo-Saisons, Palette, Icon-Creator, Sync)
