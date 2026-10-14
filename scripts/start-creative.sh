#!/usr/bin/env bash
set -euo pipefail
CREATIVE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CREATIVE_ROOT"
if ! command -v cargo >/dev/null; then
  echo 'Rust toolchain missing: install cargo and rustc.' >&2
  exit 1
fi
cargo build --manifest-path creative-core/Cargo.toml
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -c 'import fastapi, uvicorn, aiofiles, PIL, multipart' || {
  echo 'Install dependencies: .venv/bin/pip install -r studio/creative-requirements.txt' >&2
  exit 1
}
export K_CREATIVE_DIR="$CREATIVE_ROOT"
export K_CREATIVE_PORT="${K_CREATIVE_PORT:-47200}"
echo "K-Creative: http://127.0.0.1:$K_CREATIVE_PORT/creative"
exec .venv/bin/python studio/server.py
