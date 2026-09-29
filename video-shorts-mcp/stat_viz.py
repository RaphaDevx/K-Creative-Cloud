"""
stat_viz.py — Statistical visualization renderer for the Reel pipeline.

Produces PIL Image objects that can be composited into scene frames.
All renderers match the pipeline's dark-mode aesthetic.

Supported viz types:
  - contingency_table  : 2×2 (or n×m) Vier-Felder-Tafel
  - bar_chart          : Vertical bar chart with labels
  - normal_dist        : Normal distribution curve with optional markers
  - histogram          : Frequency histogram from raw counts
  - scatter            : Scatter plot with optional regression line

Usage in scene JSON:
  "viz": {
    "type": "contingency_table",
    "data": [[50, 10], [5, 35]],
    "row_labels": ["Krank", "Gesund"],
    "col_labels": ["Test +", "Test -"],
    "title": "4-Felder-Tafel: Diagnostiktest",
    "accent_hex": "#4FC3F7"
  }
"""

import io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from PIL import Image
from scipy import stats as scipy_stats


# ── Shared style constants ───────────────────────────────────────────────────

BG_DARK   = "#0d0d0f"
TEXT_WHITE = "#e8e8e8"
TEXT_GRAY  = "#999999"
GRID_COLOR = "#2a2a2a"

def _hex_to_rgb01(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def _apply_dark_style(fig, ax, accent_hex: str):
    accent = _hex_to_rgb01(accent_hex)
    fig.patch.set_facecolor('none')
    ax.set_facecolor((0.04, 0.04, 0.06, 0.7))
    ax.tick_params(colors=TEXT_GRAY, labelsize=11)
    ax.xaxis.label.set_color(TEXT_GRAY)
    ax.yaxis.label.set_color(TEXT_GRAY)
    ax.title.set_color(TEXT_WHITE)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)
    ax.grid(color=GRID_COLOR, linewidth=0.8, alpha=0.7)
    return accent

def _fig_to_pil(fig) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor='none', transparent=True, dpi=144)
    buf.seek(0)
    img = Image.open(buf).convert("RGBA")
    plt.close(fig)
    return img


# ── Vier-Felder-Tafel / Contingency Table ───────────────────────────────────

def render_contingency_table(
    data: list[list],
    row_labels: list[str],
    col_labels: list[str],
    title: str = "",
    accent_hex: str = "#4FC3F7",
    width_px: int = 900,
    height_px: int = 700,
) -> Image.Image:
    """
    Renders a styled 2×2 (or n×m) contingency table as a PIL Image.

    Scene JSON example:
      "viz": {
        "type": "contingency_table",
        "data": [[50, 10], [5, 35]],
        "row_labels": ["Krank", "Gesund"],
        "col_labels": ["Test +", "Test -"],
        "title": "Vier-Felder-Tafel: Diagnostiktest",
        "accent_hex": "#4FC3F7"
      }
    """
    accent = _hex_to_rgb01(accent_hex)
    accent_dim = tuple(c * 0.35 for c in accent)

    nrows = len(data)
    ncols = len(data[0])

    dpi = 144
    fig_w = width_px / dpi
    fig_h = height_px / dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor('none')
    ax.set_facecolor((0.04, 0.04, 0.06, 0.7))
    ax.axis("off")

    # Total cols/rows = data cols + 1 label col / data rows + 1 header row
    total_cols = ncols + 1
    total_rows = nrows + 1

    cell_w = 1.0 / total_cols
    cell_h = 1.0 / total_rows
    pad = 0.008

    def _cell(col, row, text, bg, fg=TEXT_WHITE, fontsize=18, bold=False):
        x = col * cell_w + pad
        y = 1.0 - (row + 1) * cell_h + pad
        w = cell_w - 2 * pad
        h = cell_h - 2 * pad
        rect = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.01",
            facecolor=bg, edgecolor=GRID_COLOR, linewidth=1.2,
            transform=ax.transAxes, clip_on=False
        )
        ax.add_patch(rect)
        ax.text(
            x + w / 2, y + h / 2, text,
            ha="center", va="center",
            color=fg, fontsize=fontsize,
            fontweight="bold" if bold else "normal",
            transform=ax.transAxes
        )

    # Header row: column labels
    _cell(0, 0, "", BG_DARK)  # top-left corner
    for j, label in enumerate(col_labels):
        _cell(j + 1, 0, label, accent_dim, fg=TEXT_WHITE, fontsize=14, bold=True)

    # Data rows
    for i, (row_label, row_data) in enumerate(zip(row_labels, data)):
        _cell(0, i + 1, row_label, accent_dim, fg=TEXT_WHITE, fontsize=14, bold=True)
        total = sum(sum(r) for r in data)
        for j, val in enumerate(row_data):
            pct = f"{val / total * 100:.0f}%" if total > 0 else ""
            cell_text = f"{val}\n{pct}"
            # Diagonal cells (TP/TN) get accent highlight
            is_diagonal = (i == j)
            bg = tuple(c * 0.55 for c in accent) if is_diagonal else "#1a1a1f"
            _cell(j + 1, i + 1, cell_text, bg, fontsize=17, bold=is_diagonal)

    if title:
        ax.set_title(title, color=TEXT_WHITE, fontsize=15, pad=10, fontweight="bold")

    # Accent top line
    fig.add_artist(plt.Line2D([0, 1], [1, 1], transform=fig.transFigure,
                               color=accent_hex, linewidth=3))

    return _fig_to_pil(fig)


