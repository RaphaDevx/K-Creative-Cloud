---
name: Piggy Palette & Token-Schichten
status: working
trigger: jemand ändert brand/tokens/piggy.json oder exportiert eine Palette aus dem Creator
files:
  - brand/tokens/piggy.json
  - brand/tokens/.history/piggy.v1-flat.json
  - brand/piggy/lib/tokens.js
  - scripts/export-assets.sh
depends: []
updated: 2026-09-29
---
## Ebene 1 — Idee
Eine einzige Token-Datei beschreibt die ganze Marke in drei Schichten: **Primitive** (reine Werte: Farbrampen,
4pt-Abstände, Radien, Modular Scale 16 × 1.25ⁿ) → **Semantic** (Bedeutung: Text, Hintergrund, Marke, Icon, Status,
Maskottchen, Accessoires) → **Component** (Tab-Bar, Button, Card, Icon, Maskottchen, Logo, App-Icon, Splash).
Wer eine Primitive ändert, ändert per Referenz alles: 3D-Materialien, Logos, Varianten, Icons, App-Theme.
Text-/Hintergrund-Paare müssen WCAG AA erfüllen; bewusste Ausnahmen werden dokumentiert, nicht versteckt.

**Nie:** Hex-Werte in Semantic/Component (Lint bricht); Legacy-Werte stillschweigend ändern (die App nutzt sie heute).

## Ablauf
1. WENN jemand eine Farbe ändern will DANN ändert er eine **Primitive** (Datei oder Creator → Export `piggy.json`).
2. WENN `build.js` läuft DANN `resolveTokens()` → `lintTokens()` (4er-Raster, 8er-Grössen, Modular Scale,
   Zeilenhöhen auf 4pt, keine Rohwerte ausserhalb Primitive) → `contrastReport()` über `contrastPairs`.
3. WENN ein Paar FAIL ist DANN steht es im Report; `--strict` bricht ab.
4. WENN `export-assets.sh` läuft DANN werden Referenzen vorher aufgelöst, damit `design.ts` (ios) weiter funktioniert.
5. SONST (Referenz fehlt / Zyklus) Abbruch mit Pfadangabe.

## Ebene 2 — Umsetzung
- `brand/tokens/piggy.json` — Schema `piggy-tokens/2`. Neue Primitive: pink 200/400/500/600/700/800, gold 300/600/700,
  gray 600, cocoa, green 700, red 700, swiss.red, sky, mint, violet, leaf; `space`, `radius`, `type.scale`, `size`.
- `lib/tokens.js` — `resolveTokens()`, `applyOverrides()`, `lintTokens()`, `contrastRatio()`, `contrastReport()`.
- `tools/build.js` → `dist/palette/contrast-report.md|json`; `dist/rn/theme.ts` (primitive/semantic/component/legacy).
- `scripts/export-assets.sh` — neuer Schritt „Token-Referenzen auflösen“ vor allen Targets; `EXPORT_PROJECT_DIR`.

### Migration v1 (flach) → v2 (Schichten)
| v1-Schlüssel | v2 | Wert |
|---|---|---|
| `colors.*` (17 Farben) | Alias → `semantic.color.*` → `primitive.color.*` | **identisch** (per Test geprüft) |
| `radius.xs…xxl` | Alias → `primitive.radius.8…32` | identisch (12/20 sind 4pt-Halbstufen, erlaubt) |
| `fontSize.*` | bleibt flach (deprecated) | identisch; liegt **nicht** auf der Modular Scale → neue `semantic.font.*` nutzen |
| `shadow`, `icon` | unverändert | `icon.note` ergänzt |
Original: `brand/tokens/.history/piggy.v1-flat.json`. Beweis: `export-assets.sh piggy --target ios` in einen
Testordner erzeugt ein `design.ts`, das bis auf den Zeitstempel identisch ist.

### Kontrast (Stand 2026-09-29)
- 15 PASS · 2 EXEMPT · 3 FAIL — die 3 FAIL sind **Legacy-Nutzungen in der App**: `C.gold` als Tab-Label (2.06:1)
  und Tab-Icon, `C.textTertiary` als Label (2.54:1). Ersatz-Tokens: `component.tabBar.labelActive` (#9A5700, 5.62),
  `iconActive` (#C77700, 3.46), `iconInactive`/`labelInactive` (#6B7280, 4.83).
- EXEMPT: `text.tertiary` nur für deaktivierte Elemente; `text.secondary` auf `bg.brand` (4.38) → `text.strong` nutzen.

## Akzeptanz
- [x] Primitive → Semantic → Component, Legacy-Werte unverändert (Test)
- [x] Paletten-Wechsel schlägt durch: 3D, Logos, Varianten, Icons, `theme.ts` (Lavendel-Demo)
- [x] WCAG-AA-Report automatisch bei jedem Build
- [x] 8pt/4pt-Raster, Modular Scale und Schichten-Regel per Lint erzwungen
- [ ] App nutzt die AA-konformen Tab-Tokens (Screens bewusst nicht umgebaut)
- [ ] Dark-Mode-Semantik (app.json sagt `dark`, Theme ist hell) — offen

## Idee-Historie
- 2026-09-29 — Partial angelegt; v1 flach → v2 Schichten mit Legacy-Aliasen migriert
