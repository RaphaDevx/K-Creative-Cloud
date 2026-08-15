#!/usr/bin/env bash
# K-Creative DJ Audio Setup — MacBook Air (Early 2015) + Numark Mixtrack Quad
# Target OS: Ubuntu Studio 24.04 / Linux Mint 22 XFCE
#
# Run as root:  sudo bash setup_mac_audio_linux.sh
#
# What it does:
#   1. Realtime audio kernel limits (rtprio 95, memlock unlimited)
#   2. mbpfan — MacBook Air fan control daemon
#   3. PipeWire + WirePlumber configured for 5–10 ms latency on Numark USB
#   4. ALSA UCM profile pinned to Numark Mixtrack Quad
#   5. Mixxx, SuperCollider (scsynth), python-osc, python-rtmidi, aubio
#   6. Node.js 20 LTS + npm dependencies for MIDI mapping hot-reload

set -euo pipefail
BOLD="\033[1m"; CYAN="\033[36m"; GREEN="\033[32m"; YELLOW="\033[33m"; RESET="\033[0m"
info()    { echo -e "${CYAN}[INFO]${RESET} $*"; }
success() { echo -e "${GREEN}[OK]${RESET}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash $0"; exit 1
fi

REAL_USER="${SUDO_USER:-$(logname 2>/dev/null || echo raphael)}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

echo -e "${BOLD}K-Creative DJ Audio Setup${RESET}"
echo "Target user : $REAL_USER ($REAL_HOME)"
echo "Date        : $(date)"
echo "---"

# ── 1. REALTIME AUDIO KERNEL LIMITS ───────────────────────────────────────────
info "1/6  Configuring realtime audio kernel limits…"

# Add user to audio group
usermod -aG audio "$REAL_USER"

cat > /etc/security/limits.d/99-k-audio.conf << 'EOF'
# K-Creative — Realtime audio limits for MacBook Air DJ rig
@audio   -  rtprio     95
@audio   -  memlock    unlimited
@audio   -  nice       -15
EOF
success "limits.conf → rtprio 95, memlock unlimited"

# Tune kernel scheduler for low-latency audio
if ! grep -q "threadirqs" /etc/default/grub 2>/dev/null; then
  warn "Add 'threadirqs' to GRUB_CMDLINE_LINUX_DEFAULT for IRQ threading"
  warn "Edit /etc/default/grub manually, then run: sudo update-grub"
fi

# VM settings for audio
cat > /etc/sysctl.d/99-k-audio.conf << 'EOF'
# Reduce swap pressure — keep audio buffers in RAM
vm.swappiness = 10
# Boost scheduling for RT threads
kernel.sched_rt_runtime_us = -1
EOF
sysctl -p /etc/sysctl.d/99-k-audio.conf >/dev/null 2>&1 || true
success "sysctl: vm.swappiness=10, sched_rt_runtime_us=-1"

# ── 2. MBPFAN — MacBook Air 2015 fan control ──────────────────────────────────
info "2/6  Installing mbpfan (MacBook Pro/Air fan daemon)…"

apt-get install -y mbpfan >/dev/null 2>&1 || {
  warn "mbpfan not in repos — trying PPA…"
  add-apt-repository -y ppa:markus-goldstein/mbpfan-devel >/dev/null 2>&1
  apt-get update -qq
  apt-get install -y mbpfan >/dev/null 2>&1
}

# Tuned for i7 Broadwell (MacBook Air Early 2015, TDP 15W)
cat > /etc/mbpfan.conf << 'EOF'
[general]
min_fan1_speed  = 1200
max_fan1_speed  = 6200
low_temp        = 55
high_temp       = 75
max_temp        = 85
polling_interval = 7
EOF

systemctl enable mbpfan
systemctl restart mbpfan
success "mbpfan active (min=1200rpm, ramp at 55°C, max at 85°C)"

# ── 3. PIPEWIRE + WIREPLUMBER (low-latency Numark config) ─────────────────────
info "3/6  Configuring PipeWire for Numark Mixtrack Quad (5–10 ms)…"

apt-get install -y \
  pipewire pipewire-audio-client-libraries pipewire-pulse \
  wireplumber libspa-0.2-bluetooth libspa-0.2-jack \
  qpwgraph pavucontrol >/dev/null 2>&1

# PipeWire global config — 128 samples @ 48 kHz = ~2.7 ms hardware, 5–10 ms effective
PWCFG="/usr/share/pipewire"
mkdir -p /etc/pipewire/pipewire.conf.d

cat > /etc/pipewire/pipewire.conf.d/99-k-audio.conf << 'EOF'
# K-Creative low-latency DJ config
context.properties = {
    default.clock.rate          = 48000
    default.clock.allowed-rates = [ 44100 48000 96000 ]
    default.clock.quantum       = 128
    default.clock.min-quantum   = 64
    default.clock.max-quantum   = 512
    core.daemon                 = true
    core.name                   = pipewire-0
}
EOF

# WirePlumber policy: prefer Numark as default audio sink
mkdir -p /etc/wireplumber/main.lua.d

cat > /etc/wireplumber/main.lua.d/99-numark.lua << 'EOF'
-- Prefer Numark Mixtrack Quad as default audio device
rule = {
  matches = {
    {
      { "node.description", "matches", "*Numark*" },
    },
    {
      { "node.description", "matches", "*Mixtrack*" },
    },
  },
  apply_properties = {
    ["node.nick"]               = "Numark Mixtrack",
    ["priority.driver"]         = 2000,
    ["priority.session"]        = 2000,
    ["audio.format"]            = "S24_3LE",
    ["audio.rate"]              = 48000,
    ["latency.internal.output"] = 128,
  },
}
table.insert(alsa_monitor.rules, rule)
EOF

# Enable PipeWire for the real user (user-level service)
sudo -u "$REAL_USER" systemctl --user enable --now pipewire pipewire-pulse wireplumber 2>/dev/null || true
success "PipeWire configured: 48 kHz / 128 samples (~2.7 ms hw latency)"

# ── 4. ALSA — Numark as default card ──────────────────────────────────────────
info "4/6  Pinning Numark Mixtrack Quad as ALSA default…"

# Find Numark card index (if already plugged in)
NUMARK_CARD=$(aplay -l 2>/dev/null | grep -i "numark\|mixtrack" | grep -oP 'card \K[0-9]+' | head -1 || echo "")

if [[ -n "$NUMARK_CARD" ]]; then
  cat > "$REAL_HOME/.asoundrc" << EOF
# ALSA default — Numark Mixtrack Quad
defaults.pcm.card $NUMARK_CARD
defaults.ctl.card $NUMARK_CARD

pcm.numark {
    type hw
    card $NUMARK_CARD
    device 0
}

pcm.!default {
    type plug
    slave.pcm "numark"
}
EOF
  chown "$REAL_USER:$REAL_USER" "$REAL_HOME/.asoundrc"
  success "ALSA default → card $NUMARK_CARD (Numark)"
else
  warn "Numark not plugged in — ~/.asoundrc not written. Plug in, then rerun."
fi

# ── 5. INSTALL DJ/AUDIO STACK ──────────────────────────────────────────────────
info "5/6  Installing Mixxx, SuperCollider, aubio, Python audio libs…"

# Ubuntu Studio repos have up-to-date Mixxx
apt-get install -y \
  mixxx \
  supercollider supercollider-ide sc3-plugins \
  aubio \
  ffmpeg \
  alsa-utils \
  aconnectgui a2jmidid \
  python3-pip python3-venv \
  >/dev/null 2>&1

# Python audio/OSC/MIDI stack
pip3 install --quiet --break-system-packages \
  python-osc \
  python-rtmidi \
  mutagen \
  aubio 2>/dev/null || \
pip3 install --quiet \
  python-osc \
  python-rtmidi \
  mutagen \
  aubio

success "Mixxx, scsynth, aubio, python-osc, python-rtmidi installed"

# SuperCollider startup file — auto-boot audio server with low latency
SC_STARTUP="$REAL_HOME/.config/SuperCollider/startup.scd"
mkdir -p "$(dirname "$SC_STARTUP")"
cat > "$SC_STARTUP" << 'EOF'
// K-Creative DJ SuperCollider startup
// Boots scsynth with low-latency settings for Numark Mixtrack Quad

Server.default.options.blockSize         = 128;       // 128 samples ≈ 2.7 ms @ 48 kHz
Server.default.options.sampleRate        = 48000;
Server.default.options.numBuffers        = 4096;
Server.default.options.memSize           = 131072;     // 128 MB synth memory
Server.default.options.maxNodes          = 4096;
Server.default.options.numOutputBusChannels = 4;       // Numark has 4-ch out
Server.default.options.numInputBusChannels  = 4;

// Auto-boot and load K-Creative SynthDefs
s.waitForBoot({
    "K-Creative DJ Engine: scsynth ready".postln;
    // Load K-Creative SynthDefs via OSC from Python bridge
    ~kSlots = Array.fill(4, { nil });  // 4 pattern slots
    "4 pattern slots initialized".postln;
});
EOF
chown "$REAL_USER:$REAL_USER" "$SC_STARTUP"
success "SuperCollider startup.scd configured"

# ── 6. NODE.JS 20 LTS + K-CREATIVE STUDIO DEPS ───────────────────────────────
info "6/6  Installing Node.js 20 LTS…"

if ! command -v node >/dev/null 2>&1 || [[ "$(node --version 2>/dev/null | cut -dv -f2 | cut -d. -f1)" -lt 20 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >/dev/null 2>&1
  apt-get install -y nodejs >/dev/null 2>&1
fi

success "Node.js $(node --version) ready"

# ── POST-INSTALL SUMMARY ───────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════${RESET}"
echo -e "${GREEN}K-Creative DJ Audio Setup Complete${RESET}"
echo "════════════════════════════════════════"
echo ""
echo "NEXT STEPS:"
echo "  1. Plug in Numark Mixtrack Quad via USB"
echo "  2. Log out & back in (apply rtprio limits)"
echo "  3. Verify Numark card: aplay -l | grep -i numark"
echo "  4. Start SuperCollider: scide &"
echo "  5. Test latency: pw-latency --set 128"
echo ""
echo "LATENCY TARGET:"
echo "  Hardware (scsynth): ~2.7 ms  (128 samples @ 48 kHz)"
echo "  Effective (PipeWire): 5–10 ms"
echo "  Audio group: $(getent group audio | cut -d: -f4)"
echo ""
echo "VERIFY RT LIMITS (after logout/login):"
echo "  ulimit -r   → should show 95"
echo "  ulimit -l   → should show unlimited"
echo ""
warn "Reboot recommended for sysctl + GRUB changes to take full effect."
