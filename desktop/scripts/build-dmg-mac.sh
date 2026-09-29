#!/bin/bash
set -e

# ── Constants ────────────────────────────────────────────────────────────────
MAC_PATH="/Users/Builder/KCreativeBuild"
LOG="/tmp/kcreative_build_mac.log"
SIGNING_ID="Raphael Markus Kaufmann (H6X9JDXF96)"
KEYCHAIN="/Users/Builder/Library/Keychains/kdev-signing.keychain-db"
ASC_KEY="/Users/Builder/private/AuthKey_56XGD2G938.p8"
ASC_KEY_ID="56XGD2G938"
ASC_ISSUER="574f04c9-0353-4156-9ad6-28ffe3f42850"
SSH="ssh -i /home/claude/.ssh/id_ed25519 -o StrictHostKeyChecking=no Builder@100.73.209.21"
LINUX_DEST="/home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop/release/"

# ── R2 Upload ────────────────────────────────────────────────────────────────
upload_to_r2() {
  local FILE="$1" KEY="$2"
  source /home/claude/.keys/tokens.env
  ENCODED=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$KEY")
  curl -s -X PUT \
    "https://api.cloudflare.com/client/v4/accounts/4567be498d4437b735df9c22a7313c06/r2/buckets/k-advisory-releases/objects/$ENCODED" \
    -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    -H "Content-Type: application/octet-stream" \
    --data-binary "@$FILE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('R2 OK:', d['result']['key'])" 2>/dev/null || echo "R2 upload failed: $KEY"
}

# ── Step 0: Pre-build validation ─────────────────────────────────────────────
echo "[0/8] Pre-build validation..."
DESKTOP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if ! node "$DESKTOP_DIR/scripts/validate.js"; then
  echo "ERROR: Pre-build validation failed — aborting build" | tee -a "$LOG"
  exit 1
fi

# ── Step 1: Sync to MacBook ───────────────────────────────────────────────────
echo "[1/8] Sync to MacBook..."
rsync -az --delete \
  --exclude=desktop/node_modules \
  --exclude=desktop/release \
  --exclude=studio/node_modules \
  --exclude=studio/build \
  --exclude=studio/dist \
  --exclude=.git \
  --exclude="*.log" \
  -e "ssh -i /home/claude/.ssh/id_ed25519 -o StrictHostKeyChecking=no" \
  /home/raphael/K-Dev/Projekte/K-Creative-Cloud/ \
  Builder@100.73.209.21:"$MAC_PATH/"

# ── Step 2: npm install ───────────────────────────────────────────────────────
echo "[2/8] npm install on MacBook..."
if ! $SSH "
  export NVM_DIR=\"\$HOME/.nvm\" && source \"\$NVM_DIR/nvm.sh\"
  export PATH=\"\$HOME/bin:/opt/homebrew/bin:\$PATH\"
  cd $MAC_PATH/desktop
  npm install
"; then
  echo "ERROR: npm install failed" | tee -a "$LOG"
  exit 1
fi

# ── Step 3: PyInstaller — arm64 ───────────────────────────────────────────────
echo "[3/8] PyInstaller backend — arm64..."
if ! $SSH "
  export PATH=\"\$HOME/bin:/opt/homebrew/bin:\$PATH\"
  cd $MAC_PATH
  bash desktop/scripts/build-backend.sh
  if [ ! -f studio/dist/k-creative-server ]; then
    echo 'ERROR: arm64 backend binary not found after build' >&2
    exit 1
  fi
  echo 'arm64 backend binary: OK'
" 2>&1 | tee -a "$LOG"; then
  echo "ERROR: arm64 PyInstaller build failed — aborting" | tee -a "$LOG"
  exit 1
fi

