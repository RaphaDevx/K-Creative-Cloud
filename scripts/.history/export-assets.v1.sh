#!/usr/bin/env bash
# K-Creative Export Pipeline — Multi-Target
# Usage: ./export-assets.sh <projekt> [--target ios|web|dmg|all]
#
# Targets:
#   ios  (default) → src/constants/design.ts + assets/icon.png etc. (Expo/RN)
#   web            → web/tokens.css + web/favicon.ico + web/apple-touch-icon.png
#   dmg            → desktop/assets/AppIcon.iconset/ + make-icns.sh (läuft auf Mac)
#   all            → alle drei gleichzeitig
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRAND_DIR="$SCRIPT_DIR/../brand"
PROJECT="${1:-}"
TARGET="${2:---target}"
TARGET="${TARGET#--target=}"
[[ "$TARGET" == "--target" ]] && TARGET="${3:-ios}" || true
[[ "$TARGET" == "" ]] && TARGET="ios"

if [[ -z "$PROJECT" || "$PROJECT" == --* ]]; then
  AVAIL="$(ls "$BRAND_DIR/tokens/"*.json 2>/dev/null | xargs -I{} basename {} .json | tr '\n' ' ')"
  echo "Usage: $0 <projekt> [--target ios|web|dmg|all]"
  echo "Verfügbare Projekte: $AVAIL"
  exit 1
fi

TOKENS="$BRAND_DIR/tokens/$PROJECT.json"
[[ ! -f "$TOKENS" ]] && { echo "ERROR: Token-Datei nicht gefunden: $TOKENS"; exit 1; }

# ---- Projekt-Pfad auflösen ----
PROJECTS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)/Projekte"
case "$PROJECT" in
  piggy) PROJECT_DIR="$PROJECTS_ROOT/Piggy" ;;
  *)     PROJECT_DIR="$PROJECTS_ROOT/$(python3 -c "print('${PROJECT}'.capitalize())")" ;;
esac

[[ ! -d "$PROJECT_DIR" ]] && { echo "ERROR: Projektordner nicht gefunden: $PROJECT_DIR"; exit 1; }

ICON_SOURCE="$BRAND_DIR/assets/$PROJECT/icon-master.png"
BG_COLOR="$(node -e "const t=require('$TOKENS'); console.log(t.colors?.bg || '#FFFFFF')" 2>/dev/null || echo '#FFFFFF')"

echo "▶ Export '$PROJECT' [target: $TARGET] → $PROJECT_DIR"
echo ""

