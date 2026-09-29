---
name: Piggy Sync nach Piggy/src/brand
status: working
trigger: export-assets.sh piggy --target brand oder build.sh --sync
files:
  - scripts/export-assets.sh
  - brand/piggy/tools/sync.js
  - brand/piggy/INTEGRATION.md
depends: [piggy-palette, piggy-icon-creator, piggy-logo-seasons, piggy-3d-mascot]
updated: 2026-09-29
---
## Ebene 1 — Idee
Ein Befehl bringt alles, was die App braucht, in **einen eigenen, klar als generiert markierten Ordner**
`Piggy/src/brand/`: Tokens, Theme-Datei, Icon-Komponente, SVGs, Varianten + Resolver, Logos, App-Icons,
Maskottchen-Sprites und `.glb`. Die App wird dabei **nicht** umgebaut: welche Stellen später umgestellt werden
und welche Pakete dafür nötig sind, steht in `INTEGRATION.md`.

**Nie:** ausserhalb von `src/brand/` schreiben; Dateien löschen; Abhängigkeiten installieren; Builds/TestFlight auslösen.

## Ablauf
1. WENN `export-assets.sh piggy --target brand` läuft DANN werden Token-Referenzen aufgelöst.
2. WENN noch kein Build existiert DANN startet es `build.sh --no-3d`.
3. WENN der Build da ist DANN kopiert `sync.js` nach `<Piggy>/src/brand/` und schreibt `README.md` + `.generated.json`.
4. WENN eine Zieldatei seit dem letzten Sync von Hand geändert wurde DANN Warnung (Hash-Vergleich), dann überschreiben.
5. SONST (Datei wird nicht mehr generiert) nur melden, nicht löschen.

## Ebene 2 — Umsetzung
- `scripts/export-assets.sh` — `export_brand()`, Dispatch `brand)`, Auflösung via `lib/tokens.js`;
  `all` enthält `brand` bewusst nicht (verändert sonst `assets/` und `design.ts` mit).
- `brand/piggy/tools/sync.js` — Plan aus `dist/rn`, `dist/icons/svg`, `dist/variants/<id>`, `dist/logo`,
  `dist/3d/sprites`, `piggy.glb`, `INTEGRATION.md`; Guard: Ziel muss Expo-Projekt (app.json) sein.
- Ziel: `theme.ts`, `tokens.json`, `index.ts`, `icons/{PiggyIcon.tsx,ioniconsMap.ts,index.ts,svg/}`,
  `variants/{variants.ts,index.ts,<id>/logo|signet(@2x|@3x).png}`, `app-icons/`, `logo/`, `mascot/`.
- Prüfung: `npx tsc --noEmit` über `src/brand/**` in Piggy (strict, react-native-svg-Typen) ohne Fehler.

## Akzeptanz
- [x] Ein Befehl synchronisiert Tokens, Theme, Icons, Icon-Komponente, Sprites, `.glb`, Varianten-Resolver
- [x] Zielordner `Piggy/src/brand/` mit README „GENERIERT“ und Manifest
- [x] Keine Screens umgebaut, keine Pakete installiert, kein Build, kein Commit
- [x] Integrationsdoku mit Umstellstellen, Paketen und Konzept für iOS-Alternate-Icons
- [ ] Umstellung der App selbst (App-Icon, Splash, Tab-Icons, Theme) — nächster Schritt, eigene Session

## Idee-Historie
- 2026-09-29 — Partial angelegt; sync-design um Target `brand` erweitert statt neues Tool