# ── Step 3b: PyInstaller — x64 (best-effort via Rosetta) ─────────────────────
echo "[3b/8] PyInstaller backend — x64 (Rosetta, best-effort)..."
X64_BACKEND_OK=false
# Capture SSH exit code separately — piping to tee swallows it otherwise
X64_TMP=$(mktemp)
$SSH "
  export PATH=\"\$HOME/bin:/opt/homebrew/bin:\$PATH\"
  cd $MAC_PATH
  mkdir -p studio/dist/x64
  if arch -x86_64 /usr/local/bin/python3 -m PyInstaller \
    studio/server.spec \
    --distpath studio/dist/x64 \
    --workpath /tmp/pyinstaller-x64-work \
    --noconfirm; then
    if [ -f studio/dist/x64/k-creative-server ]; then
      echo 'x64 backend binary: OK'
    else
      echo 'WARNING: x64 PyInstaller ran but binary not found' >&2
      exit 1
    fi
  else
    echo 'WARNING: x64 PyInstaller (Rosetta) failed' >&2
    exit 1
  fi
" > "$X64_TMP" 2>&1; X64_EXIT=$?
cat "$X64_TMP" | tee -a "$LOG"
rm -f "$X64_TMP"
if [ $X64_EXIT -eq 0 ]; then
  X64_BACKEND_OK=true
  echo "x64 backend build: OK"
else
  echo "WARNING: x64 backend build failed — x64 DMG will be skipped" | tee -a "$LOG"
fi

# ── Step 4: Build + sign DMGs ─────────────────────────────────────────────────
echo "[4/8] Building + signing DMGs..."

# Helper: unlock keychain (reused in both passes)
UNLOCK_CMD="
  /Users/Builder/bin/kdev-unlock-keychain
  security list-keychains -d user -s '$KEYCHAIN' /Library/Keychains/System.keychain /System/Library/Keychains/SystemRootCertificates.keychain
"

# Helper: sign the DMG container itself (electron-builder only signs the .app inside)
SIGN_DMG_CMD="
  /Users/Builder/bin/kdev-unlock-keychain
  codesign --sign 'Developer ID Application: $SIGNING_ID' --keychain '$KEYCHAIN' --force
"

# arm64 pass — arm64 binary is already in studio/dist/k-creative-server from step 3
echo "[4a/8] electron-builder — arm64..."
if ! $SSH "
  export NVM_DIR=\"\$HOME/.nvm\" && source \"\$NVM_DIR/nvm.sh\"
  export PATH=\"\$HOME/bin:/opt/homebrew/bin:\$PATH\"
  $UNLOCK_CMD
  cd $MAC_PATH/desktop
  CSC_KEYCHAIN='$KEYCHAIN' CSC_NAME='$SIGNING_ID' \
    npx electron-builder --mac dmg --arm64 --publish=never
" 2>&1 | tee -a "$LOG"; then
  echo "ERROR: arm64 electron-builder failed" | tee -a "$LOG"
  exit 1
fi

# Sign the arm64 DMG container
echo "[4a-sign/8] Signing arm64 DMG container..."
if ! $SSH "
  $UNLOCK_CMD
  DMG=\$(find $MAC_PATH/desktop/release -name '*arm64*.dmg' ! -name '*.blockmap' | sort -V | tail -1)
  codesign --sign 'Developer ID Application: $SIGNING_ID' --keychain '$KEYCHAIN' --force \"\$DMG\"
  echo 'DMG container signed:' \"\$DMG\"
" 2>&1 | tee -a "$LOG"; then
  echo "ERROR: arm64 DMG signing failed" | tee -a "$LOG"
  exit 1
fi

