/*
 * Piggy Brand Core — Tokens, Kontrast, Varianten-Resolver
 * Läuft identisch in Node (CLI) und im Browser (creator/index.html).
 * Keine Abhängigkeiten.
 */
(function (g) {
  'use strict';
  const PB = (g.PiggyBrand = g.PiggyBrand || {});

  // ---------------------------------------------------------------- helpers
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const isObj = (v) => v && typeof v === 'object' && !Array.isArray(v);
  const REF = /^\{([^}]+)\}$/;

  function getPath(obj, path) {
    const parts = Array.isArray(path) ? path : String(path).split('.');
    let cur = obj;
    for (const p of parts) {
      if (cur == null || !(p in cur)) return undefined;
      cur = cur[p];
    }
    return cur;
  }

  function setPath(obj, path, value) {
    const parts = String(path).split('.');
    let cur = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      if (!isObj(cur[parts[i]])) cur[parts[i]] = {};
      cur = cur[parts[i]];
    }
    cur[parts[parts.length - 1]] = value;
  }

  // ---------------------------------------------------------------- resolve
  /** Löst alle "{a.b.c}"-Referenzen rekursiv auf. Wirft bei Zyklus oder fehlendem Ziel. */
  function resolveTokens(raw) {
    const src = clone(raw);
    const cache = new Map();

    function resolveRef(path, stack) {
      if (cache.has(path)) return clone(cache.get(path));
      if (stack.includes(path)) throw new Error('Token-Zyklus: ' + stack.concat(path).join(' -> '));
      const target = getPath(src, path);
      if (target === undefined) throw new Error('Token-Referenz nicht gefunden: {' + path + '} (in ' + (stack[stack.length - 1] || 'root') + ')');
      const val = walk(target, stack.concat(path));
      cache.set(path, val);
      return clone(val);
    }

    function walk(v, stack) {
      if (typeof v === 'string') {
        const m = v.match(REF);
        return m ? resolveRef(m[1], stack) : v;
      }
      if (Array.isArray(v)) return v.map((x) => walk(x, stack));
      if (isObj(v)) {
        const out = {};
        for (const k of Object.keys(v)) out[k] = walk(v[k], stack);
        return out;
      }
      return v;
    }
    return walk(src, []);
  }

  /** Wendet Overrides {"primitive.color.pink.400": "#..."} auf eine Kopie der Roh-Tokens an. */
  function applyOverrides(raw, overrides) {
    const t = clone(raw);
    if (overrides) for (const k of Object.keys(overrides)) setPath(t, k, overrides[k]);
    return t;
  }

  /** Flacht ein Objekt zu {"a.b.c": wert} ab (für Creator-Formulare / Diffs). */
  function flatten(obj, prefix, out) {
    out = out || {};
    for (const k of Object.keys(obj)) {
      const p = prefix ? prefix + '.' + k : k;
      if (isObj(obj[k])) flatten(obj[k], p, out);
      else out[p] = obj[k];
    }
    return out;
  }

  // ---------------------------------------------------------------- color
  function hexToRgb(hex) {
    let h = String(hex).replace('#', '').trim();
    if (h.length === 3) h = h.split('').map((c) => c + c).join('');
    if (h.length === 8) h = h.slice(0, 6);
    const n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgbToHex(r, g2, b) {
    const c = (x) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, '0');
    return '#' + c(r) + c(g2) + c(b);
  }
  function mix(a, b, t) {
    const A = hexToRgb(a), B = hexToRgb(b);
    return rgbToHex(A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t);
  }
  /** sRGB hex -> linear [r,g,b] 0..1 (für Blender-Materialien). */
  function hexToLinear(hex) {
    return hexToRgb(hex).map((c) => {
      c /= 255;
      return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
  }
  function luminance(hex) {
    const [r, g2, b] = hexToLinear(hex);
    return 0.2126 * r + 0.7152 * g2 + 0.0722 * b;
  }
  function contrastRatio(a, b) {
    const la = luminance(a), lb = luminance(b);
    const [hi, lo] = la > lb ? [la, lb] : [lb, la];
    return (hi + 0.05) / (lo + 0.05);
  }
  /** WCAG 2.1 AA: text 4.5, large text 3.0, UI-Komponenten/Grafik 3.0 */
  const AA = { text: 4.5, large: 3.0, ui: 3.0 };

  function contrastReport(raw) {
    const t = resolveTokens(raw);
    const pairs = raw.contrastPairs || [];
    return pairs.map((p) => {
      const fg = getPath(t, p.fg), bg = getPath(t, p.bg);
      const ratio = contrastRatio(fg, bg);
      const need = AA[p.kind] || 4.5;
      const pass = ratio >= need;
      const status = pass ? 'PASS' : p.exempt ? 'EXEMPT' : 'FAIL';
      return { ...p, fgHex: fg, bgHex: bg, ratio: Math.round(ratio * 100) / 100, need, pass, status };
    });
  }

  // ---------------------------------------------------------------- lint (8pt / modular scale)
  function lintTokens(raw) {
    const issues = [];
    const t = resolveTokens(raw);
    const P = t.primitive;
    for (const [k, v] of Object.entries(P.space)) if (v % 4 !== 0) issues.push(`primitive.space.${k}=${v} ist kein Vielfaches von 4`);
    for (const [k, v] of Object.entries(P.radius)) if (k !== 'full' && v % 4 !== 0) issues.push(`primitive.radius.${k}=${v} ist kein Vielfaches von 4`);
    for (const [k, v] of Object.entries(P.size)) if (v % 8 !== 0) issues.push(`primitive.size.${k}=${v} ist kein Vielfaches von 8`);
    const base = P.type.base, r = P.type.ratio;
    for (const [n, s] of Object.entries(P.type.scale)) {
      const ideal = base * Math.pow(r, Number(n));
      if (Math.abs(ideal - s.size) > 0.6) issues.push(`primitive.type.scale.${n}.size=${s.size} weicht von ${base}×${r}^${n}=${ideal.toFixed(2)} ab`);
      if (s.lineHeight % 4 !== 0) issues.push(`primitive.type.scale.${n}.lineHeight=${s.lineHeight} nicht auf 4pt-Raster`);
      if (s.lineHeight < s.size * 1.1) issues.push(`primitive.type.scale.${n}.lineHeight=${s.lineHeight} zu eng für ${s.size}`);
    }
    // Semantic/Component dürfen keine Roh-Hexwerte enthalten (Schichten-Regel)
    const walkRaw = (obj, path) => {
      for (const [k, v] of Object.entries(obj)) {
        const p = path + '.' + k;
        if (isObj(v)) walkRaw(v, p);
        else if (typeof v === 'string' && /^#/.test(v)) issues.push(`${p}=${v}: Roh-Farbwert ausserhalb von primitive (Schichten-Regel)`);
        else if (typeof v === 'number') issues.push(`${p}=${v}: Roh-Zahl ausserhalb von primitive (Schichten-Regel)`);
      }
    };
    walkRaw(raw.semantic || {}, 'semantic');
    walkRaw(raw.component || {}, 'component');
    return issues;
  }

  // ---------------------------------------------------------------- variants
  const pad2 = (n) => String(n).padStart(2, '0');
  const mdOf = (date) => pad2(date.getMonth() + 1) + '-' + pad2(date.getDate());

  function inWindow(md, from, to) {
    return from <= to ? md >= from && md <= to : md >= from || md <= to; // Fenster über Jahreswechsel
  }

  const BASE_VARIANT = { id: 'base', kind: 'base', name: 'Basis', palette: {}, accessories: [], background: null };

  /**
   * currentVariant(date, variants)
   * Regeln: Monat schlägt Saison. Gleichstand (mehr als ein Treffer auf der höchsten Ebene) → Basis.
   */
  function currentVariant(date, variants) {
    const d = date instanceof Date ? date : new Date(date);
    const md = mdOf(d);
    const hits = (variants || []).filter((v) => v.enabled !== false && v.valid && inWindow(md, v.valid.from, v.valid.to));
    for (const kind of ['month', 'season']) {
      const k = hits.filter((v) => v.kind === kind);
      if (k.length === 1) return k[0];
      if (k.length > 1) return BASE_VARIANT;
    }
    return BASE_VARIANT;
  }

  function validateVariant(v) {
    const errs = [];
    if (!v.id) errs.push('id fehlt');
    if (!['month', 'season'].includes(v.kind)) errs.push(`${v.id}: kind muss month|season sein`);
    const re = /^\d\d-\d\d$/;
    if (!v.valid || !re.test(v.valid.from) || !re.test(v.valid.to)) errs.push(`${v.id}: valid.from/to müssen MM-DD sein`);
    if (v.kind === 'month' && v.valid) {
      const m = pad2(v.valid.month);
      if (!v.valid.from.startsWith(m) || !v.valid.to.startsWith(m)) errs.push(`${v.id}: Monatsvariante muss innerhalb von Monat ${m} liegen`);
    }
    return errs;
  }

  /** Farben, die Logo/Accessoires/App-Icon brauchen, aus (ggf. überschriebenen) Tokens. */
  function artColors(raw, variant) {
    const t = resolveTokens(applyOverrides(raw, variant && variant.palette));
    return {
      m: t.component.mascot,
      logo: t.component.logo,
      icon: t.component.appIcon,
      splash: t.component.splash,
      a: t.semantic.color.accessory,
      bg: t.semantic.color.bg,
      tokens: t,
    };
  }

  Object.assign(PB, {
    clone, getPath, setPath, resolveTokens, applyOverrides, flatten,
    hexToRgb, rgbToHex, mix, hexToLinear, luminance, contrastRatio, contrastReport, AA, lintTokens,
    currentVariant, validateVariant, inWindow, BASE_VARIANT, artColors, mdOf,
  });
  if (typeof module !== 'undefined' && module.exports) module.exports = PB;
})(typeof globalThis !== 'undefined' ? globalThis : this);
