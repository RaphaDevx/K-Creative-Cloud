---
name: create-reel
description: Lernvideos und Reels über K-Creative erzeugen; einfache Szenen, Remotion oder echte Bildschirmaufnahmen, mit Sprecher, Export und Plattform-Paket.
metadata:
  aliases: ["create-reel"]
---

# Create reel — K-Creative video workflow

`k-creative-cloud` für gemeinsame Tool-/Projektwahl laden. Videoziel, Sprache, Format, fachliche Lösung und Plattform aus Auftrag bestimmen. Nur benötigte Produktionsreferenz laden:

- Bildschirm/Excel/Calc/Software → `partials-reel-screen-recording`. Canonical Tool in K-Creative packages/screen-recording/tutorial.py; alter Harness-Aufruf ist kompatibler Launcher.
- Animierte Erklärung → --kind reel / --kind statistics Tooldiscovery; einfache Szenen über Pillow, Statistik über `partials-reel-stat`. [Animierter Ablauf](references/animated.md) nur dafür laden. Sprecherverfügbarkeit vor Render prüfen.
- Aufwendige Timeline → Kdenlive oder tatsächlich laufendes Remotion; gleiche K-Creative-Assets/Projekte wiederverwenden. Kein Remotion-Build aus Verfügbarkeit eines Ordners ableiten.

Stimme: immer über `voice.synthesize(text, out, channel=…)` (K-Creative `video-shorts-mcp/voice`, rein lokal: Piper DE, Kokoro EN, gemischte Sprache je Segment, Begriffe in `voice-data/lexicon.json` oder `{en:Begriff}`). Kanal → Persona → fixierte Stimme; bei Drift bricht die Synthese ab, Stimmwechsel nur per `registry.bump()`. Kein Edge TTS/Cloud.

Ablauf: Storyboard/geprüfte Lösung → passende Engines prüfen → Assets/Sprecher/Screen erfassen → Timeline → MP4/SRT/Thumbnail → technische und visuelle Prüfung → lokales Lernplattform-/Social-Paket. Portrait nicht auf Kosten lesbarer Tabellen erzwingen. Stumme Aufnahme als stumm kennzeichnen. Renderbefehle sind mechanisch, ohne extra Modell ausführen.

K-Learning-Publishing nur für bestätigten Kurs und autorisierten Auftrag über aktuellen Upload-/Katalogworkflow; alte kursspezifische Deploy-Scripts nicht pauschal ausführen. Social-Publishing über social-media plus Plattform-Partial. Ergebnis enthält Source/Assetpfade, Dauer, Codec, Tonstatus, Verifikation und echten Upload-Status.

Neue passende K-Creative-Adapter erscheinen durch Manifestdiscovery ohne Skill-Neuschreiben. Bewährte Engines nicht blind ersetzen; fehlgeschlagene Exporte nicht als fertig melden.
