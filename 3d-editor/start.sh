#!/bin/sh
set -eu
editor_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${EDITOR_3D_BIN:-}" ]; then
    exec "$EDITOR_3D_BIN" "$@"
fi
if [ -x "$editor_dir/target/release/3d-editor" ]; then
    exec "$editor_dir/target/release/3d-editor" "$@"
fi
if [ -x "$editor_dir/target/debug/3d-editor" ]; then
    exec "$editor_dir/target/debug/3d-editor" "$@"
fi
echo '3d-editor: noch kein Binary bereitgestellt. Desktop-Tests oder K-Dev-Build erforderlich.' >&2
exit 1
