# GIMP MCP — Setup

## Wie es funktioniert

```
Claude ←→ MCP-Server (Python, stdio) ←→ GIMP Plugin (Socket, Port 9877) ←→ GIMP 3.2 (snap)
```

## Einmalig: Plugin installieren (bereits erledigt)

```bash
# Plugin wurde installiert unter:
~/snap/gimp/current/.config/GIMP/3.0/plug-ins/gimp-mcp-plugin/gimp-mcp-plugin.py
```

## Workflow

1. GIMP 3 starten: `gimp` (snap-Version)
2. Bild öffnen (File > Open)
3. Plugin starten: **Tools > Start MCP Server** → Server läuft auf `localhost:9877`
4. Im K-Creative-Cloud-Ordner: `claude` starten
5. Claude kann jetzt das Bild in Echtzeit bearbeiten

## Beispiel-Befehle für Claude

```
"Entferne den Hintergrund vom aktuellen Bild"
"Erhöhe den Kontrast um 20% und mache das Bild wärmer"
"Füge einen weißen Text 'K-Creative' oben mittig ein"
"Zeig mir den aktuellen Stand als Vorschau"
"Exportiere als PNG nach /home/raphael/renders/output.png"
```

## Besonderheit: Live-Feedback

Claude kann mit `get_state_snapshot` jederzeit einen Screenshot des aktuellen
Bildes abrufen und seine eigenen Änderungen visuell prüfen — ohne zu speichern.

## Ports
- GIMP Plugin: `localhost:9877`
- MCP Server: stdio (kein separater Port)
