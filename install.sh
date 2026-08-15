#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║  K-Creative Studio — One-Command Installer               ║
# ║  MacBook Air (Early 2015) + Numark Mixtrack Quad         ║
# ║                                                          ║
# ║  Usage (fresh machine):                                  ║
# ║    git clone https://github.com/RaphaDevx/K-Creative-Cloud ║
# ║    cd K-Creative-Cloud && bash install.sh                ║
# ║                                                          ║
# ║  Or directly (no git needed):                            ║
# ║    curl -fsSL https://raw.githubusercontent.com/         ║
# ║      RaphaDevx/K-Creative-Cloud/main/install.sh | bash   ║
# ╚══════════════════════════════════════════════════════════╝
set -euo pipefail

REPO_URL="https://github.com/RaphaDevx/K-Creative-Cloud.git"
REPO_DIR="${K_CREATIVE_DIR:-$HOME/K-Creative-Cloud}"
VENV_DIR="$REPO_DIR/.venv"
PORT=7000

BOLD="\033[1m"; CYAN="\033[36m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"
info()    { echo -e "${CYAN}▶${RESET} $*"; }
success() { echo -e "${GREEN}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET} $*"; }
err()     { echo -e "${RED}✗${RESET} $*" >&2; }
step()    { echo -e "\n${BOLD}── $* ──${RESET}"; }

# ── Detect environment ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo "$REPO_DIR")"
IN_REPO=false
[[ -f "$SCRIPT_DIR/studio/server.py" ]] && IN_REPO=true && REPO_DIR="$SCRIPT_DIR"

echo -e "${BOLD}"
echo "  ██╗  ██╗      ██████╗██████╗ ███████╗ █████╗ ████████╗██╗██╗   ██╗███████╗"
echo "  ██║ ██╔╝     ██╔════╝██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██║██║   ██║██╔════╝"
echo "  █████╔╝      ██║     ██████╔╝█████╗  ███████║   ██║   ██║██║   ██║█████╗  "
echo "  ██╔═██╗      ██║     ██╔══██╗██╔══╝  ██╔══██║   ██║   ██║╚██╗ ██╔╝██╔══╝  "
echo "  ██║  ██╗     ╚██████╗██║  ██║███████╗██║  ██║   ██║   ██║ ╚████╔╝ ███████╗"
echo "  ╚═╝  ╚═╝      ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝"
echo -e "${RESET}"
echo -e "${BOLD}  K-Creative Studio Installer${RESET}"
echo "  Ziel: $REPO_DIR"
echo ""

# ── Step 1: Clone or update repo ───────────────────────────────────────────────
step "1/6  Repository"

if $IN_REPO; then
    info "Läuft bereits aus dem Repo-Verzeichnis"
    git -C "$REPO_DIR" pull --ff-only 2>/dev/null && success "Repo aktualisiert" || warn "Pull übersprungen (lokale Änderungen?)"
elif [[ -d "$REPO_DIR/.git" ]]; then
    info "Repo bereits vorhanden — aktualisiere..."
    git -C "$REPO_DIR" pull --ff-only
    success "Repo auf neuestem Stand"
else
    info "Klone $REPO_URL → $REPO_DIR"
    git clone "$REPO_URL" "$REPO_DIR"
    success "Repo geklont"
fi

cd "$REPO_DIR"

# ── Step 2: System dependencies (sudo) ────────────────────────────────────────
step "2/6  Systemabhängigkeiten"

# Check if audio setup already done
AUDIO_DONE=false
[[ -f /etc/security/limits.d/99-k-audio.conf ]] && AUDIO_DONE=true

if $AUDIO_DONE; then
    info "Audio-Kernel-Limits bereits konfiguriert — überspringe System-Setup"
    success "RT-Audio bereits eingerichtet"
else
    info "Führe System-Audio-Setup aus (benötigt sudo)..."
    if [[ $EUID -eq 0 ]]; then
        bash "$REPO_DIR/setup_mac_audio_linux.sh"
    else
        sudo bash "$REPO_DIR/setup_mac_audio_linux.sh"
    fi
fi

