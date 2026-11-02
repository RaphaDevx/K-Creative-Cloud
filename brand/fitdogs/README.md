# FitDogs (Shiba "Shiro", Dobermann "Brutus")

Zwei muskulöse Hunde-Maskottchen im Esport-Sticker-Look (dicke Outline, Cel-Shading, farbiger Aura-Ring) als
**zwei Skins auf einem gemeinsamen Skelett** (`fitdogs-v1`). Eigene Interpretation im Stil einer Referenz, kein Tracing.
Die Namen Shiro und Brutus sind **Platzhalter** (`placeholder_name: true`).

## Aufruf

```bash
blender -b -P brand/fitdogs/3d/build_dogs.py -- --skin shiba|dobermann|all --out brand/fitdogs/dist/3d \
    [--render none|preview|all|icons] [--samples N] [--size 768] [--icon-size 1024] [--no-aura]
python3 brand/fitdogs/tools/test_fitdogs.py        # schneller Test, gibt "N ok" aus (ca. 30 s)
```

`--render all` (ca. 1 min, 32 Samples) erzeugt je Skin Modell, Sprites, Overview und App-Icon. `--render none` baut nur
`.blend`/`.glb`/`.manifest.json`. `--cam cx,cz,scale` ist ein Debug-Schalter für `preview`.

## Struktur

| Pfad | Inhalt |
|---|---|
| `skins/<skin>.json` | **Alle** Unterschiede und alle Farben: Palette, Toon-Schattenton, Outline-/Aura-Farbe, Hintergrund, Kopf-/Schnauzen-/Ohren-/Augenmasse, Markings, Schwanz, Accessoires (Goldkette nur Dobermann) |
| `3d/build_dogs.py` | Ein Körper-/Rig-Builder. Skins ändern nur Aussehen und Proportionen innerhalb derselben Bones |
| `characters/<id>.json` | Character-Dateien im Schema von `voice-data/characters/piggy.json` (+ `skeleton`, `palette`, `icon`, `background`); Kopie liegt in `voice-data/characters/` für den Characters-Tab. `persona` ist `null` (keine Stimme gebunden, voice-preview liefert 409; API musste nicht geändert werden) |
| `tools/test_fitdogs.py` | Test ohne pytest |
| `dist/` (gitignored) | `3d/<skin>.blend/.glb/.manifest.json`, `3d/sprites/<skin>-mascot-<pose>-<expr>.png`, `3d/<skin>-overview.png`, `icons/<skin>-1024.png` + `.meta.json` |

## Skelett, Aktionen, Gesicht

* 19 Bones (Namen, Hierarchie und Ruhepositionen fest im Code): root, pelvis, torso, neck, head, jaw, ear.L/R,
  upper_arm/forearm/hand.L/R, thigh/shin.L/R, tail. Objekte hängen starr an Bones (wie bei Piggy), kein Weight-Painting.
* Actions (identische F-Curve-Pfade): `idle` (Atmen, Loop, 48 Frames), `flex` (Doppelbizeps mit Puls), `wave`, `hop`,
  `talk` (Kiefer-Bone, Loop). Im glTF als NLA-Spuren.
* Gesichts-Shape-Keys auf Augen, Brauen und Mund: `neutral`, `happy`, `angry`, `surprised`.
* Sprites: 5 Posen (idle, flex, wave, hop, talk) plus idle mit happy/angry/surprised, RGBA, mit Aura-Ring.

## Look-Technik

Cel-Shading in Cycles ohne Lichter: Emission, gesteuert über Geometry-Normal · feste Lichtrichtung → Farbrampe ohne
Interpolation (Schatten/Basis/Glanzband). Outline als Inverted Hull (Displace entlang der Normalen, nur Rückseiten
sichtbar). Aura per Alpha-Dilatation (numpy) nach dem Render. Dadurch kein Rauschen, 4 Samples reichen für Tests.
Im `.glb` stehen stattdessen schlichte PBR-Materialien mit denselben Basisfarben (der Toon-Shader ist nicht exportierbar;
Outline und Aura fehlen dort).

