#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CRATE_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CARGO=${CARGO:-cargo}

if ! command -v "$CARGO" >/dev/null 2>&1; then
    printf 'error: cargo executable not found: %s\n' "$CARGO" >&2
    exit 127
fi

cd "$CRATE_DIR"
printf '%s\n' '==> Rust formatting'
"$CARGO" fmt --all -- --check

printf '%s\n' '==> Headless tests'
"$CARGO" test --locked --no-default-features

printf '%s\n' '==> Desktop Clippy'
"$CARGO" clippy --locked --all-targets -- -D warnings

printf '%s\n' '==> Desktop tests (last, leaves the GUI test binary available)'
"$CARGO" test --locked
