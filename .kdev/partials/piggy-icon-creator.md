---
name: Piggy Icon- & Style-Creator
status: working
trigger: jemand ändert icons/style.json, icons/sources.json oder öffnet creator/index.html
files:
  - brand/piggy/icons/style.json
  - brand/piggy/icons/sources.json
  - brand/piggy/lib/icons.js
  - brand/piggy/creator/index.html
  - brand/piggy/tools/build.js
depends: [piggy-palette, piggy-logo-seasons]
updated: 2026-09-29
---
## Ebene 1 — Idee
Ein eigenes, weiches Icon-Set, das zum Schwein passt: runde Enden, runde Ecken, kräftiger Strich. Die Icons sind
keine gezeichneten Dateien, sondern **Quellen aus Primitiven** (Kreis, Rechteck, Polygon, Pfad, Zahnrad, Stern) auf
einem 24er-Raster, die über eine **Style-Definition** (Strichstärke, Eckenradius, Füllung outline/filled/duotone,
Palette-Token) gerendert werden. Ein Regler im Creator ändert das ganze Set.

Der Creator ist eine statische Seite: Palette und Icon-Style live ändern, Logo, Varianten, Icons und Kontrast sofort
sehen, Ergebnis als JSON exportieren. Er nutzt denselben Code wie die CLI.

**Nie:** SVG-Dateien von Hand editieren (werden überschrieben); Farbwerte in `style.json` statt Token-Pfaden.

## Ablauf
1. WENN jemand den Stil ändern will DANN öffnet er `brand/piggy/creator/index.html` (file:// genügt).
2. WENN ein Regler/Farbwähler bewegt wird DANN rendert die Seite per `requestAnimationFrame` neu und merkt
   den Entwurf in `localStorage`.
3. WENN „exportieren“ DANN lädt der Browser `piggy.json` bzw. `style.json` herunter → Dateien ersetzen.
4. WENN `build.js` läuft DANN entstehen `dist/icons/svg/<modus>/*.svg`, Übersicht und `rn/icons/PiggyIcon.tsx`.
5. SONST (unbekanntes Primitiv, Token-Pfad fehlt) Fehler mit Namen.

## Ebene 2 — Umsetzung
- `icons/sources.json` — 48 Icons, Gruppen nav/action/status/object/brand; Rollen `base` / `detail` / `dot`,
  `in: true` = liegt auf der Fläche (filled → Aussparung); `ionicons` = ersetzte Ionicons-Namen (für Migration).
- `icons/style.json` — `piggy-soft`: Strich 2, Radius 3, duotone, Palette `component.icon.*`.
- `lib/icons.js` — `roundedPolygon()`, `gearPoints()`, `starPoints()`, `geom()`, `iconElements()` (Rollen → Farbrollen),
  `elementsToSvg()`, `styleColors()`, `renderIcon()`.
- `tools/build.js` — SVGs, `piggy-icons-overview.png`, `PiggyIcon.tsx` (Geometrie + Rolle, Modus zur Laufzeit),
  `ioniconsMap.ts`, `creator/data.js`.
- `creator/index.html` — lädt `lib/*.js` + `data.js`; Palette-Tab (alle Primitive), Style-Tab (Regler, Select),
  Varianten-Raster mit Datum → Resolver, Icon-Raster, Modi-Vergleich, Kontrast-Tabelle, Sprite-Galerie.
- Kopplung: Rollen-Logik steht in `iconElements()` **und** in `PiggyIcon.tsx` (generiert, Kommentar verweist darauf).

## Akzeptanz
- [x] Icon-Set für Navigation und Kernaktionen (Scan, Quittung, Split, Freunde, Profil, Statistik, Einstellungen,
      Hinzufügen, Kamera, Teilen …) + alle in `Piggy/app` und `src/` genutzten Ionicons abgedeckt
- [x] Generiert aus Style-Definition; drei Füllmodi
- [x] CLI (`build.js`) + statische HTML-Oberfläche mit Live-Vorschau und JSON-Export/-Import
- [x] Output: SVGs + `<PiggyIcon name="scan" />` (react-native-svg), `tsc --strict` fehlerfrei
- [ ] Creator kann neue Icon-Quellen nicht grafisch zeichnen (nur Style/Palette) — Quellen bleiben JSON
- [ ] 3D-Sprites reagieren im Creator nicht live auf die Palette (brauchen Blender-Render)

## Idee-Historie
- 2026-09-29 — Partial angelegt; „split“ als geteilte Münze statt Pfeile