## App-Icons (1024², RGB ohne Alpha)

Kompakte Bizeps-Pose, Beine ausgeblendet, Kamera passt sich automatisch an die gemessene Figurenhülle an
(Rand 7 %, nichts angeschnitten). Hintergründe aus `skins/*.json`: Shiba weiss → Creme, Dobermann Anthrazit → fast
Schwarz mit dezentem orangem Schein.

## Verifiziert (`test_fitdogs.py`)

Beide `.glb`/`.blend` entstehen; Bones, Hierarchie, Ruhepositionen und glTF-Joints identisch; Action-Namen, Längen und
F-Curve-Pfade identisch; Shape Keys identisch; Materialfarben, Ohrenhöhe und Goldkette unterscheiden sich; Sprites haben
Alpha; Icons sind RGB, ohne angeschnittene Figur (glatter Randstreifen) und bei 60 px noch klar vom Hintergrund abgesetzt;
Character-Dateien passen zu Skin-Dateien und Rig. Zusätzlich lief `tests/test_creative_characters.py` grün.

## Nicht verifiziert / bekannte Mängel

* Animationen wurden nicht als Video gerendert, nur Standbild-Posen (idle, flex, wave, hop, talk) gesichtet; Pose-Übergänge
  und Loop-Nahtstellen der Actions sind rechnerisch, nicht visuell geprüft. Das `.glb` wurde nicht in einem fremden Viewer geöffnet.
* Anatomie ist stilisiert-unbeholfen: Köpfe sind runde Kugeln mit Schnauze, wirken im Vergleich zur Referenz eher niedlich
  (Dobermann etwas hasenhaft), Muskeln sind Ellipsoid-Blobs, Fäuste ohne Finger, Hüfte läuft im Icon als runder Sockel aus.
* Kein Fell-/Muskelrelief, keine Hintergrund-Sticker-Kontur in Sprites ausser Outline + Aura.
* Namen sind Platzhalter; keine Stimme/Persona gebunden.

## 2,5D-Rig aus der Zeichnung (`2d/`)

Der Blender-Nachbau (`3d/`) und Bild-zu-3D treffen die Vorlage nicht genau genug. Darum gibt es einen zweiten Weg: die
Zeichnung selbst wird in Teile zerlegt und mit einem gemeinsamen 2D-Skelett animiert. Die Pixel sind exakt die der Vorlage.

```bash
python3 brand/fitdogs/tools/split_parts.py                      # Teile schneiden -> dist/2d/<skin>/parts + parts.json
python3 brand/fitdogs/2d/render_2d.py --skin all --action all --sheet --out brand/fitdogs/dist/2d
python3 brand/fitdogs/2d/render_2d.py --skin shiba --action flex --size 1080 --bg skin --out brand/fitdogs/dist/2d
python3 brand/fitdogs/2d/render_2d.py --skin all --still pose_flex --out brand/fitdogs/dist/2d
python3 brand/fitdogs/tools/test_fitdogs2d.py                   # "N ok"
```

Frames: `dist/2d/<skin>/<action>/frame_0001.png ...` (RGBA, 24 fps, 2x Supersampling, `meta.json`, mit `--sheet` ein
Kontaktbogen). Das ist das Format des `piggy:`-Ordners in `brand/piggy/3d/compose.py` (Szene `kind: piggy`, `seconds`).
`--bg skin` setzt den Skin-Hintergrund ein. Alle Aktionen eines Skins sind gleich eingepasst (Vereinigung aller Posen), die
Figur bleibt im Bild; dafür ist sie bei 1080 px kleiner als im Freisteller (Flex und Wave sind breit).

