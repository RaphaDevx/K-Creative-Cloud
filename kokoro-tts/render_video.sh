#!/usr/bin/env bash
# ============================================================
#  render_video.sh — 9:16 Short-Video Generator
#  Usage: ./render_video.sh "Your text" [output_name]
#  Deps : ffmpeg, python3 + kokoro-onnx
# ============================================================

set -euo pipefail

# Use system ffmpeg (has libfreetype/drawtext) instead of linuxbrew version
FFMPEG="/usr/bin/ffmpeg"
FFPROBE="/usr/bin/ffprobe"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEXT="${1:-Everything you know about AI is changing right now.}"
OUTPUT_NAME="${2:-short_video}"
AUDIO_FILE="$SCRIPT_DIR/output.wav"
OUTPUT_VIDEO="$SCRIPT_DIR/${OUTPUT_NAME}.mp4"
BG_VIDEO="$SCRIPT_DIR/background.mp4"

# ── 1. Generate TTS audio ──────────────────────────────────
echo "🎙️  Generating TTS audio..."
python3 "$SCRIPT_DIR/generate_audio.py" "$TEXT" "$AUDIO_FILE"

# ── 2. Get audio duration ──────────────────────────────────
DURATION=$($FFPROBE -v quiet -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 "$AUDIO_FILE")
echo "⏱️  Audio duration: ${DURATION}s"

# ── 3. Create background if missing ───────────────────────
if [ ! -f "$BG_VIDEO" ]; then
  echo "🎨  No background.mp4 found — generating dark gradient background..."
  $FFMPEG -y -loglevel error \
    -f lavfi \
    -i "color=c=0x0d0d0d:size=1080x1920:rate=30,format=yuv420p" \
    -f lavfi \
    -i "aevalsrc=0:c=mono:s=44100" \
    -t "$DURATION" \
    -vf "
      drawgrid=width=1:height=1:thickness=1:color=0x1a1a2e@0.3,
      vignette=PI/4
    " \
    -c:v libx264 -preset fast -crf 23 \
    -c:a aac -shortest \
    "$BG_VIDEO"
  echo "✅  Background created: $BG_VIDEO"
fi

# ── 4. Word-wrap text for subtitle overlay ────────────────
# Split into lines of ~42 chars for comfortable reading in 9:16
SUBTITLE_TEXT=$(python3 -c "
import textwrap, sys
text = sys.argv[1]
lines = textwrap.wrap(text, width=38)
print('\n'.join(lines))
" "$TEXT")

# Escape single quotes for ffmpeg
SUBTITLE_ESCAPED="${SUBTITLE_TEXT//\'/\'\\\'\'}"

# Build drawtext filter (multi-line via newline chars)
DRAWTEXT_FILTER=$(python3 -c "
import textwrap, sys
text = sys.argv[1]
lines = textwrap.wrap(text, width=38)

filters = []
total  = len(lines)
# center block vertically around 50% of frame (960px)
line_h = 80   # approx px per line (fontsize 62 + padding)
block_h = total * line_h
start_y = 960 - block_h // 2

for i, line in enumerate(lines):
    esc = line.replace(\"'\", \"'\\\\''\").replace(':', r'\\:')
    y = start_y + i * line_h
    f = (
        f\"drawtext=text='{esc}':\"
        f\"fontsize=62:fontcolor=white:\"
        f\"font='DejaVu Sans Bold':\"
        f\"x=(w-text_w)/2:y={y}:\"
        f\"box=1:boxcolor=black@0.55:boxborderw=18\"
    )
    filters.append(f)
print(','.join(filters))
" "$TEXT")

# ── 5. Render final video ──────────────────────────────────
echo "🎬  Rendering 9:16 short video..."
$FFMPEG -y -loglevel warning \
  -stream_loop -1 -i "$BG_VIDEO" \
  -i "$AUDIO_FILE" \
  -t "$DURATION" \
  -vf "
    scale=1080:1920:force_original_aspect_ratio=increase,
    crop=1080:1920,
    ${DRAWTEXT_FILTER}
  " \
  -c:v libx264 -preset fast -crf 20 \
  -c:a aac -ar 44100 -ac 1 -b:a 128k \
  -movflags +faststart \
  -shortest \
  "$OUTPUT_VIDEO"

# ── 6. Report ─────────────────────────────────────────────
SIZE=$(du -sh "$OUTPUT_VIDEO" | cut -f1)
echo ""
echo "✅  VIDEO READY!"
echo "   📁 File   : $OUTPUT_VIDEO"
echo "   📐 Format : 1080×1920 (9:16 Portrait)"
echo "   ⏱️  Length : ${DURATION}s"
echo "   💾 Size   : ${SIZE}"
