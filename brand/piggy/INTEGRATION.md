# Piggy Brand-System — Integration in die App

> Quelle: `K-Creative-Cloud/brand/piggy/INTEGRATION.md` (wird nach `Piggy/src/brand/INTEGRATION.md` kopiert).
> Stand 2026-09-29. **Noch nichts in der App ist umgestellt.** `src/brand/` wird von keinem Screen importiert.

## 1. Was in `src/brand/` liegt (generiert)

| Pfad | Inhalt | Braucht |
|---|---|---|
| `theme.ts` | `primitive` / `semantic` / `component` + `legacy` (= exakt `C`/`R`/`S` aus `src/constants/design.ts`) | nichts |
| `tokens.json` | aufgelöste Tokens (alle Schichten) | nichts |
| `icons/PiggyIcon.tsx` | `<PiggyIcon name="scan" mode="duotone" />`, 48 Icons, 3 Modi | `react-native-svg` (bereits installiert) |
| `icons/ioniconsMap.ts` | `ioniconToPiggy('receipt-outline')` → `{ name: 'receipt', mode: 'outline' }` | nichts |
| `icons/svg/<modus>/*.svg` | dieselben Icons als SVG (Web, Store-Grafiken) | — |
| `variants/variants.ts` | `PIGGY_VARIANTS`, `currentVariant(date)`, `VARIANT_ASSETS[id].logo/.signet` (@1x/@2x/@3x) | nichts |
| `app-icons/<id>.png` | App-Icon 1024 je Variante, `-adaptive.png` (Android-Vordergrund), `-splash.png` | — |
| `logo/` | Basis-Logo horizontal/stacked, Signet, Wortmarke (SVG + PNG) | — |
| `mascot/mascot.ts` | `MASCOT_SPRITES['cheer-happy']` usw., 256 pt (@1x/@2x/@3x) | nichts |
| `mascot/piggy.glb` | 3D-Modell mit Rig, Morph Targets, 4 Animationen (< 1 MB) | siehe §4 |
| `.generated.json` | Datei-Hashes; der nächste Sync meldet manuelle Änderungen | — |

Neu erzeugen: `bash K-Creative-Cloud/brand/piggy/build.sh --sync` (alles, inkl. Blender) oder nur kopieren:
`bash K-Creative-Cloud/scripts/export-assets.sh piggy --target brand`.

## 2. Stellen, die später umgestellt werden (nicht angefasst)

| # | Stelle | Heute | Umstellung |
|---|---|---|---|
| 1 | **App-Icon** `app.json → expo.icon` | `./assets/icon.png` = Platzhalter (Raster/Kreise) | `src/brand/app-icons/base.png` als `brand/assets/piggy/icon-master.png` ablegen → `export-assets.sh piggy --target ios` schreibt `assets/icon.png`, `adaptive-icon.png`, `splash-icon.png` (schreibt auch `design.ts` neu — Werte identisch, nur Zeitstempel). |
| 2 | **Android Adaptive** `app.json → android.adaptiveIcon` | `backgroundColor: #0A0A0F` | `foregroundImage` = `app-icons/base-adaptive.png`, `backgroundColor` = `component.appIcon.bgTo` (`#FFC247`). |
| 3 | **Splash** `app.json → splash` | `backgroundColor: #0A0A0F`, `userInterfaceStyle: "dark"` | Bild `app-icons/base-splash.png`, Hintergrund `component.splash.bg` (`#FAFAF9`). ⚠ Widerspruch klären: App-Theme ist hell, `app.json` sagt dunkel. |
| 4 | **Tab-Icons** `src/components/CustomTabBar.tsx` (`ICON_MAP` Z. 11–16, `<Ionicons>` Z. 51) | Ionicons, aktiv `C.gold`, inaktiv `C.textTertiary` | `<PiggyIcon name={…} mode={isFocused ? 'filled' : 'outline'} color={isFocused ? component.tabBar.iconActive : component.tabBar.iconInactive} />`. Mapping: index→`home`, quittungen→`receipt`, projekte→`folder`, profil→`profile`. |
| 5 | **Tab-Labels** `CustomTabBar.tsx` `tabLabelActive` / `tabLabel` | `C.gold` (2.06:1) / `C.textTertiary` (2.54:1) — **WCAG-FAIL** | `component.tabBar.labelActive` (`#9A5700`, 5.62:1) / `labelInactive` (`#6B7280`, 4.83:1). |
| 6 | **Scan-Button** `CustomTabBar.tsx` `scanEmoji` (Z. 88, 🐷-Emoji) | Emoji | `<Image source={MASCOT_SPRITES['idle-happy']} style={{ width: 48, height: 48 }} />` oder `<PiggyIcon name="piggy" mode="filled" color="#fff" />`. |
| 7 | **Scan-Quellen** `src/hooks/useScanner.ts` (`scan-outline`, `images-outline`) + `src/components/Ionicons.tsx` | eigener Ionicons-Nachbau | `ioniconToPiggy()` im Wrapper `Ionicons.tsx` nutzen → alle 23 Screens bekommen Piggy-Icons, ohne dass Screens angefasst werden. |
| 8 | **Theme** `src/constants/design.ts` (23 Importe) | `C`/`R`/`S` flach | Schritt 1: `export { legacy } from '@/brand/theme'` → identische Werte. Schritt 2: Screens auf `semantic.*` migrieren (z.B. `C.textTertiary` → `semantic.color.text.secondary` für lesbare Labels). |
| 9 | **Saison-Logo** Dashboard-Header (`app/(tabs)/index.tsx`) | kein Logo | `const v = currentVariant(); <Image source={VARIANT_ASSETS[v.id].logo} />` |
| 10 | **Leerzustände / Onboarding** | Text | Maskottchen-Sprites (`idle-sad` bei Fehlern, `cheer-happy` nach Split erledigt, `catch-surprised` beim Scannen). |

