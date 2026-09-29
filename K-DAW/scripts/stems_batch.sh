#!/bin/bash
# Stems-Batch — läuft über Nacht, verarbeitet alle Tracks im downloads/ Ordner
# Modell: htdemucs_6s  →  6 Stems: drums / bass / guitar / piano / vocals / other
# Aufruf: bash stems_batch.sh [input_dir] [output_dir]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="${HOME}/ki_pipeline_env_312"
INPUT_DIR="${1:-$PROJECT_DIR/downloads}"
OUTPUT_DIR="${2:-$PROJECT_DIR/stems}"
LOG_FILE="$OUTPUT_DIR/stems_batch.log"
MODEL="htdemucs_6s"

source "$VENV/bin/activate"

mkdir -p "$OUTPUT_DIR"

echo "========================================" | tee -a "$LOG_FILE"
echo " Stems Batch — $(date)"                  | tee -a "$LOG_FILE"
echo " Modell:   $MODEL (6 Stems)"             | tee -a "$LOG_FILE"
echo " Input:    $INPUT_DIR"                    | tee -a "$LOG_FILE"
echo " Output:   $OUTPUT_DIR"                   | tee -a "$LOG_FILE"
echo " CPU-Kerne: $(nproc)"                     | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Alle Audio-Dateien sammeln
mapfile -t FILES < <(find "$INPUT_DIR" -maxdepth 1 \
  \( -iname "*.mp3" -o -iname "*.wav" -o -iname "*.flac" \
     -o -iname "*.m4a" -o -iname "*.aiff" \) \
  | sort)

TOTAL=${#FILES[@]}
echo "→ $TOTAL Tracks gefunden" | tee -a "$LOG_FILE"

if [ "$TOTAL" -eq 0 ]; then
  echo "Keine Audio-Dateien in $INPUT_DIR" | tee -a "$LOG_FILE"
  exit 0
fi

DONE=0; SKIPPED=0; FAILED=0

for FILE in "${FILES[@]}"; do
  BASENAME=$(basename "$FILE")
  STEM_NAME="${BASENAME%.*}"
  # Demucs legt Stems unter output/model/trackname/ ab
  STEM_OUT="$OUTPUT_DIR/$MODEL/$STEM_NAME"

  # Skip wenn bereits alle Stems vorhanden
  if [ -d "$STEM_OUT" ] && [ "$(ls "$STEM_OUT"/*.wav 2>/dev/null | wc -l)" -ge 5 ]; then
    echo "  ⏭  Übersprungen: $BASENAME" | tee -a "$LOG_FILE"
    ((SKIPPED++)) || true
    continue
  fi

  NUM=$((DONE + SKIPPED + FAILED + 1))
  echo "" | tee -a "$LOG_FILE"
  echo "  ▶  [$NUM/$TOTAL] $BASENAME" | tee -a "$LOG_FILE"
  START=$(date +%s)

  if python3 -m demucs \
      --name "$MODEL" \
      --out "$OUTPUT_DIR" \
      --jobs 4 \
      "$FILE" >> "$LOG_FILE" 2>&1; then
    ELAPSED=$(( $(date +%s) - START ))
    echo "  ✓  Fertig in ${ELAPSED}s (~$(( ELAPSED/60 ))min)" | tee -a "$LOG_FILE"
    ((DONE++)) || true
  else
    echo "  ✗  FEHLER bei $BASENAME" | tee -a "$LOG_FILE"
    ((FAILED++)) || true
  fi
done

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo " FERTIG: $DONE OK · $SKIPPED übersprungen · $FAILED Fehler" | tee -a "$LOG_FILE"
echo " $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
