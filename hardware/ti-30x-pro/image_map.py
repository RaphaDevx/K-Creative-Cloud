#!/usr/bin/env python3
"""
Image-to-UI Mapper
Analyzes a UI image pixel-by-pixel and extracts:
- Exact bounding boxes of all rectangular UI elements (keys, panels)
- Dominant colors per region (HSL + HEX)
- Relative proportions (% of image)
- A JSON map ready for CSS/HTML reconstruction

Usage:
  python3 image_map.py <image_path> [--output map.json] [--vis]
"""

import sys, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

# ── helpers ──────────────────────────────────────────────────────────────────

def dominant_color(pixels_rgb):
    """Returns the most dominant color in a pixel array as #rrggbb."""
    if len(pixels_rgb) == 0:
        return "#000000"
    arr = np.array(pixels_rgb, dtype=np.float32)
    mean = arr.mean(axis=0).astype(int)
    return "#{:02x}{:02x}{:02x}".format(*mean)

def rgb_to_hsl(r, g, b):
    r, g, b = r/255, g/255, b/255
    cmax, cmin = max(r,g,b), min(r,g,b)
    l = (cmax + cmin) / 2
    if cmax == cmin:
        return (0, 0, round(l*100))
    d = cmax - cmin
    s = d / (2 - cmax - cmin) if l > 0.5 else d / (cmax + cmin)
    if cmax == r:   h = (g - b) / d + (6 if g < b else 0)
    elif cmax == g: h = (b - r) / d + 2
    else:           h = (r - g) / d + 4
    return (round(h*60), round(s*100), round(l*100))

def region_stats(img_arr, x, y, w, h):
    """Extract color stats for a rectangular region."""
    region = img_arr[y:y+h, x:x+w]
    if region.size == 0:
        return {"hex": "#000000", "hsl": [0,0,0]}
    flat = region.reshape(-1, 3).tolist()
    r, g, b = np.array(flat).mean(axis=0)
    hex_col = "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))
    hsl = rgb_to_hsl(r, g, b)
    return {"hex": hex_col, "hsl": list(hsl)}

# ── core analysis ─────────────────────────────────────────────────────────────

def find_rects(img, min_area=50, epsilon_factor=0.04):
    """Find all rectangular regions using edge detection + contour approximation."""
    try:
        import cv2
    except ImportError:
        print("ERROR: pip install opencv-python-headless", file=sys.stderr)
        sys.exit(1)

    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, 30, 100)
    dilated = cv2.dilate(edges, np.ones((2,2), np.uint8), iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    rects = []
    seen = set()
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        # Approximate to polygon
        epsilon = epsilon_factor * cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, epsilon, True)
        # Accept both 4-sided and bounding-box approach
        x, y, w, h = cv2.boundingRect(cnt)
        key = (x//2*2, y//2*2, w//2*2, h//2*2)
        if key in seen:
            continue
        seen.add(key)
        # Filter near-degenerate rects
        aspect = w / h if h > 0 else 0
        if aspect < 0.1 or aspect > 20:
            continue
        rects.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h),
                       "area": int(area), "sides": len(approx)})

    # Sort by area descending
    rects.sort(key=lambda r: r["area"], reverse=True)
    return rects

def cluster_rects(rects, img_w, img_h):
    """
    Group rects into semantic layers:
      - body (largest)
      - display
      - keys (grid-like, similar sizes)
      - labels / small decorations
    """
    if not rects:
        return {}

    body = rects[0]  # largest = calculator body
    total_area = body["area"]

    display_candidates = [r for r in rects[1:]
                          if r["area"] > total_area * 0.03
                          and r["area"] < total_area * 0.25]

    key_candidates = [r for r in rects[1:]
                      if total_area * 0.002 < r["area"] < total_area * 0.04]

    return {
        "body": body,
        "display": display_candidates[:3],
        "keys": key_candidates,
    }