# =============================================================================
# TARGET: ios — TypeScript Tokens + Expo Icons
# =============================================================================
export_ios() {
  local TS_OUT="$PROJECT_DIR/src/constants/design.ts"

  node - "$TOKENS" "$TS_OUT" << 'NODE_EOF'
const fs   = require('fs');
const path = require('path');
const t    = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out  = process.argv[3];
const c = t.colors, r = t.radius, s = t.fontSize, sh = t.shadow;

const pad = (k, w) => k.padEnd(w);
const lines = [
  '// AUTO-GENERATED — nicht manuell bearbeiten.',
  `// Quelle: K-Creative/brand/tokens/${path.basename(process.argv[2])}`,
  `// Zuletzt generiert: ${new Date().toISOString()}`,
  '',
  "import { Platform, StyleSheet } from 'react-native';",
  '',
  'export const C = {',
  '  // Backgrounds',
  ...['bg','bgCard','bgSoft','bgAccent','bgPink'].map(k => `  ${pad(k,13)}: '${c[k]}',`),
  '',
  '  // Text',
  ...['textPrimary','textSecondary','textTertiary'].map(k => `  ${pad(k,13)}: '${c[k]}',`),
  '',
  '  // Brand',
  ...['gold','goldSoft','pink','pinkSoft'].map(k => `  ${pad(k,13)}: '${c[k]}',`),
  '',
  '  // Semantic',
  ...['success','error','warning'].map(k => `  ${pad(k,13)}: '${c[k]}',`),
  '',
  '  // Borders',
  ...['border','borderSoft'].map(k => `  ${pad(k,13)}: '${c[k]}',`),
  '} as const;',
  '',
  'export const R = {',
  ...Object.entries(r).map(([k,v]) => `  ${pad(k,4)}: ${v},`),
  '} as const;',
  '',
  'export const S = {',
  ...Object.entries(s).map(([k,v]) => `  ${pad(k,4)}: ${v},`),
  '} as const;',
  '',
  'export const cardShadow = Platform.select({',
  '  ios: {',
  `    shadowColor: '${sh.ios.color}',`,
  `    shadowOffset: { width: ${sh.ios.offsetX}, height: ${sh.ios.offsetY} },`,
  `    shadowOpacity: ${sh.ios.opacity},`,
  `    shadowRadius: ${sh.ios.radius},`,
  '  },',
  `  android: { elevation: ${sh.android.elevation} },`,
  '  default: {',
  `    shadowColor: '${sh.default.color}',`,
  `    shadowOffset: { width: ${sh.default.offsetX}, height: ${sh.default.offsetY} },`,
  `    shadowOpacity: ${sh.default.opacity},`,
  `    shadowRadius: ${sh.default.radius},`,
  '  },',
  '});',
  '',
  'export const card = StyleSheet.flatten({',
  '  backgroundColor: C.bgCard,',
  '  borderRadius: R.xl,',
  '  ...cardShadow,',
  '});',
];
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, lines.join('\n') + '\n');
console.log(`  ✓ TypeScript → ${out}`);
NODE_EOF

  if [[ -f "$ICON_SOURCE" ]]; then
    local A="$PROJECT_DIR/assets"
    convert "$ICON_SOURCE" -resize 1024x1024 "$A/icon.png"
    echo "  ✓ icon.png (1024×1024)"
    convert "$ICON_SOURCE" -resize 820x820 -gravity center -extent 1024x1024 \
      -background none "$A/adaptive-icon.png"
    echo "  ✓ adaptive-icon.png"
    convert "$ICON_SOURCE" -resize 200x200 -gravity center \
      -extent 1284x2778 -background "$BG_COLOR" "$A/splash-icon.png"
    echo "  ✓ splash-icon.png"
  else
    echo "  ℹ Kein icon-master.png → Icons übersprungen ($ICON_SOURCE)"
  fi
}

# =============================================================================
# TARGET: web — CSS Variablen + Favicons
# =============================================================================
export_web() {
  local WEB_DIR="$PROJECT_DIR/web"
  mkdir -p "$WEB_DIR"

  # CSS Variablen
  node - "$TOKENS" "$WEB_DIR/tokens.css" << 'NODE_EOF'
const fs   = require('fs');
const path = require('path');
const t    = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out  = process.argv[3];
const c = t.colors, r = t.radius, s = t.fontSize;

const toKebab = k => k.replace(/([A-Z])/g, '-$1').toLowerCase();

const lines = [
  '/* AUTO-GENERATED — nicht manuell bearbeiten. */',
  `/* Quelle: K-Creative/brand/tokens/${path.basename(process.argv[2])} */`,
  `/* Zuletzt generiert: ${new Date().toISOString()} */`,
  '',
  ':root {',
  '  /* Colors */',
  ...Object.entries(c).map(([k,v]) => `  --color-${toKebab(k)}: ${v};`),
  '',
  '  /* Border Radius */',
  ...Object.entries(r).map(([k,v]) => `  --radius-${k}: ${v}px;`),
  '',
  '  /* Font Sizes */',
  ...Object.entries(s).map(([k,v]) => `  --font-size-${k}: ${v}px;`),
  '}',
];
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, lines.join('\n') + '\n');
console.log(`  ✓ CSS Variablen → ${out}`);
NODE_EOF

  # Favicons via ImageMagick (wenn Master vorhanden)
  if [[ -f "$ICON_SOURCE" ]]; then
    # apple-touch-icon: 180x180
    convert "$ICON_SOURCE" -resize 180x180 "$WEB_DIR/apple-touch-icon.png"
    echo "  ✓ apple-touch-icon.png (180×180)"

    # favicon.ico: multi-size (16, 32, 48)
    local TMP=$(mktemp -d)
    convert "$ICON_SOURCE" -resize 16x16  "$TMP/16.png"
    convert "$ICON_SOURCE" -resize 32x32  "$TMP/32.png"
    convert "$ICON_SOURCE" -resize 48x48  "$TMP/48.png"
    convert "$TMP/16.png" "$TMP/32.png" "$TMP/48.png" "$WEB_DIR/favicon.ico"
    rm -rf "$TMP"
    echo "  ✓ favicon.ico (16×16, 32×32, 48×48)"

    # og-image: 1200x630 (Social Media Preview)
    convert "$ICON_SOURCE" -resize 256x256 -gravity center \
      -extent 1200x630 -background "$BG_COLOR" "$WEB_DIR/og-image.png"
    echo "  ✓ og-image.png (1200×630)"
  else
    echo "  ℹ Kein icon-master.png → Web-Icons übersprungen"
  fi
}

