# Inkscape MCP — Setup

## Wie es funktioniert

```
Claude ←→ MCP-Server (Python, stdio) ←→ Inkscape CLI / SVG-DOM direkt
```

Kein live Inkscape nötig — der Server arbeitet direkt auf SVG-Dateien via CLI und DOM-Manipulation.

## Zwei Modi

| Modus | Beschreibung |
|-------|-------------|
| CLI | Inkscape-Aktionen über Kommandozeile (Export, Transform, Pfade) |
| DOM | Direkte SVG-XML-Manipulation via CSS-Selektoren |

## Workflow

1. Im K-Creative-Cloud-Ordner `claude` starten — MCP lädt automatisch
2. Claude arbeitet auf SVG-Dateien (kein laufendes Inkscape nötig)
3. Optional: `inkscape datei.svg` öffnen um Ergebnis zu sehen

## Beispiel-Befehle

```
"Erstelle eine neue SVG mit einem roten Kreis und einem blauen Rechteck"
"Exportiere design.svg als 300dpi PNG nach /home/raphael/renders/"
"Ändere alle Elemente mit class='.title' auf Schriftgröße 24px"
"Optimiere design.svg (scour) und reduziere die Dateigröße"
"Konvertiere den Pfad auf Ebene 'logo' in einen Umriss"
```

## Workspace

Standardmäßig arbeitet der Server im aktuellen Verzeichnis.
SVG-Pfade außerhalb des Workspace sind aus Sicherheitsgründen gesperrt.