Struktur:
- `2d/rigs/<skin>.json`: Teile `torso`, `head`, `upper_arm_l/r`, `forearm_l/r` mit Eltern (`root > torso > head | upper_arm > forearm`),
  Pivots und Polygonen/Kreisen in Freisteller-Pixeln. Namen, Eltern und Reihenfolge sind in beiden Rigs gleich; nur Polygone
  und Pivots unterscheiden sich (Shiba-Kopf 3/4, Dobermann frontal mit Kette am Torso). `l` = linke Bildseite.
- `2d/anims.json`: EINE Datei für beide Hunde. Keyframes `[Sekunden, Wert, Easing]` je Teil und Kanal (`rot` Grad um den
  Pivot, im Uhrzeigersinn positiv; `tx/ty` als Anteil der Figurenhöhe; `sx/sy`). Aktionen `idle` (Loop, 2 s), `flex` (3 s),
  `wave` (2,4 s), `hop` (1 s), `talk` (Loop, 1 s); Posen `pose_idle`, `pose_flex`, `pose_wave`.
- `tools/split_parts.py`: schneidet mit weicher Kante (1,2 px), hinterfüllt den Torso hinter Kopf und Armen per `cv2.inpaint`
  und zeichnet dort eine Outline-Linie an die Körperkante. Schreibt auch `dist/2d/<skin>/cutout.png`.
- `characters/*.json` und `voice-data/characters/*.json`: `assets.render2d`, `poster` (Ruhepose-Render), `idle_video`
  (`dist/2d/<skin>/idle.mp4`, Skin-Hintergrund, 3 Wiederholungen). Die Characters-API braucht keine Änderung
  (`render2d` ist kein Allowlist-Schlüssel und wird nicht ausgeliefert).

Freisteller-Reparatur: `dist/ref/dobermann-cutout.png` (aus `icon_from_reference.py`) hat die dunkle Outline verloren, weil sie
fast die Hintergrundfarbe hat; die Schwellwert-Maske lässt dort Löcher. `split_parts.py` baut den Dobermann-Freisteller deshalb
selbst (alles, was nicht vom Rand aus erreichbar ist, gehört zur Figur) und schreibt ihn nach `dist/2d/dobermann/cutout.png`.
`icon_from_reference.py` ist unverändert; das Dobermann-Icon hat weiterhin die Löcher.

Grenzen:
- Nur Frontansicht (Shiba: die fest gezeichnete 3/4-Kopfdrehung), kein Drehen der Figur, kein Lip-Sync-Mund (der Mund ist
  Teil des Kopf-Bilds; `talk` nickt nur im Takt), keine Gesichtsausdrücke.
- Gelenke sind harte Teilegrenzen mit Überlappung: Schulter und Ellbogen gehen als Drehung ohne Verformung. Amplituden:
  Flex Oberarm 40 Grad, Unterarm 135 Grad (Fäuste zeigen nach oben, Oberarme nicht ganz waagerecht wie bei einer echten
  Doppelbizeps-Pose); Wave Oberarm 65, Unterarm 105 Grad plus Winken ±20 Grad; Hop und Idle klein (unter 20 bzw. 2 Grad).
- Sichtbare Mängel bei grossen Winkeln: am Schulteransatz ist die Teilegrenze zwischen Deltamuskel und Brust eine harte Kante
  ohne Outline (Flex/Wave); der hinterfüllte Torso an den Körperseiten ist glatt gefüllt (beim Dobermann dunkel, mit kleinen
  gezackten Resten an der Taille); am Ellbogen zeigt die Gelenkscheibe um 135 Grad gedrehte Muskelzeichnung (runde Beule an
  der Aussenseite); die Aura der Arme bleibt bei Armbewegung an den Armen (am Torso fehlt sie dort, wo der Arm weg ist).
- `tools/test_fitdogs2d.py` prüft Teile, identische Rigs, gemeinsame Animationen, RGBA-Frames im Bild, Idle-Loop,
  Ruhepose gegen Freisteller (mittlere Abweichung unter 2/255) und einen `compose.py`-Lauf für beide Hunde.

## Tracing-3D (`3d/build_traced.py`)

