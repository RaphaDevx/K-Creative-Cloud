# FreeCAD MCP — Setup

## Wie es funktioniert

```
Claude ←→ MCP-Server (Python, stdio) ←→ FreeCAD Addon (Socket, Port 9878) ←→ FreeCAD
```

## Einmalig: Addon aktivieren

Das Addon wurde installiert unter:
```
~/.local/share/FreeCAD/Mod/freecad_mcp/addon.py
```

In FreeCAD:
1. `Tools > Addon Manager` → nach `freecad_mcp` suchen und aktivieren
2. ODER: Manuell laden via `Tools > Execute Macro` → `addon.py` wählen
3. FreeCAD neu starten
4. Server startet automatisch auf Port 9878

> Snap-Variante: Falls FreeCAD via snap installiert ist, liegt das Addon unter
> `~/snap/freecad/current/.local/share/FreeCAD/Mod/freecad_mcp/`

## Workflow

1. FreeCAD starten
2. Addon aktivieren (einmalig)
3. Im K-Creative-Cloud-Ordner `claude` starten
4. Claude steuert FreeCAD via natürlicher Sprache

## Beispiel-Befehle

```
"Erstelle eine Box mit 100x50x30mm"
"Füge eine Bohrung mit 8mm Durchmesser hinzu"
"Exportiere das Modell als STL nach /home/raphael/renders/teil.stl"
"Exportiere als STEP für den CNC-Fräser"
"Zeig mir alle Objekte in der aktuellen Szene"
```

## Ports
- Blender: 9876
- FreeCAD: 9878 (absichtlich anders)
