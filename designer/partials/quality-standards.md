# Quality Standards — K-Creative Designer

Verbindliche Qualitäts- und Format-Standards für alle Brand-Assets.

---

## Dateiformat-Standards

### Logo
| Datei | Format | Auflösung | Verwendung |
|-------|--------|-----------|------------|
| `*-logo-primary.svg` | SVG | Vektorisch | Master, skalierbar |
| `*-logo-primary.png` | PNG (transparent) | 2000px Breite | Print, Präsentationen |
| `*-logo-white.svg` | SVG | Vektorisch | Dunkle Hintergründe |
| `*-logo-black.svg` | SVG | Vektorisch | Helle Hintergründe |
| `*-logo-mono.svg` | SVG | Vektorisch | Monochrom-Anwendungen |

### App Icons
| Datei | Format | Grösse |
|-------|--------|--------|
| `*-icon-1024.png` | PNG | 1024×1024 (Master) |
| `*-icon-512.png` | PNG | 512×512 |
| `*-icon-192.png` | PNG | 192×192 (Android) |
| `*-icon-180.png` | PNG | 180×180 (iOS @3x) |
| `*-icon-167.png` | PNG | 167×167 (iPad Pro) |
| `*-icon-152.png` | PNG | 152×152 (iPad) |
| `*-icon-120.png` | PNG | 120×120 (iPhone @2x) |
| `*-favicon-32.png` | PNG | 32×32 |
| `*-favicon-16.png` | PNG | 16×16 |
| `*-favicon.ico` | ICO | 16+32+48 kombiniert |

### Social Media
| Plattform | Format | Grösse |
|-----------|--------|--------|
| Profilbild (alle) | PNG | 400×400 min |
| Twitter/X Header | PNG | 1500×500 |
| LinkedIn Cover | PNG | 1584×396 |
| YouTube Channel Art | PNG | 2560×1440 |
| Instagram Post | PNG/JPG | 1080×1080 |
| Instagram Story | PNG | 1080×1920 |
| Open Graph (Website) | PNG/JPG | 1200×630 |

### Sound
| Datei | Format | Specs |
|-------|--------|-------|
| `*-sound-logo.wav` | WAV | 44.1kHz, 16bit, Stereo |
| `*-sound-logo.mp3` | MP3 | 320kbps |
| Länge Sound Logo | — | 2–4 Sekunden |

### Motion
| Datei | Format | Specs |
|-------|--------|-------|
| `*-motion-logo.mp4` | H.264 | 1080p, 30fps, transparenter BG via ProRes falls nötig |
| Länge Motion Logo | — | 3–5 Sekunden |

---

## Farb-Standards

- Primärfarbe: immer aus LOCKED Brand Research Log
- Nie Farbwerte schätzen — exakte HEX aus dem Research Log nehmen
- PNG-Exports: immer mit Transparenz (kein weisser Hintergrund)
- Farbprofil: sRGB (Web-Standard)

---

## Dateiname-Konvention

```
[projekt]-[asset]-[variante].[ext]

Varianten:
  primary   → Standard-Version
  white     → Weisse Version (für dunkle BGs)
  black     → Schwarze Version (für helle BGs)
  mono      → Einfarbig
  dark      → Optimiert für Dark Mode
  light     → Optimiert für Light Mode

Beispiele:
  klearning-logo-primary.svg
  klearning-logo-white.svg
  klearning-icon-1024.png
  klearning-sound-logo.wav
  klearning-motion-logo.mp4
  klearning-banner-twitter.png
```

---

## Quality Checklist — vor Abschluss eines Assets

### Logo / Icon
- [ ] Vektordatei (SVG) als Master vorhanden
- [ ] Alle Varianten (primary, white, black) exportiert
- [ ] Keine unsichtbaren Elemente oder leere Gruppen im SVG
- [ ] Schriften zu Pfaden konvertiert (kein Font-Dependency)
- [ ] Asset-Registry aktualisiert

### App Icon
- [ ] 1024px Master erstellt (kein Upscaling)
- [ ] Alle 9 Grössen exportiert
- [ ] Kein Text unter 8px Grösse
- [ ] Sieht auf weissem UND schwarzem Hintergrund gut aus
- [ ] Asset-Registry aktualisiert

### Sound Logo
- [ ] WAV + MP3 beide vorhanden
- [ ] Kein Clipping (Pegel unter -1dB)
- [ ] Kein harter Cut am Ende (Fadeout oder natürliche Auflösung)
- [ ] Asset-Registry aktualisiert

### Motion Logo
- [ ] Loopt sauber wenn nötig
- [ ] Kein Flackern oder Artefakte
- [ ] MP4 unter 5MB
- [ ] Asset-Registry aktualisiert