Dritter Weg: Die Teilebilder der Zeichnung (`dist/2d/<skin>/parts`) werden zu aufgeblasenen 3D-Volumen. Von vorn ist das Ergebnis
die Zeichnung (Pixelfehler siehe unten), von der Seite ist es erfunden.

```bash
blender -b -P brand/fitdogs/3d/build_traced.py -- --skin shiba|dobermann|all --out brand/fitdogs/dist/3d_traced \
    [--render none|preview|all] [--samples N] [--depth 0.25] [--size 768] [--cam front,q30,q-30,side,back,turntable,turntable360] \
    [--action idle,hop,wave,flex,talk|all] [--action-stride N] [--frames 36] [--turn 35] [--shade 0..1]
python3 brand/fitdogs/tools/test_fitdogs_traced.py     # "N ok" (ca. 40 s)
```

Ausgabe: `<out>/<skin>.glb/.blend/.manifest.json`; Renders `<out>/<skin>/<cam>/frame_####.png` (RGBA, Format wie `piggy:` in
`compose.py`), Aktionen `<out>/<skin>/<action>_front/` (Einpassung wie `render_2d.py`), `<skin>-overview.png`, `<skin>-<action>-sheet.png`.
`--render preview` = front, q30, q-30, side; `all` = zusätzlich Turntable (±35 Grad), back und alle Aktionen. `front` ist exakt die
Freisteller-Einstellung (gleiches Seitenverhältnis), die übrigen Ansichten sind quadratisch.

Ansatz: Alpha -> Kontur (cv2, vereinfacht) -> Delaunay-Netz mit Randringen -> Tiefe `z = depth * Teilbreite * sin(t*pi/2)` mit
`t` = geglättete Randdistanz (am Rand z=0) -> Rückseite gespiegelt, am Rand verschweisst (geschlossenes Volumen). Vorderseite: Teilebild
planar von vorn (UV = Bildkoordinaten), Emission ohne Licht (Farben exakt wie die Zeichnung; `--shade` dunkelt optional schräge Flächen).
Teile liegen in Zeichenreihenfolge auf der Oberfläche der darunterliegenden (Arme über Torso, Kopf über Torso). Armature: root, torso, head,
upper_arm_l/r, forearm_l/r mit Pivots aus den Rigs, harte Gewichte (Vertex Group + Armature-Modifier), Bones zeigen entlang +Y, damit
Rotation um die lokale Y-Achse die Drehung der Ansicht ist. Actions aus `2d/anims.json` (24 fps, je Frame gebacken, linear), für beide
Skins gleich; im glb als Animationen. glb: Basecolor-Textur, roughness 1, kein Specular, Alpha-Clip.

Verifiziert (Test): mittlerer Frontfehler im Figurbereich 2,1/255 (Shiba) und 2,4/255 (Dobermann) bei 360 px, Alpha-Fehler unter 0,5;
Meshes geschlossen bis auf wenige Kanten (höchstens 3 offene Randkanten je Teil); gleiche Bones/Actions/F-Curves; Idle animiert; glb.

Grenzen (ehrlich):
- Tiefe und Rückseite sind erfunden: die Tiefe ist ein aufgeblasenes Kissen, die Rückseite eine verwischte, abgedunkelte Vorderseite.
- Die Seiten sind gedehnt: Rand- und Aura-Pixel der Frontansicht werden auf die steilen Flanken projiziert (Schlieren in Outline und Aura).
- Ab etwa ±40 Grad unplausibel; in der Seitenansicht sieht man ein Linsenprofil mit gestreckter Textur, Kopf und Arme sind flache Platten.
  Der Turntable ist deshalb auf ±35 Grad begrenzt, `turntable360` zeigt die erfundene Rückseite.
- Animation ist 2,5D wie im 2D-Rig (starre Teile, harte Gelenkgrenzen); bei grossen Winkeln gelten dieselben Nähte wie dort.
- Kein Lip-Sync, keine Gesichtsausdrücke. Armaturen/Gewichte sind hart, keine Verformung am Gelenk.