# ── Bar Chart ────────────────────────────────────────────────────────────────

def render_bar_chart(
    labels: list[str],
    values: list[float],
    title: str = "",
    y_label: str = "",
    accent_hex: str = "#FFD700",
    highlight_max: bool = True,
    width_px: int = 900,
    height_px: int = 700,
) -> Image.Image:
    """
    Renders a dark-mode bar chart as a PIL Image.

    Scene JSON example:
      "viz": {
        "type": "bar_chart",
        "labels": ["Arithm.", "Geom.", "Harm."],
        "values": [5.5, 4.9, 4.4],
        "title": "Mittelwert-Vergleich",
        "y_label": "Wert",
        "accent_hex": "#FFD700"
      }
    """
    dpi = 144
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi))
    accent = _apply_dark_style(fig, ax, accent_hex)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)

    accent_hex_list = _hex_to_rgb01(accent_hex)
    dim = tuple(c * 0.45 for c in accent_hex_list)

    max_idx = values.index(max(values)) if highlight_max else -1
    colors = [accent_hex_list if i == max_idx else dim for i in range(len(values))]

    bars = ax.bar(labels, values, color=colors, width=0.6, zorder=3,
                  edgecolor=GRID_COLOR, linewidth=0.8)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(values) * 0.02,
                f"{val:g}", ha="center", va="bottom",
                color=TEXT_WHITE, fontsize=13, fontweight="bold")

    ax.set_title(title, color=TEXT_WHITE, fontsize=14, pad=12, fontweight="bold")
    ax.set_ylabel(y_label, color=TEXT_GRAY, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelsize=12, colors=TEXT_WHITE)

    return _fig_to_pil(fig)


# ── Normal Distribution ──────────────────────────────────────────────────────