# ── Step 3: Python venv ────────────────────────────────────────────────────────
step "3/6  Python Virtual Environment"

if [[ ! -d "$VENV_DIR" ]]; then
    info "Erstelle venv in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    success "venv erstellt"
else
    info "venv vorhanden — aktualisiere Pakete..."
fi

source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$REPO_DIR/requirements.txt"
success "Python-Pakete installiert: $(pip list --format=freeze | wc -l) Pakete"

# ── Step 4: Node.js dependencies ──────────────────────────────────────────────
step "4/6  Node.js"

if ! command -v node >/dev/null 2>&1; then
    warn "Node.js nicht gefunden — stelle sicher dass setup_mac_audio_linux.sh lief"
elif [[ ! -d "$REPO_DIR/studio/node_modules" ]]; then
    info "Installiere npm-Pakete..."
    cd "$REPO_DIR/studio" && npm install --silent
    cd "$REPO_DIR"
    success "npm-Pakete installiert"
else
    success "node_modules vorhanden"
fi

# ── Step 5: Systemd user service ───────────────────────────────────────────────
step "5/6  Studio-Service"

SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/k-creative.service"

mkdir -p "$SERVICE_DIR"
cp "$REPO_DIR/studio/k-creative.service" "$SERVICE_FILE"
# Patch the ExecStart path to use the actual venv
sed -i "s|%h/K-Creative-Cloud/.venv|$VENV_DIR|g; s|%h/K-Creative-Cloud/studio|$REPO_DIR/studio|g" "$SERVICE_FILE"

if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload
    systemctl --user enable k-creative 2>/dev/null || true
    success "systemd-Service installiert: k-creative.service"
    info "  Starten:  systemctl --user start k-creative"
    info "  Status:   systemctl --user status k-creative"
else
    warn "systemctl nicht verfügbar — manuell starten mit: make start"
fi

# ── Step 6: Global launcher ────────────────────────────────────────────────────
step "6/6  Launcher"

LAUNCHER="$HOME/.local/bin/k-creative"
mkdir -p "$HOME/.local/bin"

cat > "$LAUNCHER" << EOF
#!/usr/bin/env bash
# K-Creative Studio — global launcher
# Generated by install.sh — do not edit manually
REPO="$REPO_DIR"
VENV="$VENV_DIR"
cd "\$REPO/studio"
source "\$VENV/bin/activate"
exec python3 server.py "\$@"
EOF
chmod +x "$LAUNCHER"
success "Launcher: ~/.local/bin/k-creative"

# Ensure ~/.local/bin is in PATH
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    warn "~/.local/bin ist nicht in PATH"
    info "Füge folgendes zu ~/.bashrc oder ~/.zshrc hinzu:"
    echo '    export PATH="$HOME/.local/bin:$PATH"'
fi

# ── Renders-Verzeichnis ────────────────────────────────────────────────────────
mkdir -p "$REPO_DIR/renders/audio"

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo -e "${GREEN}  K-Creative Studio installiert!${RESET}"
echo "════════════════════════════════════════"
echo ""
echo "  STARTEN:"
echo "    k-creative                    (Global Launcher)"
echo "    make start                    (aus Repo-Verzeichnis)"
echo "    systemctl --user start k-creative"
echo ""
echo "  STUDIO UI:  http://localhost:$PORT"
echo ""
echo "  DJ ENGINE:"
echo "    make dj-init                  SuperCollider booten"
echo "    make scan                     ~/Music indexieren"
echo "    make sync                     Hot-Reload Mappings+SC"
echo ""
echo "  UPDATES:"
echo "    git pull && make deps         Repo + Pakete aktualisieren"
echo "    make push                     Änderungen auf GitHub pushen"
echo ""
if ! $AUDIO_DONE; then
    echo -e "  ${YELLOW}WICHTIG: Ausloggen + einloggen damit RT-Audio-Limits greifen!${RESET}"
    echo "  Dann prüfen: ulimit -r  (→ 95) und ulimit -l (→ unlimited)"
    echo ""
fi
echo "  Numark Mixtrack Quad einstecken → Autoerkennung über MIDI-WebSocket"
echo ""
