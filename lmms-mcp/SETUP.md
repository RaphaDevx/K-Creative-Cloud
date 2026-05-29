# LMMS MCP — Setup

## Wie es funktioniert

```
Claude ←→ MCP-Server (Python, stdio) ←→ LMMS CLI
```

LMMS wird per CLI gesteuert: Projekte rendern, Presets browsen, Samples finden.
Für Komposition öffnet Claude die LMMS GUI und du arbeitest direkt darin.

## Workflow

1. Im K-Creative-Cloud-Ordner `claude` starten
2. Claude kann Projekte rendern, Presets/Samples listen, LMMS starten
3. Neue Projekte in der LMMS GUI erstellen, dann von Claude rendern lassen

## Beispiel-Befehle

```
"Liste alle LMMS-Projekte auf"
"Rendere das Projekt 'beat.mmp' als WAV"
"Zeig mir alle TripleOscillator Presets"
"Liste alle Drum-Samples"
"Öffne LMMS mit dem Projekt kick_pattern.mmp"
"Was ist die LMMS-Version?"
```

## Verfügbare Tools

| Tool | Beschreibung |
|------|-------------|
| `list_projects` | Alle .mmp Projekte auflisten |
| `render_project` | Projekt zu WAV/OGG rendern |
| `list_presets` | Instrument-Presets browsen |
| `list_samples` | Audio-Samples nach Kategorie |
| `get_lmms_info` | Version + Pfade |
| `launch_lmms` | LMMS GUI öffnen |
