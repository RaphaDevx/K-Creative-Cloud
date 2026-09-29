#!/usr/bin/env bash
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SSH_KEY="/home/claude/.ssh/id_ed25519"
MACBOOK="100.73.209.21"
SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no Builder@$MACBOOK"
SCP="scp -i $SSH_KEY -o StrictHostKeyChecking=no"

SIGNING_ID="Raphael Markus Kaufmann (H6X9JDXF96)"
KEYCHAIN="/Users/Builder/Library/Keychains/kdev-signing.keychain-db"

REMOTE_DIR="/Users/Builder/KDAWBuild"
LOCAL_SRC="/home/raphael/K-Dev/Projekte/K-Creative-Cloud"
RELEASE_DIR="/home/raphael/K-Dev/Projekte/K-Creative-Cloud/K-DAW/desktop/release"

R2_BUCKET="k-advisory-releases"
R2_PREFIX="k-daw"
R2_PUBLIC="https://pub-f8a055810aee4622b6883b39e71485fe.r2.dev"
CF_ACCOUNT="4567be498d4437b735df9c22a7313c06"
TOKENS_FILE="$HOME/.keys/tokens.env"

r2_upload() {
  local file="$1" key="$2"
  local token; token=$(grep '^CLOUDFLARE_API_TOKEN=' "$TOKENS_FILE" | cut -d= -f2- | tr -d '"')
  local encoded_key; encoded_key=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1],safe='/'))" "$key")
  local code
  code=$(curl -s -o /tmp/r2_resp.json -w "%{http_code}" \
    -X PUT \
    "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT/r2/buckets/$R2_BUCKET/objects/$encoded_key" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/octet-stream" \
    --data-binary "@$file")
  if [ "$code" = "200" ]; then
    echo "  ✓ $R2_PUBLIC/$key"
  else
    echo "  ✗ upload failed HTTP $code"
    cat /tmp/r2_resp.json
    return 1
  fi
}

echo "==> [1/5] Sync source to MacBook"
rsync -az --delete \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  --exclude=node_modules \
  --exclude=release \
  --exclude=dist \
  --exclude='backend/dist' \
  "$LOCAL_SRC/" "Builder@$MACBOOK:$REMOTE_DIR/"

echo "==> [2/5] npm install on MacBook"
$SSH "
  export NVM_DIR=\"\$HOME/.nvm\" && source \"\$NVM_DIR/nvm.sh\"
  export PATH=\"\$HOME/bin:/opt/homebrew/bin:\$PATH\"
  cd '$REMOTE_DIR/desktop'
  npm install --silent
"

echo "==> [3/5] Build + Sign DMG (arm64)"
$SSH "
  export NVM_DIR=\"\$HOME/.nvm\" && source \"\$NVM_DIR/nvm.sh\"
  export PATH=\"\$HOME/bin:/opt/homebrew/bin:\$PATH\"
  cd '$REMOTE_DIR/desktop'

  /Users/Builder/bin/kdev-unlock-keychain
  security list-keychains -d user -s '$KEYCHAIN' \
    /Library/Keychains/System.keychain \
    /System/Library/Keychains/SystemRootCertificates.keychain

  CSC_KEYCHAIN='$KEYCHAIN' \
  CSC_NAME='$SIGNING_ID' \
  npx electron-builder --mac dmg --arm64 \
    2>&1
"

echo "==> [4/5] Notarize + Staple"
$SSH "
  ASC_KEY='/Users/Builder/private/AuthKey_56XGD2G938.p8'
  ASC_KEY_ID='56XGD2G938'
  ASC_ISSUER='574f04c9-0353-4156-9ad6-28ffe3f42850'

  DMG=\$(find '$REMOTE_DIR/desktop/release' -name '*.dmg' ! -name '*.blockmap' | sort | tail -1)
  [ -z \"\$DMG\" ] && echo 'No DMG found!' && exit 1
  echo \"Notarizing: \$DMG\"

  xcrun notarytool submit \"\$DMG\" \
    --key \"\$ASC_KEY\" --key-id \"\$ASC_KEY_ID\" --issuer \"\$ASC_ISSUER\" --wait
  xcrun stapler staple \"\$DMG\"
  echo 'Notarized + stapled OK'
"

echo "==> [5/5] Download + Upload to R2"
mkdir -p "$RELEASE_DIR"

REMOTE_DMG=$($SSH "find '$REMOTE_DIR/desktop/release' -name '*.dmg' ! -name '*.blockmap' | sort | tail -1")
DMG_NAME=$(basename "$REMOTE_DMG")
$SCP "Builder@$MACBOOK:$REMOTE_DMG" "$RELEASE_DIR/$DMG_NAME"
echo "Downloaded DMG: $DMG_NAME"

REMOTE_YML=$($SSH "find '$REMOTE_DIR/desktop/release' -name 'latest-mac.yml' | head -1")
if [ -n "$REMOTE_YML" ]; then
  $SCP "Builder@$MACBOOK:$REMOTE_YML" "$RELEASE_DIR/latest-mac.yml"
  echo "Downloaded: latest-mac.yml"
fi

if [ -f "$TOKENS_FILE" ]; then
  echo "Uploading to R2 ($R2_PREFIX/):"
  r2_upload "$RELEASE_DIR/$DMG_NAME"  "$R2_PREFIX/$DMG_NAME"
  [ -f "$RELEASE_DIR/latest-mac.yml" ] && \
    r2_upload "$RELEASE_DIR/latest-mac.yml" "$R2_PREFIX/latest-mac.yml"
fi

echo ""
echo "✅ Done: $DMG_NAME"
echo "   DMG:    $R2_PUBLIC/$R2_PREFIX/$DMG_NAME"
echo "   YML:    $R2_PUBLIC/$R2_PREFIX/latest-mac.yml"
