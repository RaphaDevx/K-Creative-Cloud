#!/usr/bin/env bash
# K-Brand Build — HTML Brand Guide → PDF (color-accurate via headless Chrome)
set -e

BRAND_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST="$BRAND_DIR/dist"
HTML="$DIST/brand-guide.html"
PDF="$DIST/brand-guide.pdf"

if [ ! -f "$HTML" ]; then
  echo "ERROR: $HTML not found. Generate the HTML brand guide first."
  exit 1
fi

echo "Building PDF from $HTML ..."

google-chrome \
  --headless \
  --disable-gpu \
  --no-sandbox \
  --print-to-pdf="$PDF" \
  --print-to-pdf-no-header \
  --no-pdf-header-footer \
  --run-all-compositor-stages-before-draw \
  "file://$HTML"

echo "PDF created: $PDF"

# Show file sizes
ls -lh "$HTML" "$PDF"