# x64 pass — copy x64 binary into place first, then build
if [ "$X64_BACKEND_OK" = "true" ]; then
  echo "[4b/8] electron-builder — x64..."
  if ! $SSH "
    export NVM_DIR=\"\$HOME/.nvm\" && source \"\$NVM_DIR/nvm.sh\"
    export PATH=\"\$HOME/bin:/opt/homebrew/bin:\$PATH\"
    $UNLOCK_CMD
    # Swap in x64 binary
    cp $MAC_PATH/studio/dist/x64/k-creative-server $MAC_PATH/studio/dist/k-creative-server
    cd $MAC_PATH/desktop
    CSC_KEYCHAIN='$KEYCHAIN' CSC_NAME='$SIGNING_ID' \
      npx electron-builder --mac dmg --x64
  " 2>&1 | tee -a "$LOG"; then
    echo "ERROR: x64 electron-builder failed" | tee -a "$LOG"
    exit 1
  fi
  # Sign the x64 DMG container (electron-builder names x64 DMG without arch suffix)
  $SSH "
    $UNLOCK_CMD
    DMG=\$(find $MAC_PATH/desktop/release -name '*.dmg' ! -name '*arm64*' ! -name '*.blockmap' | sort -V | tail -1)
    [ -n \"\$DMG\" ] && codesign --sign 'Developer ID Application: $SIGNING_ID' --keychain '$KEYCHAIN' --force \"\$DMG\" && echo 'x64 DMG signed:' \"\$DMG\"
  " 2>&1 | tee -a "$LOG" || true
else
  echo "Skipping x64 electron-builder (no x64 backend binary)"
fi

# ── Step 5: Notarize + staple ─────────────────────────────────────────────────
echo "[5/8] Notarizing + stapling..."

# Find both DMGs on the Mac
# electron-builder names arm64 DMG with -arm64, x64 DMG without arch suffix
ARM64_DMG=$($SSH "find $MAC_PATH/desktop/release -name '*arm64*.dmg' ! -name '*.blockmap' | sort -V | tail -1")
X64_DMG=$($SSH "find $MAC_PATH/desktop/release -name '*.dmg' ! -name '*arm64*' ! -name '*.blockmap' | sort -V | tail -1" 2>/dev/null || true)

if [ -z "$ARM64_DMG" ]; then
  echo "ERROR: arm64 DMG not found after build" | tee -a "$LOG"
  exit 1
fi

echo "arm64 DMG: $ARM64_DMG"

if ! $SSH "
  xcrun notarytool submit '$ARM64_DMG' \
    --key '$ASC_KEY' \
    --key-id '$ASC_KEY_ID' \
    --issuer '$ASC_ISSUER' \
    --wait
  xcrun stapler staple '$ARM64_DMG'
  echo 'Notarization + stapling arm64: OK'
" 2>&1 | tee -a "$LOG"; then
  echo "ERROR: notarization failed for arm64 DMG" | tee -a "$LOG"
  exit 1
fi

if [ "$X64_BACKEND_OK" = "true" ] && [ -n "$X64_DMG" ]; then
  echo "x64 DMG: $X64_DMG"
  if ! $SSH "
    xcrun notarytool submit '$X64_DMG' \
      --key '$ASC_KEY' \
      --key-id '$ASC_KEY_ID' \
      --issuer '$ASC_ISSUER' \
      --wait
    xcrun stapler staple '$X64_DMG'
    echo 'Notarization + stapling x64: OK'
  " 2>&1 | tee -a "$LOG"; then
    echo "ERROR: notarization failed for x64 DMG" | tee -a "$LOG"
    exit 1
  fi
else
  echo "Skipping x64 notarization (no x64 DMG)"
fi

# ── Step 6: SCP back to Linux ─────────────────────────────────────────────────
echo "[6/8] Fetching DMGs to Linux..."
mkdir -p "$LINUX_DEST"

scp -i /home/claude/.ssh/id_ed25519 -o StrictHostKeyChecking=no \
  "Builder@100.73.209.21:$ARM64_DMG" \
  "$LINUX_DEST"

if [ "$X64_BACKEND_OK" = "true" ] && [ -n "$X64_DMG" ]; then
  scp -i /home/claude/.ssh/id_ed25519 -o StrictHostKeyChecking=no \
    "Builder@100.73.209.21:$X64_DMG" \
    "$LINUX_DEST"
fi

# ── Step 7: Upload to R2 ──────────────────────────────────────────────────────
echo "[7/8] Uploading to R2..."

ARM64_LOCAL="$LINUX_DEST$(basename "$ARM64_DMG")"
upload_to_r2 "$ARM64_LOCAL" "k-creative/$(basename "$ARM64_DMG")"

if [ "$X64_BACKEND_OK" = "true" ] && [ -n "$X64_DMG" ]; then
  X64_LOCAL="$LINUX_DEST$(basename "$X64_DMG")"
  upload_to_r2 "$X64_LOCAL" "k-creative/$(basename "$X64_DMG")"
fi

# ── Upload latest-mac.yml + latest-arm64-mac.yml for OTA updater ─────────────
echo "[7b/8] Uploading YML files for OTA..."
source /home/claude/.keys/tokens.env

# latest-mac.yml (from x64 build — references x64 DMG)
YML_LOCAL="$LINUX_DEST/latest-mac.yml"
scp -i /home/claude/.ssh/id_ed25519 -o StrictHostKeyChecking=no \
  "Builder@100.73.209.21:$MAC_PATH/desktop/release/latest-mac.yml" \
  "$YML_LOCAL"
curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/4567be498d4437b735df9c22a7313c06/r2/buckets/k-advisory-releases/objects/k-creative%2Flatest-mac.yml" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: text/yaml" \
  --data-binary "@$YML_LOCAL" | python3 -c "import sys,json; d=json.load(sys.stdin); print('latest-mac.yml R2 OK' if d.get('success') else d)" 2>/dev/null

# latest-arm64-mac.yml — generated from arm64 DMG sha512 so arm64 users get the native binary
ARM64_BASE=$(basename "$ARM64_LOCAL")
ARM64_SHA=$(openssl dgst -sha512 -binary "$ARM64_LOCAL" | base64 | tr -d '\n')
ARM64_SIZE=$(stat -c%s "$ARM64_LOCAL")
REL_DATE=$(grep 'releaseDate:' "$YML_LOCAL" | sed "s/releaseDate: //")
cat > "$LINUX_DEST/latest-arm64-mac.yml" << YMLEOF
version: $(grep '^version:' "$YML_LOCAL" | awk '{print $2}')
files:
  - url: $ARM64_BASE
    sha512: $ARM64_SHA
    size: $ARM64_SIZE
path: $ARM64_BASE
sha512: $ARM64_SHA
releaseDate: $REL_DATE
YMLEOF
curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/4567be498d4437b735df9c22a7313c06/r2/buckets/k-advisory-releases/objects/k-creative%2Flatest-arm64-mac.yml" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: text/yaml" \
  --data-binary "@$LINUX_DEST/latest-arm64-mac.yml" | python3 -c "import sys,json; d=json.load(sys.stdin); print('latest-arm64-mac.yml R2 OK' if d.get('success') else d)" 2>/dev/null

# Upload zip for OTA delta download
ARM64_ZIP=$($SSH "find $MAC_PATH/desktop/release -name '*arm64*-mac.zip' | sort -V | tail -1" 2>/dev/null || true)
if [ -n "$ARM64_ZIP" ]; then
  ZIP_LOCAL="$LINUX_DEST$(basename "$ARM64_ZIP")"
  scp -i /home/claude/.ssh/id_ed25519 -o StrictHostKeyChecking=no \
    "Builder@100.73.209.21:$ARM64_ZIP" "$ZIP_LOCAL"
  ZIP_KEY=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$(basename "$ARM64_ZIP")")
  curl -s -X PUT \
    "https://api.cloudflare.com/client/v4/accounts/4567be498d4437b735df9c22a7313c06/r2/buckets/k-advisory-releases/objects/$ZIP_KEY" \
    -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
    -H "Content-Type: application/zip" \
    --data-binary "@$ZIP_LOCAL" | python3 -c "import sys,json; d=json.load(sys.stdin); print('zip R2 OK' if d.get('success') else d)" 2>/dev/null
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "Build complete:"
ls "$LINUX_DEST"*.dmg 2>/dev/null || echo "(no DMGs in $LINUX_DEST)"
