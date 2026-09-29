/*
 * Piggy Brand Core — Icon-Generator.
 * Quelle: icons/sources.json (Primitive auf 24er-Raster), Style: icons/style.json.
 * Ausgabe: Element-Liste mit Farb-Rollen (primary | secondary | onPrimary), daraus SVG oder React-Native-Code.
 *
 * Rollen der Primitive:
 *   base   — Silhouette. outline: nur Kontur · filled: gefüllt primary · duotone: gefüllt secondary + Kontur primary
 *   detail — immer Strich. Mit "in": true liegt es auf einer base-Fläche → in filled: onPrimary (Aussparung)
 *   dot    — immer gefüllt (kleine Punkte). Mit "in": true → in filled: onPrimary
 */
(function (g) {
  'use strict';
  const PB = (g.PiggyBrand = g.PiggyBrand || {});
  const r2 = (n) => Math.round(n * 100) / 100;

  // ------------------------------------------------------------ geometry → path
  function roundedPolygon(pts, radius, closed) {
    if (!radius || pts.length < 3) {
      return 'M' + pts.map((p) => r2(p[0]) + ',' + r2(p[1])).join(' L') + (closed ? ' Z' : '');
    }
    const n = pts.length;
    let d = '';
    const corner = (i) => {
      const p = pts[i], a = pts[(i - 1 + n) % n], b = pts[(i + 1) % n];
      const la = Math.hypot(a[0] - p[0], a[1] - p[1]), lb = Math.hypot(b[0] - p[0], b[1] - p[1]);
      const r = Math.min(radius, la / 2, lb / 2);
      const pa = [p[0] + ((a[0] - p[0]) / la) * r, p[1] + ((a[1] - p[1]) / la) * r];
      const pb = [p[0] + ((b[0] - p[0]) / lb) * r, p[1] + ((b[1] - p[1]) / lb) * r];
      return { pa, pb, p };
    };
    if (closed) {
      const cs = pts.map((_, i) => corner(i));
      d = `M${r2(cs[0].pb[0])},${r2(cs[0].pb[1])}`;
      for (let i = 1; i <= n; i++) {
        const c = cs[i % n];
        d += ` L${r2(c.pa[0])},${r2(c.pa[1])} Q${r2(c.p[0])},${r2(c.p[1])} ${r2(c.pb[0])},${r2(c.pb[1])}`;
      }
      return d + ' Z';
    }
    d = `M${r2(pts[0][0])},${r2(pts[0][1])}`;
    for (let i = 1; i < n - 1; i++) {
      const p = pts[i], a = pts[i - 1], b = pts[i + 1];
      const la = Math.hypot(a[0] - p[0], a[1] - p[1]), lb = Math.hypot(b[0] - p[0], b[1] - p[1]);
      const r = Math.min(radius, la / 2, lb / 2);
      const pa = [p[0] + ((a[0] - p[0]) / la) * r, p[1] + ((a[1] - p[1]) / la) * r];
      const pb = [p[0] + ((b[0] - p[0]) / lb) * r, p[1] + ((b[1] - p[1]) / lb) * r];
      d += ` L${r2(pa[0])},${r2(pa[1])} Q${r2(p[0])},${r2(p[1])} ${r2(pb[0])},${r2(pb[1])}`;
    }
    const last = pts[n - 1];
    return d + ` L${r2(last[0])},${r2(last[1])}`;
  }

  function gearPoints(cx, cy, ro, ri, teeth) {
    const pts = [];
    const step = (Math.PI * 2) / teeth;
    for (let i = 0; i < teeth; i++) {
      const a = i * step - Math.PI / 2;
      const w = step * 0.22;
      pts.push([cx + Math.cos(a - w) * ro, cy + Math.sin(a - w) * ro]);
      pts.push([cx + Math.cos(a + w) * ro, cy + Math.sin(a + w) * ro]);
      pts.push([cx + Math.cos(a + step / 2 - w * 1.1) * ri, cy + Math.sin(a + step / 2 - w * 1.1) * ri]);
      pts.push([cx + Math.cos(a + step / 2 + w * 1.1) * ri, cy + Math.sin(a + step / 2 + w * 1.1) * ri]);
    }
    return pts;
  }

  function starPoints(cx, cy, r, inner, spikes) {
    const pts = [];
    for (let i = 0; i < spikes * 2; i++) {
      const a = (i / (spikes * 2)) * Math.PI * 2 - Math.PI / 2;
      const rr = i % 2 ? r * inner : r;
      pts.push([cx + Math.cos(a) * rr, cy + Math.sin(a) * rr]);
    }
    return pts;
  }

  /** Primitive → {tag, attrs} ohne Farben. */
  function geom(p, style) {
    const cr = style.cornerRadius;
    const R = (v) => (v === 'auto' || v === undefined ? cr : v === 'full' ? 999 : v);
    switch (p.t) {
      case 'circle': return { tag: 'circle', a: { cx: p.cx, cy: p.cy, r: p.r } };
      case 'ellipse': return { tag: 'ellipse', a: { cx: p.cx, cy: p.cy, rx: p.rx, ry: p.ry } };
      case 'rect': {
        const r = Math.min(R(p.r), p.w / 2, p.h / 2);
        return { tag: 'rect', a: { x: p.x, y: p.y, width: p.w, height: p.h, rx: r2(r), ry: r2(r) } };
      }
      case 'line': return { tag: 'path', a: { d: `M${p.x1},${p.y1} L${p.x2},${p.y2}` } };
      case 'poly': return { tag: 'path', a: { d: roundedPolygon(p.pts, p.r === undefined ? cr * 0.6 : R(p.r), !!p.closed) } };
      case 'path': return { tag: 'path', a: { d: p.d } };
      case 'gear': return { tag: 'path', a: { d: roundedPolygon(gearPoints(p.cx, p.cy, p.ro, p.ri, p.teeth), Math.min(cr * 0.5, 1), true) } };
      case 'star': return { tag: 'path', a: { d: roundedPolygon(starPoints(p.cx, p.cy, p.r, p.inner || 0.42, p.spikes || 4), Math.min(cr * 0.35, 1), true) } };
      default: throw new Error('Unbekanntes Icon-Primitiv: ' + p.t);
    }
  }

  /**
   * Icon → Elementliste. Jedes Element: {tag, a:{...geometrie, fill, stroke, strokeWidth, ...}} mit Farbrollen als Strings
   * 'primary' | 'secondary' | 'onPrimary' | 'none'.
   */
  function iconElements(def, style, mode) {
    mode = mode || style.fill;
    const sw = style.strokeWidth;
    const out = [];
    const strokeAttrs = (role) => ({ stroke: role, strokeWidth: sw, strokeLinecap: 'round', strokeLinejoin: 'round' });
    for (const p of def.shapes) {
      const role = p.role || 'base';
      const gm = geom(p, style);
      let a;
      if (role === 'base') {
        if (mode === 'outline') a = { fill: 'none', ...strokeAttrs('primary') };
        else if (mode === 'filled') a = { fill: 'primary', ...strokeAttrs('primary') };
        else a = { fill: 'secondary', ...strokeAttrs('primary') };
      } else if (role === 'detail') {
        const col = mode === 'filled' && p.in ? 'onPrimary' : 'primary';
        a = { fill: 'none', ...strokeAttrs(col) };
        if (p.thin) a.strokeWidth = r2(sw * 0.8);
      } else if (role === 'dot') {
        a = { fill: mode === 'filled' && p.in ? 'onPrimary' : 'primary', stroke: 'none' };
      } else throw new Error('Unbekannte Rolle ' + role);
      out.push({ tag: gm.tag, a: { ...gm.a, ...a } });
    }
    return out;
  }

  const kebab = (k) => k.replace(/[A-Z]/g, (m) => '-' + m.toLowerCase());

  function elementsToSvg(els, colors, size) {
    const col = (v) => (v in colors ? colors[v] : v);
    const inner = els.map((e) => {
      const attrs = Object.entries(e.a).map(([k, v]) => `${kebab(k)}="${['fill', 'stroke'].includes(k) ? col(v) : v}"`).join(' ');
      return `<${e.tag} ${attrs}/>`;
    }).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="${size || 24}" height="${size || 24}">${inner}</svg>`;
  }

  /** Style-Palette (Token-Pfade) gegen aufgelöste Tokens → Farbwerte. */
  function styleColors(style, resolved) {
    const c = {};
    for (const [role, path] of Object.entries(style.palette)) {
      const v = PB.getPath(resolved, path);
      if (!v) throw new Error(`Icon-Style: Token ${path} nicht gefunden`);
      c[role] = v;
    }
    c.none = 'none';
    return c;
  }

  function renderIcon(name, sources, style, resolved, opts) {
    opts = opts || {};
    const def = sources.icons[name];
    if (!def) throw new Error('Icon nicht gefunden: ' + name);
    const els = iconElements(def, style, opts.mode);
    const colors = Object.assign(styleColors(style, resolved), opts.colors || {});
    return elementsToSvg(els, colors, opts.size);
  }

  Object.assign(PB, { iconElements, elementsToSvg, styleColors, renderIcon, roundedPolygon });
  if (typeof module !== 'undefined' && module.exports) module.exports = PB;
})(typeof globalThis !== 'undefined' ? globalThis : this);
