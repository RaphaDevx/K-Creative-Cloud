#!/usr/bin/env bash
# Sichert voice-data/ (Personas, Kanäle, Lexikon, Referenzsamples) verschlüsselt mit restic.
# Modelle (voice-models/) sind wiederbeschaffbar und nur mit --with-models dabei.
#   backup-voices.sh run [--with-models]   sichern auf alle Repos, danach restic check
#   backup-voices.sh list | restore <snapshot> <zielordner> | --selftest
# Umgebung: K_CREATIVE_BACKUP_REPOS  (Leerzeichen-getrennte restic-Repos, mind. 2 auf verschiedenen Datenträgern)
#           RESTIC_PASSWORD_FILE     (Passwortdatei, nie im Repo/Chat ablegen)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${K_CREATIVE_VOICE_HOME:-$ROOT/voice-data}"
REPOS="${K_CREATIVE_BACKUP_REPOS:-}"

need() { [ -n "$REPOS" ] || { echo "K_CREATIVE_BACKUP_REPOS fehlt" >&2; exit 2; }; [ -n "${RESTIC_PASSWORD_FILE:-}" ] || { echo "RESTIC_PASSWORD_FILE fehlt" >&2; exit 2; }; }

run() {
  need
  local paths=("$DATA"); [ "${1:-}" = "--with-models" ] && paths+=("$ROOT/voice-models")
  [ -d "$DATA" ] || { echo "voice-data fehlt: $DATA" >&2; exit 1; }
  for r in $REPOS; do
    restic -r "$r" cat config >/dev/null 2>&1 || restic -r "$r" init >/dev/null
    restic -r "$r" backup --tag voices --host k-creative "${paths[@]}" --quiet
    restic -r "$r" check --quiet
    restic -r "$r" forget --tag voices --keep-hourly 24 --keep-daily 30 --keep-weekly 12 --keep-monthly 24 --prune --quiet
    echo "ok: $r"
  done
}

restore() { need; local r; r="$(echo "$REPOS" | awk '{print $1}')"; restic -r "$r" restore "$1" --target "$2"; }

selftest() {
  local t; t="$(mktemp -d)"; trap 'rm -rf "$t"' RETURN
  mkdir -p "$t/data/personas" "$t/data/samples"
  echo '{"id":"x"}' > "$t/data/personas/x.json"; head -c 4096 /dev/urandom > "$t/data/samples/ref.wav"
  head -c 32 /dev/urandom | base64 > "$t/pw"
  export RESTIC_PASSWORD_FILE="$t/pw"; DATA="$t/data"; REPOS="$t/r1 $t/r2"
  run
  # Verlust simulieren und aus dem zweiten Repo wiederherstellen
  rm -rf "$t/data" "$t/r1"
  restic -r "$t/r2" restore latest --target "$t/out" --quiet
  [ -s "$t/out$t/data/personas/x.json" ] && [ -s "$t/out$t/data/samples/ref.wav" ] || { echo "Restore unvollständig" >&2; exit 1; }
  echo "backup selftest ok"
}

case "${1:-}" in
  run) shift; run "$@" ;;
  list) need; for r in $REPOS; do restic -r "$r" snapshots --tag voices; done ;;
  restore) shift; restore "$@" ;;
  --selftest) selftest ;;
  *) sed -n 2,9p "$0"; exit 2 ;;
esac