def build_map(image_path, vis=False):
    img_path = Path(image_path)
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    arr = np.array(img)

    print(f"Image: {W}×{H}px  ({img_path.name})")

    rects = find_rects(img)
    clusters = cluster_rects(rects, W, H)

    # Enrich with color info and relative positions
    def enrich(r):
        color = region_stats(arr, r["x"], r["y"], r["w"], r["h"])
        return {
            **r,
            "color": color,
            "rel": {
                "x_pct": round(r["x"] / W * 100, 2),
                "y_pct": round(r["y"] / H * 100, 2),
                "w_pct": round(r["w"] / W * 100, 2),
                "h_pct": round(r["h"] / H * 100, 2),
            }
        }

    result = {
        "source": str(img_path),
        "image_size": {"w": W, "h": H},
        "body": enrich(clusters["body"]) if clusters.get("body") else None,
        "display": [enrich(r) for r in clusters.get("display", [])],
        "keys": [enrich(r) for r in clusters.get("keys", [])],
        "all_rects_count": len(rects),
    }

    # ── grid analysis of keys ─────────────────────────────────────────────────
    if result["keys"]:
        keys = result["keys"]
        # Find median key size
        widths  = sorted(k["w"] for k in keys)
        heights = sorted(k["h"] for k in keys)
        med_w = widths[len(widths)//2]
        med_h = heights[len(heights)//2]
        result["median_key"] = {"w": med_w, "h": med_h}

        # Snap to grid
        col_xs = sorted(set(round(k["x"] / med_w) * med_w for k in keys))
        row_ys = sorted(set(round(k["y"] / med_h) * med_h for k in keys))
        result["grid"] = {
            "estimated_cols": len(col_xs),
            "estimated_rows": len(row_ys),
            "col_xs": col_xs[:20],
            "row_ys": row_ys[:20],
        }

    # ── visualization (optional) ──────────────────────────────────────────────
    if vis:
        vis_path = img_path.with_suffix(".mapped.png")
        vis_img = img.copy()
        draw = ImageDraw.Draw(vis_img)

        if result["body"]:
            b = result["body"]
            draw.rectangle([b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]],
                           outline=(0,255,0), width=3)

        for r in result.get("display", []):
            draw.rectangle([r["x"], r["y"], r["x"]+r["w"], r["y"]+r["h"]],
                           outline=(0,120,255), width=2)

        for i, k in enumerate(result.get("keys", [])[:80]):
            draw.rectangle([k["x"], k["y"], k["x"]+k["w"], k["y"]+k["h"]],
                           outline=(255,80,0), width=1)
            draw.text((k["x"]+2, k["y"]+2), str(i), fill=(255,255,0))

        vis_img.save(vis_path)
        print(f"Visualization saved: {vis_path}")

    return result

# ── CSS generator ─────────────────────────────────────────────────────────────

def map_to_css(result):
    """Convert the map to CSS custom properties for pixel-perfect layout."""
    lines = [":root {"]
    body = result.get("body")
    if body:
        lines.append(f"  --calc-width: {body['w']}px;")
        lines.append(f"  --calc-height: {body['h']}px;")
        lines.append(f"  --calc-bg: {body['color']['hex']};")

    for i, d in enumerate(result.get("display", [])):
        lines.append(f"  --display-{i}-x: {d['x']}px;")
        lines.append(f"  --display-{i}-y: {d['y']}px;")
        lines.append(f"  --display-{i}-w: {d['w']}px;")
        lines.append(f"  --display-{i}-h: {d['h']}px;")
        lines.append(f"  --display-{i}-bg: {d['color']['hex']};")

    mk = result.get("median_key")
    if mk:
        lines.append(f"  --key-w: {mk['w']}px;")
        lines.append(f"  --key-h: {mk['h']}px;")

    g = result.get("grid", {})
    if g:
        lines.append(f"  --grid-cols: {g.get('estimated_cols', '?')};")
        lines.append(f"  --grid-rows: {g.get('estimated_rows', '?')};")

    lines.append("}")
    return "\n".join(lines)

# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Map image UI elements to JSON+CSS")
    parser.add_argument("image", help="Path to image (JPEG/PNG/PDF page)")
    parser.add_argument("--output", "-o", default=None, help="Save JSON to file")
    parser.add_argument("--vis", action="store_true", help="Save annotated visualization")
    parser.add_argument("--css", action="store_true", help="Print CSS custom properties")
    parser.add_argument("--top", type=int, default=30, help="Show top N keys")
    args = parser.parse_args()

    result = build_map(args.image, vis=args.vis)

    out_path = args.output or Path(args.image).with_suffix(".map.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Map saved: {out_path}")

    print(f"\n── Summary ──────────────────────────")
    print(f"All detected rects: {result['all_rects_count']}")
    if result.get("body"):
        b = result["body"]
        print(f"Body:     {b['w']}×{b['h']}px @ ({b['x']},{b['y']})  color={b['color']['hex']}")
    for i, d in enumerate(result.get("display", [])):
        print(f"Display {i}: {d['w']}×{d['h']}px @ ({d['x']},{d['y']})  color={d['color']['hex']}")
    mk = result.get("median_key")
    if mk:
        print(f"Median key: {mk['w']}×{mk['h']}px")
    g = result.get("grid", {})
    if g:
        print(f"Grid: ~{g.get('estimated_cols')} cols × {g.get('estimated_rows')} rows")

    print(f"\n── Top {args.top} keys ──────────────────────────")
    for i, k in enumerate(result.get("keys", [])[:args.top]):
        print(f"  [{i:2d}] {k['w']:3d}×{k['h']:3d}px @ ({k['x']:3d},{k['y']:3d})  {k['color']['hex']}")

    if args.css:
        print("\n── CSS ──────────────────────────────")
        print(map_to_css(result))

if __name__ == "__main__":
    main()
