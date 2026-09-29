# Blender — Offene Aufgaben

## [ ] Server-Agnostic + Native macOS Setup

**Ziel:** Blender auf dem Linux-Server fühlt sich 100% nativ auf dem Mac an. Kein VNC, kein Browser — echtes Fenster auf dem Mac-Desktop.

**Ansatz:**
- XQuartz auf Mac + SSH X11 Forwarding (`ssh -X`)
- Blender öffnet sich als natives macOS-Fenster über SSH
- Alle Scripts auf `$HOME` statt hardcoded `/home/raphael/` umstellen
- Einziger `install.sh` → funktioniert auf jedem Linux-Server (server-agnostic)

**Schritte wenn wir das angehen:**
1. `$HOME` statt `/home/raphael/` in allen Scripts und Configs
2. `install.sh` schreiben: Blender-Addons installieren, Symlinks setzen
3. SSH-Config-Template für Mac bereitstellen (XQuartz + ForwardX11)
4. Testen: `git clone` auf frischem Server → Blender öffnet sich nativ auf Mac

**Notiz:** VNC-Setup bleibt als Fallback (z.B. für Windows-Clients oder wenn kein X11 verfügbar).
