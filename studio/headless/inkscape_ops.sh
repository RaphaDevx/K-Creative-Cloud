#!/usr/bin/env bash
# K-Creative Headless Inkscape Operations
# Usage examples — all run without GUI

INPUT="${1:-/path/to/input.svg}"
OUTPUT_DIR="${2:-/home/raphael/K-Creative-Cloud/renders/inkscape}"
mkdir -p "$OUTPUT_DIR"

# ── SVG → PNG (various sizes) ─────────────────────────────────
export_png() {
    local size="$1"
    inkscape "$INPUT" \
        --export-type=png \
        --export-filename="$OUTPUT_DIR/export_${size}.png" \
        --export-width="$size" \
        --export-height="$size"
    echo "[K-Creative] PNG ${size}x${size} exported"
}

# ── SVG → Optimized SVG ───────────────────────────────────────
optimize_svg() {
    inkscape "$INPUT" \
        --export-type=svg \
        --export-plain-svg \
        --export-filename="$OUTPUT_DIR/optimized.svg"
    echo "[K-Creative] Optimized SVG exported"
}

# ── Apply Inkscape actions (transform, style, etc.) ───────────
apply_actions() {
    local actions="$1"
    local out="${OUTPUT_DIR}/result.svg"
    inkscape "$INPUT" \
        --actions="$actions" \
        --export-type=svg \
        --export-filename="$out"
    echo "[K-Creative] Actions applied → $out"
}

# ── App Icon export set ───────────────────────────────────────
export_icon_set() {
    for size in 16 32 64 128 256 512 1024; do
        export_png "$size"
    done
    optimize_svg
    echo "[K-Creative] Full icon set exported to $OUTPUT_DIR"
}

# ── Run based on command arg ──────────────────────────────────
case "${3:-icon_set}" in
    png)        export_png "${4:-1024}" ;;
    svg)        optimize_svg ;;
    actions)    apply_actions "${4}" ;;
    icon_set)   export_icon_set ;;
esac
