# Piggy Marketing-Pipeline: Feature-Briefing → Reel

Ziel: Zu einem Feature (z. B. «Beleg scannen») entsteht ein Reel/Post, in dem Piggy das Feature vorstellt und die
**echte iPhone-App** im Simulator zu sehen ist. Reproduzierbar per Briefing-Datei, alles lokal.

## Ablauf

```
brief.yaml ─▶ Voice (voice.synthesize, Persona piggy)  ─▶ Dauer/Segmente je Szene
          ├─▶ Piggy-Clips (Blender, marketing.py [GEPLANT], Alpha) ─▶ PNG-Sequenz je Aktion
          ├─▶ App-Capture (MacBook-Simulator + Maestro)    ─▶ MP4 je Szene
          └─▶ Compositing (ffmpeg, Linux): Gerät-Rahmen + Piggy-Overlay + Untertitel + Stimme + Musik   [GEPLANT]
                   ─▶ QA (ffprobe; Whisper-Abgleich mit Skript und Pegelprüfung: GEPLANT) ─▶ Paket (MP4/SRT/Thumbnail)
```

## Teile im Detail

**Voice (vorhanden).** `video-shorts-mcp/voice`, rein lokal. Persona `piggy` (Version 1, `voice-data/personas/piggy.json`):
Deutsch mit Piper `de_DE-kerstin-low`, Englisch mit Kokoro `af_heart` (Tempo 1.05). Der Text wird je Sprache segmentiert
(englische Fachbegriffe per Lexikon oder `{en:…}`), jedes Segment geht an die Engine der Persona, der Pegel wird vereinheitlicht.
Stimmwechsel nur per `registry.bump()`, sonst bricht die Synthese mit `VoiceDriftError` ab. Die Persona ist ein Vorschlag und nicht angehört.

**3D-Clips (Ist und Plan).** Ist: `brand/piggy/3d/build_piggy.py` erzeugt Modell, Rig, Gesichts-Shape-Keys, Posen und eine Idle-Animation
aus den Brand-Tokens (Blender headless, Cycles CPU). Plan: `brand/piggy/3d/marketing.py` ergänzt Aktionen (hop, wave, cheer_jump,
coin_drop, turntable, talk_loop), rendert PNG-Sequenzen mit Alpha in 9:16, 1:1 und 16:9 und einen Icon-Render.

**Compositing (Plan).** Vorhanden sind nur `ffmpeg`/`ffprobe` auf Linux. Das Skript, das Simulator-Video in einen Geräterahmen setzt,
Piggy-Clips mit Alpha überlagert, Untertitel brennt und Stimme plus Musik mischt, ist noch nicht gebaut.

## Briefing-Format (Vorschlag, noch nicht implementiert)

```yaml
feature: receipt-scan
format: 9x16            # 9x16 | 1x1 | 16x9
persona: piggy          # Stimme/Kanal aus voice-data
scenes:
  - kind: piggy         # Piggy-Clip
    action: wave        # Blender-Aktion aus marketing.py
    say: "Hi, ich bin Piggy. Heute zeige ich dir, wie du Belege in Sekunden erfasst."
  - kind: app           # Simulator-Aufnahme
    flow: flows/receipt_scan.yaml     # Maestro-Flow im Piggy-Repo (.maestro/)
    say: "Tippe auf Scannen, halte die Kamera auf den Beleg, fertig."
  - kind: piggy
    action: cheer_jump
    say: "Und schon ist alles sortiert."
```

## Warum Simulator auf dem MacBook (kein «Xcode für Linux»)

- Xcode und der iOS-Simulator laufen nur auf macOS. Auf Linux gibt es keinen Ersatz, der die **originale** App zeigt.
- Vom Autor am 21.10.2026 per SSH gemessen, nicht erneut verifiziert: MacBook per SSH erreichbar, Xcode-Simulatoren iOS 26.2/26.4 vorhanden, `maestro` installiert,
  Gerät «iPhone 17 Pro» (iOS 26.2) gebootet. `ffmpeg` ist auf dem Mac **nicht** installiert, deshalb läuft das Compositing auf Linux.
- Steuerung: MCP `ios-simulator` (XcodeBuildMCP) für interaktiv, **Maestro-Flows** für reproduzierbare Abläufe,
  Aufnahme mit `xcrun simctl io <UDID> recordVideo`, danach per rsync nach Linux.
- Bessere Wege als interaktives Klicken: Maestro-Flows sind versioniert, wiederholbar und liefern jedes Mal dieselbe Aufnahme.
- Fallback ohne Mac: Expo-Web-Build der App im headless Chrome aufnehmen. Das ist **nicht** die iPhone-UI und nur Notlösung.

## Was dafür noch fehlt (ehrlich)

1. **Piggy hat noch keinen Simulator-Build im Test-System:** `/home/raphael/K-AI/skills/ios-simulator/apps/` enthält nur `k-learning.json` (`ios-regression` ist ein Skript), `build-sim.sh`
   hat keinen `piggy`-Zweig. Ein Simulator-Build geht über K-Dev (`profile: local`), nicht über diese Session.
2. **Es gibt keine Maestro-Flows für Piggy** (`/storage/projekte/Piggy/.maestro` fehlt). Flows gehören ins Piggy-Repo und werden von der Piggy-Session geschrieben.
3. **Demo-Daten:** Für Aufnahmen braucht es ein Testkonto mit erfundenen Belegen, keine echten Daten.
4. **Login:** Wie bei K-Learning ist Google/Apple-Login im Simulator nicht automatisierbar. Es braucht einen Build mit Test-Login (capability `e2e_login`) oder vorbefüllten Zustand.
5. **Kamera-Funktionen** (Beleg fotografieren) laufen im Simulator nur mit eingespieltem Testbild. Für solche Szenen ist ein vorbereitetes Bild nötig.
6. **Compositing-Skript** (`ffmpeg`, Geräterahmen, Overlay, Untertitel) und **Lip-Sync-Zeiten aus der Stimme** sind noch nicht gebaut.
7. Die **Piggy-3D-Clips** (hop, wave, cheer_jump, coin_drop, turntable, talk_loop) und der Icon-Render sind in `brand/piggy/3d/marketing.py` geplant (Datei noch nicht vorhanden).

## Arbeitsteilung

| Teil | Wer |
|---|---|
| Piggy-Clips, Voice, Compositing, Briefing | K-Creative-Session |
| Maestro-Flows, Test-Login, Demo-Daten in der App | Piggy-Session |
| Simulator-Build, Signieren, Mac-Worker | K-Dev (Builder) |
