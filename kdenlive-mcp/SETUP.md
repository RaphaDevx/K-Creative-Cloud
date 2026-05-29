# Kdenlive MCP — Setup

## Wie es funktioniert

```
Claude ←→ MCP-Server (Python, stdio) ←→ MLT-XML Projekte + melt CLI
```

Kein gepatchtes Kdenlive nötig. Der Server arbeitet direkt auf `.kdenlive`-Projektdateien
(MLT-XML-Format) und rendert via `melt` (Teil des Kdenlive-Pakets).

## Abhängigkeiten prüfen

```bash
which melt     # melt CLI (kommt mit kdenlive)
which kdenlive # GUI-Launcher
```

## Workflow

1. Im K-Creative-Cloud-Ordner `claude` starten
2. Claude erstellt/modifiziert Projekte direkt als MLT-XML
3. Rendert via `melt` in MP4/MKV
4. Kdenlive GUI öffnen zum visuellen Nachbearbeiten

## Beispiel-Befehle

```
"Erstelle ein neues Kdenlive-Projekt '1080p25' in 1920x1080 @ 25fps"
"Füge die Clips aus ~/Videos/ in das Projekt ein"
"Rendere das Projekt als MP4 nach ~/renders/"
"Zeig mir alle Clips im Projekt intro.kdenlive"
"Öffne das Projekt in der Kdenlive GUI"
```

## Verfügbare Tools

| Tool | Beschreibung |
|------|-------------|
| `create_project` | Neues leeres Projekt erstellen |
| `get_project_info` | Projektmetadaten auslesen |
| `list_projects` | Alle Projekte auflisten |
| `add_clip_to_project` | Mediendatei in Projekt einfügen |
| `render_project` | Projekt zu MP4 rendern |
| `launch_kdenlive` | Kdenlive GUI öffnen |