# =============================================================================
# TARGET: dmg — macOS Icon Set vorbereiten
# (iconutil läuft auf Mac; Linux generiert .iconset/, Mac konvertiert zu .icns)
# =============================================================================
export_dmg() {
  local DESKTOP_DIR="$PROJECT_DIR/desktop"
  local ICONSET="$DESKTOP_DIR/assets/AppIcon.iconset"
  mkdir -p "$ICONSET"

  if [[ -f "$ICON_SOURCE" ]]; then
    # macOS .iconset — Standard-Größen
    declare -A SIZES=(
      [icon_16x16]=16 [icon_16x16@2x]=32
      [icon_32x32]=32 [icon_32x32@2x]=64
      [icon_128x128]=128 [icon_128x128@2x]=256
      [icon_256x256]=256 [icon_256x256@2x]=512
      [icon_512x512]=512 [icon_512x512@2x]=1024
    )
    for NAME in "${!SIZES[@]}"; do
      local SIZE="${SIZES[$NAME]}"
      convert "$ICON_SOURCE" -resize "${SIZE}x${SIZE}" "$ICONSET/${NAME}.png"
    done
    echo "  ✓ AppIcon.iconset/ (10 Größen: 16→1024px)"

    # DMG Background: 660x400 (Standard DMG-Fenstergröße)
    convert "$ICON_SOURCE" \
      -resize 128x128 -gravity center \
      -extent 660x400 -background "$BG_COLOR" \
      "$DESKTOP_DIR/assets/dmg-background.png"
    echo "  ✓ dmg-background.png (660×400, BG: $BG_COLOR)"

    # make-icns.sh — läuft auf Mac via ssh macbook
    cat > "$DESKTOP_DIR/assets/make-icns.sh" << 'MACSCRIPT'
#!/usr/bin/env bash
# Auf macOS ausführen: bash make-icns.sh
# Konvertiert AppIcon.iconset → AppIcon.icns (benötigt macOS iconutil)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
iconutil --convert icns "$SCRIPT_DIR/AppIcon.iconset" --output "$SCRIPT_DIR/AppIcon.icns"
echo "✓ AppIcon.icns erstellt: $SCRIPT_DIR/AppIcon.icns"
MACSCRIPT
    chmod +x "$DESKTOP_DIR/assets/make-icns.sh"
    echo "  ✓ make-icns.sh → auf Mac ausführen: ssh macbook 'bash $DESKTOP_DIR/assets/make-icns.sh'"
  else
    echo "  ℹ Kein icon-master.png → DMG-Icons übersprungen"
  fi

  # electron-builder AppIcon Hint
  echo "  ℹ electron-builder erwartet AppIcon.icns in resources/ (macbook build)"
  echo "    Vorhandenes Build-Script: $PROJECT_DIR/desktop/scripts/build-dmg-mac.sh"
}

# =============================================================================
# Dispatch
# =============================================================================
case "$TARGET" in
  ios)        export_ios ;;
  web)        export_web ;;
  dmg)        export_dmg ;;
  all)        export_ios; echo ""; export_web; echo ""; export_dmg ;;
  *)          echo "ERROR: Unbekanntes Target '$TARGET'. Erlaubt: ios, web, dmg, all"; exit 1 ;;
esac

# ---- git status ----
echo ""
echo "  ── git status ($PROJECT_DIR) ──"
git -C "$PROJECT_DIR" status --short 2>/dev/null || echo "  (kein Git-Repo)"
echo ""
echo "✓ Export abgeschlossen: $PROJECT --target $TARGET"
