# ADR 0001: Logo-Varianten als Datenschicht über dem Basis-Logo

## Status
Accepted — 2026-09-29

## Kontext
Piggy soll wie Clash of Clans saisonale und monatliche Logo-/Icon-Varianten bekommen (1. August, Fasnacht, Ski,
Samichlaus …): mindestens 4 Saisons und 12 Monate, jeweils Logo, App-Icon und Splash. Gleichzeitig ist die Palette
editierbar und soll überall durchschlagen. Würde jede Variante als eigene Grafik gepflegt, wären das 16 × 5 Dateien,
die bei jeder Palettenänderung, jedem Signet-Feinschliff und jeder neuen Grösse von Hand nachgezogen werden müssten.

## Entscheidung
- Es gibt **ein** Basis-Logo (Signet + Wortmarke) als Code (`brand/piggy/lib/art.js`).
- Eine Variante ist eine JSON-Datei in `brand/piggy/seasons/` mit nur vier Dingen:
  `palette` (Token-Overrides als Pfad → Wert oder `{Referenz}`), `accessories` (IDs aus einer Bibliothek),
  `background` (Deko-IDs, nur App-Icon/Splash) und `valid` (MM-DD-Fenster, `kind` month|season).
- Ein Generator rendert daraus alle Formate; ein Resolver `currentVariant(date)` wählt:
  Monat schlägt Saison, Gleichstand auf der entscheidenden Ebene → Basis, kein Treffer → Basis.
- Die Resolver-Logik wird für die App als TypeScript generiert; ein Test prüft die Parität.

## Begründung
- **Konsistenz:** Signet-Geometrie ist in jeder Variante identisch; die Marke bleibt erkennbar.
- **Palette schlägt durch:** Overrides laufen durch dieselbe Token-Auflösung wie die Basis.
- **Billig zu erweitern:** eine neue Variante ist eine 15-Zeilen-JSON-Datei; ein neues Accessoire ist eine Funktion.
- **Prüfbar:** Varianten werden beim Build validiert (Schema, IDs, Fenster im Monat, Splash-Kontrast).
- **Gleichstand → Basis** statt Priorität/Reihenfolge: überlappende Pflege-Fehler fallen auf die sichere Basis
  zurück, statt zufällig eine Variante zu zeigen.

## Konsequenzen
- Positiv: 16 Varianten × (Logo, Stacked, Signet, App-Icon, Adaptive, Splash, Splash-Screen, @1x–@3x) in ~30 s.
- Negativ: Accessoires sind Vektor-Code in `art.js` — neue Motive brauchen Code statt Zeichenprogramm; frei
  gezeichnete Einzelstücke passen nicht ins Modell. Bewegliche Feiertage (Ostern, Fasnacht) haben feste Fenster.
- Resolver existiert zweimal (JS + generiertes TS) — abgesichert durch `tools/test.js`.

## Was passiert bei Austausch?
1. `seasons/*.json` bleiben als Datenbeschreibung nutzbar (z.B. für einen anderen Renderer).
2. `renderLogo/renderAppIcon/renderSplash` in `art.js` durch den neuen Renderer ersetzen; `ACCESSORIES`-IDs beibehalten.
3. `variants/variants.ts` in der App bleibt kompatibel, solange `id`/`kind`/`valid` gleich bleiben.
