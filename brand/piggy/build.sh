#!/usr/bin/env bash
# Piggy Brand-System — ALLE Assets aus Tokens neu erzeugen.
#
#   bash brand/piggy/build.sh                 # Tokens, Kontrast, Logos, Varianten, Icons, RN-Code, 3D (voll)
#   bash brand/piggy/build.sh --quick         # 3D mit 16 Samples + jedem 2. Animationsframe (Vorschau-Qualität)
#   bash brand/piggy/build.sh --no-3d         # ohne Blender (ca. 30 s)
#   bash brand/piggy/build.sh --sync          # danach nach Piggy/src/brand synchronisieren
#   bash brand/piggy/build.sh --tokens x.json # andere Token-Datei (z.B. Creator-Export)
#
# Palette ändern = brand/tokens/piggy.json editieren (oder Creator-Export) → dieses Script → alles ist neu.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
KCC="$(cd "$DIR/../.." && pwd)"
TOKENS="$KCC/brand/tokens/piggy.json"
DO_3D=1; QUICK=""; SYNC=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-3d) DO_3D=0 ;;
    --quick) QUICK="--quick" ;;
    --sync) SYNC=1 ;;
    --tokens) TOKENS="$(realpath "$2")"; shift ;;
    *) echo "Unbekannte Option: $1"; exit 1 ;;
  esac
  shift
done

echo "▶ Piggy Brand Build (Tokens: ${TOKENS#$KCC/})"
node "$DIR/tools/build.js" --tokens "$TOKENS"

if [[ $DO_3D -eq 1 ]]; then
  echo ""
  echo "▶ 3D-Maskottchen (Blender headless, Cycles CPU) ${QUICK:+[quick]}"
  OUT3D="$DIR/dist/3d"
  mkdir -p "$OUT3D"
  blender -b -P "$DIR/3d/build_piggy.py" -- \
    --tokens "$DIR/dist/tokens/piggy.resolved.json" --out "$OUT3D" --render all $QUICK \
    > "$OUT3D/blender.log" 2>&1 || { echo "✗ Blender fehlgeschlagen — siehe $OUT3D/blender.log"; tail -20 "$OUT3D/blender.log"; exit 1; }
  grep -E "^\[piggy\]" "$OUT3D/blender.log" | sed 's/^/   /' | grep -v render || true

  # Sprites: 2×-Master (Rausch-Reduktion ohne Denoiser) → @3x 768 / @2x 512 / @1x 256 px
  SPR="$OUT3D/sprites"
  for M in "$SPR"/_master/*.png; do
    B="$(basename "$M" .png)"
    convert "$M" -filter Lanczos -resize 768x768 "$SPR/$B@3x.png"
    convert "$M" -filter Lanczos -resize 512x512 "$SPR/$B@2x.png"
    convert "$M" -filter Lanczos -resize 256x256 "$SPR/$B.png"
  done
  echo "   ✓ Sprites @1x/@2x/@3x ($(ls "$SPR"/_master/*.png | wc -l) Posen/Ausdrücke)"
  montage -background '#FFF0F4' -geometry 256x256+6+6 -tile 4x "$SPR"/_master/*.png "$OUT3D/piggy-mascot-overview.png"

  # Idle-Animation: transparente PNG-Sequenz → WebM (VP9+Alpha), GIF, MP4 (auf Canvas-Farbe)
  FPS=24; [[ -n "$QUICK" ]] && FPS=12
  ANIM="$OUT3D/anim"
  BG="$(node -e "console.log(require('$DIR/dist/tokens/piggy.resolved.json').semantic.color.bg.brand)")"
  ffmpeg -y -loglevel error -framerate $FPS -pattern_type glob -i "$ANIM/idle_*.png" -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 32 "$OUT3D/piggy-idle.webm"
  ffmpeg -y -loglevel error -framerate $FPS -pattern_type glob -i "$ANIM/idle_*.png" \
    -filter_complex "color=c=${BG}:s=384x384[bg];[bg][0:v]overlay=shortest=1,format=yuv420p" -c:v libx264 -crf 20 -movflags +faststart "$OUT3D/piggy-idle.mp4"
  ffmpeg -y -loglevel error -framerate $FPS -pattern_type glob -i "$ANIM/idle_*.png" \
    -filter_complex "scale=256:-1:flags=lanczos,split[a][b];[a]palettegen=reserve_transparent=1[p];[b][p]paletteuse=alpha_threshold=128" "$OUT3D/piggy-idle.gif"
  echo "   ✓ Idle-Animation: $(ls "$ANIM"/idle_*.png | wc -l) Frames → piggy-idle.webm / .mp4 / .gif"
  ls -lh "$OUT3D/piggy.glb" | awk '{print "   ✓ piggy.glb " $5}'

  # mascot.ts kennt jetzt die Sprites
  node "$DIR/tools/build.js" --tokens "$TOKENS" --no-png > /dev/null
fi

# Kopie der Kern-Assets in die Designer-Ordnerstruktur (Konvention k-creative-designer: [projekt]-[asset]-[variante].[ext])
DA="$KCC/designer/assets"
mkdir -p "$DA/logo" "$DA/icons" "$DA/mockups" "$DA/motion"
cp "$DIR"/dist/logo/piggy-*.svg "$DIR"/dist/logo/piggy-*.png "$DA/logo/"
cp "$DIR/dist/variants/base/piggy-appicon-base-1024.png" "$DA/icons/piggy-icon-1024.png"
cp "$DIR/dist/icons/piggy-icons-overview.png" "$DA/icons/piggy-uiicons-overview.png"
if [[ -d "$DIR/dist/3d/sprites/_master" ]]; then
  for M in "$DIR"/dist/3d/sprites/piggy-mascot-*@3x.png; do cp "$M" "$DA/mockups/$(basename "$M" | sed 's/@3x//')"; done
  [[ -f "$DIR/dist/3d/piggy-idle.mp4" ]] && cp "$DIR/dist/3d/piggy-idle.mp4" "$DA/motion/piggy-mascot-idle.mp4"
fi
echo "   ✓ Kern-Assets → designer/assets/{logo,icons,mockups,motion}"

if [[ $SYNC -eq 1 ]]; then
  echo ""
  bash "$KCC/scripts/export-assets.sh" piggy --target brand
fi
echo ""
echo "✓ Fertig. Vorschau: $DIR/creator/index.html · Report: $DIR/dist/palette/contrast-report.md"
