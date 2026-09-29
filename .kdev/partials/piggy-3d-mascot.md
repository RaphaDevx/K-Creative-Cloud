---
name: Piggy 3D-Maskottchen
status: working
trigger: build.sh läuft (ohne --no-3d) oder jemand ändert brand/piggy/3d/build_piggy.py bzw. Maskottchen-Tokens
files:
  - brand/piggy/3d/build_piggy.py
  - brand/piggy/build.sh
  - brand/tokens/piggy.json
depends: [piggy-palette]
updated: 2026-09-29
---
## Ebene 1 — Idee
Piggy ist ein rundes, weiches Sparschwein-Maskottchen im Mobile-Game-Stil: grosser Kopf, kurze Beine,
glänzende Vinyl-Oberfläche mit Glanzlichtern, grosse Augen mit Lichtreflexen, Rougebäckchen und ein
**Münzschlitz oben auf dem Kopf** als Markenzeichen. Es entsteht vollständig aus einem Script, damit eine neue
Palette nach einem Neu-Render automatisch ein neues Schwein ergibt.

Es kann Gefühle zeigen (freuen, staunen, traurig, zwinkern) und Posen einnehmen (idle, jubeln, Münze fangen),
und es gibt eine kurze Idle-Animation (Wippen, Ohrenwackeln, Blinzeln).

**Nie:** Farben im Script hart codieren; ein handgeklicktes `.blend` als Quelle behandeln; Clash-of-Clans- oder
Duolingo-Figuren nachbauen.

## Ablauf
1. WENN `build.sh` läuft DANN löst `tools/build.js` die Tokens auf → `dist/tokens/piggy.resolved.json`.
2. WENN die Tokens aufgelöst sind DANN baut Blender headless Geometrie, Rig, Shape Keys, Aktionen und Materialien
   aus `component.mascot.*` und speichert `dist/3d/piggy.blend`.
3. WENN das Modell steht DANN wird `piggy.glb` exportiert (Subdivision auf Stufe 1, < 1 MB).
4. WENN Sprites gerendert werden DANN rendert Cycles jede Pose/jeden Ausdruck in 2× Grösse (kein Denoiser in
   dieser Blender-Build) und `build.sh` skaliert auf @3x/@2x/@1x (768/512/256 px) herunter.
5. WENN die Idle-Animation gerendert ist DANN erzeugt ffmpeg WebM (Alpha), MP4 und GIF.
6. SONST (Blender-Fehler) bricht `build.sh` ab und zeigt die letzten Zeilen von `dist/3d/blender.log`.

```mermaid
graph LR
  T[piggy.json] --> R[build.js resolve] --> B[Blender build_piggy.py]
  B --> BL[piggy.blend] & G[piggy.glb] & S[Sprites 2x] & A[anim/*.png]
  S -->|convert Lanczos| SP[@1x/@2x/@3x]
  A -->|ffmpeg| V[webm/mp4/gif]
```

## Ebene 2 — Umsetzung
- `build_piggy.py`
  - `head_surface()` / `face_frame()` — Kopf-Ellipsoid; Gesichtsteile werden auf die Oberfläche projiziert.
  - `build_eye()` — Auge + 2 Glanzlichter in einem Mesh; Shape Keys `closed` (^-Bogen), `wide`, `sad`.
  - `build_brow()` — Röhre, Basis ist unsichtbar eingeklappt; Keys `up`, `sad`, `happy`, `angry`.
  - `mouth_outline()` / `build_mouth()` — 48-Punkte-Umriss mit gleicher Topologie für `smile` (Basis), `open`,
    `O`, `frown`, `smirk`; Zunge als eigenes Objekt mit Keys.
  - `build_parts()` — Kopf, Körper, Bauch, Schnauze (Bevel-Puck), Nasenlöcher, Ohren (verjüngte Ellipsoide),
    Wangen, Münzschlitz + Rand, Beine/Hufe, Arme/Hände, Ringelschwanz, Münze.
  - `BONES` / `PARENT` / `build_rig()` — Armature, Teile starr an Knochen gehängt (kein Skinning).
  - `POSES` (inkl. `aim`-Richtungsvektoren für Arme), `EXPRESSIONS`, `apply_pose()`, `apply_expression()`.
  - `key_pose_action()`, `build_idle_action()` (48 Frames), Blinzeln als geparkte Shape-Key-Aktion `blink_L/R`.
  - `setup_stage()` — Key/Fill/Rim/Top + spekular-only `Gloss`-Licht, Shadow Catcher, 85-mm-Kamera 3/4-Ansicht.
  - `export_glb()` — Pose- und Idle-Aktionen als NLA-Spuren → glTF-Animationen.
- `build.sh` — Aufruf, Sprite-Skalierung, ffmpeg, Kopie nach `designer/assets/{mockups,motion}`.
- Kopplung: Sprite-Namen `piggy-mascot-<pose>-<ausdruck>` werden von `tools/build.js` (`mascot.ts`) und vom Creator gelesen.

## Akzeptanz
- [x] Modell entsteht aus Script; `piggy.blend` + `piggy.glb` (≈0.8 MB) reproduzierbar
- [x] Materialfarben nur aus Tokens (Demo: Lavendel-Palette ergibt lila Schwein)
- [x] Shape Keys für freuen, staunen, traurig, zwinkern; Posen idle, jubeln, Münze fangen
- [x] Sprites @1x/@2x/@3x transparent, 7 Kombinationen
- [x] Idle-Animation als PNG-Sequenz + WebM/MP4/GIF
- [x] Vorschauen selbst angeschaut und iteriert (Belichtung, Schlitz, Arme, Mund, Glanzlichter)
- [ ] Echtes Skinning/Deformation (Körper biegt sich) — bewusst nicht: starre Teile sind headless robust
- [ ] Accessoires der Saison-Varianten auch in 3D
- [ ] Rauschen: ohne Denoiser nur durch 2×-Supersampling reduziert; Schattenkante bleibt leicht körnig

## Idee-Historie
- 2026-09-29 — Partial angelegt; Kopf-Schlitz statt Rücken-Schlitz, damit er in der Frontansicht sichtbar ist