def render_normal_dist(
    mu: float = 0.0,
    sigma: float = 1.0,
    markers: list[dict] | None = None,
    shade_between: tuple | None = None,
    title: str = "",
    caption: str = "",
    accent_hex: str = "#4FC3F7",
    width_px: int = 900,
    height_px: int = 600,
) -> Image.Image:
    """
    Renders a normal distribution curve.

    markers: [{"label": "μ", "value": 0, "color": "#FFD700"}, ...]
    shade_between: (x_start, x_end) — shade area under curve

    Scene JSON example:
      "viz": {
        "type": "normal_dist",
        "mu": 0,
        "sigma": 1,
        "markers": [{"label": "μ", "value": 0, "color": "#FFD700"}],
        "shade_between": [-1.96, 1.96],
        "title": "95% Konfidenzintervall",
        "accent_hex": "#4FC3F7"
      }
    """
    dpi = 144
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi))
    accent = _apply_dark_style(fig, ax, accent_hex)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.5)

    x_range = 4 * sigma
    x = np.linspace(mu - x_range, mu + x_range, 500)
    y = scipy_stats.norm.pdf(x, mu, sigma)

    # Main curve
    ax.plot(x, y, color=accent_hex, linewidth=2.5, zorder=3)
    ax.fill_between(x, y, alpha=0.12, color=accent_hex)

    # Shaded region
    if shade_between:
        x1, x2 = shade_between
        xs = np.linspace(x1, x2, 300)
        ys = scipy_stats.norm.pdf(xs, mu, sigma)
        ax.fill_between(xs, ys, alpha=0.45, color=accent_hex)
        pct = (scipy_stats.norm.cdf(x2, mu, sigma) -
               scipy_stats.norm.cdf(x1, mu, sigma)) * 100
        ax.text((x1 + x2) / 2, max(ys) * 0.5, f"{pct:.1f}%",
                ha="center", va="center", color=TEXT_WHITE,
                fontsize=14, fontweight="bold")

    # Markers
    for m in (markers or []):
        val = m.get("value", 0)
        label = m.get("label", "")
        color = m.get("color", "#FFD700")
        y_val = scipy_stats.norm.pdf(val, mu, sigma)
        ax.axvline(val, color=color, linewidth=1.8, linestyle="--", alpha=0.85, zorder=4)
        ax.text(val, y_val * 1.08, label, ha="center", va="bottom",
                color=color, fontsize=13, fontweight="bold")

    ax.set_title(title, color=TEXT_WHITE, fontsize=14, pad=10, fontweight="bold")
    ax.set_xlabel(caption or f"N({mu}, {sigma}²)", color=TEXT_GRAY, fontsize=11)
    ax.set_ylabel("f(x)", color=TEXT_GRAY, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_pil(fig)


# ── Histogram ────────────────────────────────────────────────────────────────

def render_histogram(
    data: list[float],
    bins: int = 12,
    title: str = "",
    x_label: str = "",
    accent_hex: str = "#66BB6A",
    width_px: int = 900,
    height_px: int = 600,
) -> Image.Image:
    """
    Scene JSON example:
      "viz": {
        "type": "histogram",
        "data": [12, 15, 14, 10, 18, 22, 19, 13, 11, 16],
        "bins": 8,
        "title": "Häufigkeitsverteilung",
        "x_label": "Wert",
        "accent_hex": "#66BB6A"
      }
    """
    dpi = 144
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi))
    accent = _apply_dark_style(fig, ax, accent_hex)
    ax.set_axisbelow(True)

    arr = np.array(data)
    ax.hist(arr, bins=bins, color=_hex_to_rgb01(accent_hex),
            edgecolor=BG_DARK, linewidth=0.8, zorder=3, alpha=0.85)

    ax.axvline(np.mean(arr), color="#FFD700", linewidth=2,
               linestyle="--", label=f"x̄ = {np.mean(arr):.1f}", zorder=4)
    ax.axvline(np.median(arr), color="#FF7043", linewidth=2,
               linestyle=":", label=f"Median = {np.median(arr):.1f}", zorder=4)

    ax.legend(facecolor="#1a1a1f", edgecolor=GRID_COLOR,
              labelcolor=TEXT_WHITE, fontsize=11)
    ax.set_title(title, color=TEXT_WHITE, fontsize=14, pad=10, fontweight="bold")
    ax.set_xlabel(x_label, color=TEXT_GRAY, fontsize=11)
    ax.set_ylabel("Häufigkeit", color=TEXT_GRAY, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_pil(fig)


# ── Scatter Plot ─────────────────────────────────────────────────────────────

def render_scatter(
    x: list[float],
    y: list[float],
    x_label: str = "X",
    y_label: str = "Y",
    title: str = "",
    regression: bool = True,
    accent_hex: str = "#CE93D8",
    width_px: int = 900,
    height_px: int = 700,
) -> Image.Image:
    """
    Scene JSON example:
      "viz": {
        "type": "scatter",
        "x": [1, 2, 3, 4, 5],
        "y": [2.1, 3.8, 5.2, 7.1, 8.9],
        "x_label": "Lernstunden",
        "y_label": "Prüfungspunkte",
        "title": "Korrelation",
        "regression": true,
        "accent_hex": "#CE93D8"
      }
    """
    dpi = 144
    fig, ax = plt.subplots(figsize=(width_px / dpi, height_px / dpi))
    accent = _apply_dark_style(fig, ax, accent_hex)

    xarr, yarr = np.array(x), np.array(y)
    ax.scatter(xarr, yarr, color=_hex_to_rgb01(accent_hex),
               s=80, alpha=0.85, zorder=3, edgecolors=BG_DARK, linewidths=0.8)

    if regression and len(xarr) >= 2:
        m, b, r, p, _ = scipy_stats.linregress(xarr, yarr)
        xs = np.linspace(xarr.min(), xarr.max(), 100)
        ax.plot(xs, m * xs + b, color="#FFD700", linewidth=2,
                linestyle="--", zorder=4,
                label=f"r = {r:.2f}  |  y = {m:.2f}x + {b:.2f}")
        ax.legend(facecolor="#1a1a1f", edgecolor=GRID_COLOR,
                  labelcolor=TEXT_WHITE, fontsize=11)

    ax.set_title(title, color=TEXT_WHITE, fontsize=14, pad=10, fontweight="bold")
    ax.set_xlabel(x_label, color=TEXT_GRAY, fontsize=11)
    ax.set_ylabel(y_label, color=TEXT_GRAY, fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_pil(fig)


# ── Formula (mathtext) ───────────────────────────────────────────────────────

def render_formula(
    latex: str,
    subtitle: str = "",
    title: str = "",
    accent_hex: str = "#4FC3F7",
    width_px: int = 900,
    height_px: int = 700,  # ignored internally; formula always renders at ~360px tall
    fontsize: int = 38,
) -> Image.Image:
    """
    Renders a mathematical formula using matplotlib mathtext (no LaTeX install needed).
    Use standard LaTeX math notation wrapped in $...$:
      \\frac{a}{b}  \\sum_{i=1}^{n}  \\bar{x}  \\sigma  \\cdot

    Scene JSON example:
      "viz": {
        "type": "formula",
        "latex": "$Cov(x,y) = \\\\frac{\\\\sum(x_i - \\\\bar{x})(y_i - \\\\bar{y})}{N-1}$",
        "subtitle": "N-1 bei Stichprobe, N bei Grundgesamtheit",
        "accent_hex": "#FFD700"
      }
    """
    internal_h = 360
    dpi = 144
    accent_rgb = _hex_to_rgb01(accent_hex)
    fig, ax = plt.subplots(figsize=(width_px / dpi, internal_h / dpi))
    fig.patch.set_facecolor('none')
    ax.set_facecolor((0.04, 0.04, 0.06, 0.7))
    ax.axis("off")

    # Subtle accent box behind formula
    box_top = 0.82 if subtitle else 0.88
    box_bottom = 0.18 if subtitle else 0.12
    rect = FancyBboxPatch(
        (0.04, box_bottom), 0.92, box_top - box_bottom,
        boxstyle="round,pad=0.015",
        facecolor=tuple(c * 0.18 for c in accent_rgb) + (1.0,),
        edgecolor=accent_hex,
        linewidth=2.5,
        transform=ax.transAxes,
        zorder=1,
    )
    ax.add_patch(rect)

    formula_y = 0.58 if subtitle else 0.50
    try:
        ax.text(
            0.5, formula_y, latex,
            ha="center", va="center",
            color=accent_hex,
            fontsize=fontsize,
            transform=ax.transAxes,
            usetex=False,
            math_fontfamily="dejavusans",
            zorder=2,
        )
    except Exception:
        # Fallback: plain text if mathtext parse fails
        plain = latex.replace("$", "").replace("\\", "")
        ax.text(0.5, formula_y, plain, ha="center", va="center",
                color=accent_hex, fontsize=fontsize - 6, transform=ax.transAxes, zorder=2)

    if subtitle:
        ax.text(0.5, 0.24, subtitle,
                ha="center", va="center",
                color=TEXT_GRAY,
                fontsize=12,
                transform=ax.transAxes,
                zorder=2)

    if title:
        ax.text(0.5, 0.94, title,
                ha="center", va="center",
                color=TEXT_WHITE,
                fontsize=11,
                fontweight="bold",
                transform=ax.transAxes,
                zorder=2)

    return _fig_to_pil(fig)


# ── Dispatcher ───────────────────────────────────────────────────────────────

def render_viz(viz: dict, width_px: int = 900, height_px: int = 700) -> Image.Image | None:
    """
    Main entry point. Pass the scene's "viz" dict, get back a PIL Image.

    All renderers accept accent_hex from viz dict (fallback: #4FC3F7).
    """
    vtype = viz.get("type")
    kw = {
        "accent_hex": viz.get("accent_hex", "#4FC3F7"),
        "width_px": width_px,
        "height_px": height_px,
    }

    if vtype == "contingency_table":
        return render_contingency_table(
            data=viz["data"],
            row_labels=viz.get("row_labels", [f"R{i}" for i in range(len(viz["data"]))]),
            col_labels=viz.get("col_labels", [f"C{j}" for j in range(len(viz["data"][0]))]),
            title=viz.get("title", ""),
            **kw,
        )
    elif vtype == "bar_chart":
        return render_bar_chart(
            labels=viz["labels"],
            values=viz["values"],
            title=viz.get("title", ""),
            y_label=viz.get("y_label", ""),
            highlight_max=viz.get("highlight_max", True),
            **kw,
        )
    elif vtype == "normal_dist":
        return render_normal_dist(
            mu=viz.get("mu", 0.0),
            sigma=viz.get("sigma", 1.0),
            markers=viz.get("markers"),
            shade_between=viz.get("shade_between"),
            title=viz.get("title", ""),
            caption=viz.get("caption", ""),
            **kw,
        )
    elif vtype == "histogram":
        return render_histogram(
            data=viz["data"],
            bins=viz.get("bins", 12),
            title=viz.get("title", ""),
            x_label=viz.get("x_label", ""),
            **kw,
        )
    elif vtype == "scatter":
        return render_scatter(
            x=viz["x"],
            y=viz["y"],
            x_label=viz.get("x_label", "X"),
            y_label=viz.get("y_label", "Y"),
            title=viz.get("title", ""),
            regression=viz.get("regression", True),
            **kw,
        )
    elif vtype == "formula":
        return render_formula(
            latex=viz["latex"],
            subtitle=viz.get("subtitle", ""),
            title=viz.get("title", ""),
            fontsize=viz.get("fontsize", 38),
            **kw,
        )
    else:
        print(f"[stat_viz] Unknown viz type: {vtype}")
        return None
