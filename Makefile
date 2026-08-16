# K-Creative Studio — Makefile
# Usage: make <target>

VENV       := .venv
PYTHON     := $(VENV)/bin/python
PIP        := $(VENV)/bin/pip
STUDIO_DIR := studio
PORT       := 7000

.PHONY: help install venv deps start stop dj-init sc-init \
        scan sync push release tag clean logs status

help:
	@echo ""
	@echo "  K-Creative Studio"
	@echo "  ──────────────────────────────────────"
	@echo "  make install      Full setup (run once on new machine)"
	@echo "  make start        Start studio server on :$(PORT)"
	@echo "  make stop         Stop background server"
	@echo "  make logs         Tail server log"
	@echo "  make status       Show DJ engine / SC / MIDI status"
	@echo ""
	@echo "  make dj-init      Boot SuperCollider + load SynthDefs"
	@echo "  make sc-init      Alias for dj-init"
	@echo "  make scan         Scan ~/Music into track library"
	@echo "  make sync         Hot-reload mappings + SC loops"
	@echo ""
	@echo "  make push         Commit all changes + git push"
	@echo "  make clean        Remove generated files (renders, __pycache__)"
	@echo ""

# ── Installation ───────────────────────────────────────────────────────────────

install: venv deps
	@echo ""
	@echo "[install] Running system-level audio setup (needs sudo)..."
	@sudo bash setup_mac_audio_linux.sh
	@echo ""
	@echo "[install] Installing Node.js dependencies..."
	@cd $(STUDIO_DIR) && npm install --silent
	@echo ""
	@echo "[install] Creating launch script..."
	@$(MAKE) _launcher
	@echo ""
	@echo "════════════════════════════════════════"
	@echo "  Installation complete!"
	@echo "  → make start     to launch the studio"
	@echo "  → make dj-init   to boot SuperCollider"
	@echo "════════════════════════════════════════"

venv:
	@if [ ! -d "$(VENV)" ]; then \
	  echo "[venv] Creating Python virtual environment..."; \
	  python3 -m venv $(VENV); \
	fi

deps: venv
	@echo "[deps] Installing Python dependencies..."
	@$(PIP) install --quiet --upgrade pip
	@$(PIP) install --quiet -r requirements.txt

_launcher:
	@mkdir -p $(HOME)/.local/bin
	@cat > $(HOME)/.local/bin/k-creative << 'EOF'
#!/usr/bin/env bash
# K-Creative Studio launcher
REPO="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
KREPO="/home/raphael/K-Creative-Cloud"
cd "$$KREPO/studio"
source "$$KREPO/.venv/bin/activate"
exec python3 server.py "$$@"
EOF
	@chmod +x $(HOME)/.local/bin/k-creative
	@echo "[launcher] k-creative installed → ~/.local/bin/k-creative"

# ── Studio Server ──────────────────────────────────────────────────────────────

start:
	@echo "Starting K-Creative Studio on :$(PORT)..."
	@cd $(STUDIO_DIR) && source ../$(VENV)/bin/activate && python3 server.py

start-bg:
	@echo "Starting K-Creative Studio in background..."
	@cd $(STUDIO_DIR) && source ../$(VENV)/bin/activate && \
	  nohup python3 server.py > /tmp/k-creative.log 2>&1 & echo $$! > /tmp/k-creative.pid
	@echo "PID: $$(cat /tmp/k-creative.pid) — logs: make logs"

stop:
	@if [ -f /tmp/k-creative.pid ]; then \
	  kill $$(cat /tmp/k-creative.pid) 2>/dev/null && echo "Studio stopped." \
	  || echo "Process already stopped."; \
	  rm -f /tmp/k-creative.pid; \
	else echo "No PID file found."; fi

logs:
	@tail -f /tmp/k-creative.log

status:
	@$(PYTHON) -c "import urllib.request,json; \
	  r=urllib.request.urlopen('http://localhost:$(PORT)/api/dj/status',timeout=3); \
	  s=json.loads(r.read()); \
	  print('SC:',s['sc'],'| Numark:',s['numark'],'| Library:',s['library'],'tracks')" \
	  2>/dev/null || echo "Studio not running (make start)"

# ── DJ / SuperCollider ─────────────────────────────────────────────────────────

dj-init sc-init:
	@echo "Initializing SuperCollider DJ engine..."
	@$(PYTHON) $(STUDIO_DIR)/workers/sc_bridge.py init

scan:
	@$(PYTHON) $(STUDIO_DIR)/workers/dj_engine.py scan \
	  --dir $(HOME)/Music \
	  --db $(STUDIO_DIR)/dj_library.db

sync:
	@curl -s -X POST http://localhost:$(PORT)/api/sync/pipeline \
	  -H 'Content-Type: application/json' \
	  -d '{"target":"all"}' | python3 -m json.tool

# ── Git & Release ─────────────────────────────────────────────────────────────

push:
	@git add -A
	@git status --short
	@git diff --cached --stat
	@read -p "Commit message: " msg && git commit -m "$$msg"
	@GIT_SSH_COMMAND="ssh -i ~/.ssh/id_github_lumina" git push origin main
	@echo "Pushed to GitHub ✓"

# make tag v=0.2.0  →  creates v0.2.0 tag and triggers CI build+release
tag:
	@if [ -z "$(v)" ]; then echo "Usage: make tag v=1.2.3"; exit 1; fi
	@echo "Tagging v$(v)..."
	@npm version $(v) --prefix desktop --no-git-tag-version
	@git add desktop/package.json desktop/package-lock.json
	@git commit -m "chore: bump version to v$(v)"
	@git tag -a "v$(v)" -m "Release v$(v)"
	@GIT_SSH_COMMAND="ssh -i ~/.ssh/id_github_lumina" git push origin main
	@GIT_SSH_COMMAND="ssh -i ~/.ssh/id_github_lumina" git push origin "v$(v)"
	@echo "Tag v$(v) pushed → GitHub Actions will build & release automatically ✓"

# Local Electron build (no signing)
release:
	@cd desktop && npm ci && npx electron-builder --linux AppImage deb --publish never
	@echo "Build artifacts: desktop/release/"

# ── Cleanup ────────────────────────────────────────────────────────────────────

clean:
	@find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true
	@find . -name '*.pyc' -delete 2>/dev/null; true
	@rm -rf renders/*
	@echo "Cleaned."