## 3. Pakete, die dafür nötig wären (nicht installiert)

| Zweck | Paket | Status |
|---|---|---|
| PiggyIcon, Logos als SVG | `react-native-svg` | ✅ schon da |
| Sprites / PNG-Logos | — (RN `Image`) | ✅ |
| Idle-Animation (GIF/WebP) | `expo-image` (animierte Formate auf iOS) | ⬜ nötig |
| 3D-Maskottchen `.glb` | `three`, `expo-gl`, `@react-three/fiber` (+ optional `@react-three/drei`), `expo-asset` | ⬜ nötig |
| Metro soll `.glb` bündeln | `metro.config.js`: `config.resolver.assetExts.push('glb')` | ⬜ Datei fehlt noch |
| Dynamische App-Icons | `expo-alternate-app-icons` (Config-Plugin) | ⬜ nötig, siehe §5 |

## 4. 3D-Modell (`piggy.glb`)

- glTF 2.0 Binär, Y-up, ~0.8 MB, keine Texturen (Farben als Materialfarben aus den Tokens).
- Armature `PiggyRig` (root, body, head, ear.L/R, arm.L/R, leg.L/R, tail, coin); Teile sind starr an Knochen gehängt (kein Skinning).
- Animationen: `pose_idle`, `pose_cheer`, `pose_catch` (Einzelframe) und `anim_idle` (48 Frames @ 24 fps, Loop).
- Morph Targets: `eye.L/R` closed · wide · sad — `brow.L/R` up · sad · happy · angry — `mouth` open · O · frown · smirk — `tongue` open · O.
  Ausdrücke = Kombinationen (siehe `EXPRESSIONS` in `brand/piggy/3d/build_piggy.py`), z.B. staunen = mouth.O + eye.wide + brow.up.
- Hinweis: Das Blinzeln ist im `.blend` als eigene Shape-Key-Aktion abgelegt und nicht Teil von `anim_idle` im glTF.

## 5. Konzept: saisonale App-Icons auf iOS (alternate icons) — nicht implementiert

1. **Auswahl begrenzen.** Alle alternativen Icons werden zur Build-Zeit ins Binary gebündelt (17 × 1024-PNG ≈ Grössenzuwachs messen). Empfehlung: Basis + 4 Saisons + 3 Highlights (1. August, Samichlaus, Neujahr).
2. **Plugin konfigurieren.** `npx expo install expo-alternate-app-icons`, in `app.json → plugins`:
   `["expo-alternate-app-icons", [{ "name": "seasonwinter", "ios": "./src/brand/app-icons/season-winter.png", "android": { "foregroundImage": "./src/brand/app-icons/season-winter-adaptive.png", "backgroundColor": "#6CC3FF" } }, …]]`
   (Icon-Namen ohne Bindestrich wählen; Mapping `variant.id → iconName` in einer kleinen Tabelle pflegen.)
3. **Build** wie gewohnt lokal auf dem MacBook (`/home/raphael/K-Dev/CLAUDE.md`): `buildNumber` in `app.json` erhöhen, `production`-Profil, Patches vorher.
4. **Laufzeit-Logik** (z.B. in `app/_layout.tsx` bei `AppState === 'active'`):
   `const v = currentVariant(new Date()); const want = v.id === 'base' ? null : ICON_NAME[v.id]; if (supportsAlternateIcons && getAppIconName() !== want) await setAlternateAppIcon(want);`
5. **UX-Grenze:** iOS zeigt bei jedem Wechsel einen System-Hinweis („Du hast das Symbol für Piggy geändert“). Deshalb: nur mit Opt-in in den Einstellungen („Saisonale Icons“), höchstens einmal pro Variantenfenster wechseln, nie im Hintergrund.
6. **Android** (Activity-Aliases) später und separat testen — Launcher-Verknüpfungen können beim Wechsel verschwinden.
7. **Review:** Alternativ-Icons müssen klar zur App gehören — erfüllt (gleiches Signet, gleiche Farben).

## 6. Bekannte offene Punkte

- Fasnacht und Ostern haben feste Fenster; die echten Daten verschieben sich jährlich → Fenster in `brand/piggy/seasons/*.json` jährlich prüfen (oder später eine Oster-Berechnung im Resolver).
- `legacy.S` (11/13/15/17/22/28/42) liegt nicht auf der Modular Scale 16 × 1.25ⁿ; die neuen `semantic.font.*` schon. Migration schrittweise.
- Die 3D-Sprites sind Standbilder aus einer festen 3/4-Kamera; andere Winkel = `build_piggy.py` anpassen und neu rendern.
