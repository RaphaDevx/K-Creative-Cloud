#!/usr/bin/env node
/*
 * Piggy Brand Build — Tokens → Kontrast/Lint → Logos/Varianten/Icons (SVG+PNG) → RN-Code → Creator-Daten.
 * Das 3D-Maskottchen baut build.sh separat mit Blender (braucht dist/tokens/piggy.resolved.json von hier).
 *
 *   node brand/piggy/tools/build.js [--tokens <pfad>] [--no-png] [--strict]
 *
 * --tokens  alternative Token-Datei (z.B. Export aus dem Creator) statt brand/tokens/piggy.json
 * --dist    anderes Ausgabeverzeichnis (z.B. Paletten-Demo), Creator-Daten werden dann nicht überschrieben
 * --strict  Exit 1 bei Kontrast-FAIL oder Lint-Fehler
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');            // brand/piggy
const BRAND = path.resolve(ROOT, '..');                // brand
const KCC = path.resolve(BRAND, '..');                 // K-Creative-Cloud
require(path.join(ROOT, 'lib/tokens.js'));
require(path.join(ROOT, 'lib/art.js'));
const PB = require(path.join(ROOT, 'lib/icons.js'));

const args = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const TOKENS = path.resolve(opt('--tokens') || path.join(BRAND, 'tokens/piggy.json'));
const NO_PNG = args.includes('--no-png');
const STRICT = args.includes('--strict');
const DIST = path.resolve(opt('--dist') || path.join(ROOT, 'dist'));
const IS_DEFAULT_DIST = !opt('--dist');

const w = (p, s) => { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, s); };
const rel = (p) => path.relative(KCC, p);
const log = (...a) => console.log('  ', ...a);

// ------------------------------------------------------------------ 1. Tokens
const raw = JSON.parse(fs.readFileSync(TOKENS, 'utf8'));
const T = PB.resolveTokens(raw);
w(path.join(DIST, 'tokens/piggy.resolved.json'), JSON.stringify(T, null, 2) + '\n');
log('✓ Tokens aufgelöst →', rel(path.join(DIST, 'tokens/piggy.resolved.json')));

// ------------------------------------------------------------------ 2. Lint + Kontrast
const lint = PB.lintTokens(raw);
const report = PB.contrastReport(raw);
const fails = report.filter((r) => r.status === 'FAIL');
let md = `# Piggy — Kontrast-Report (WCAG 2.1 AA)\n\n_Generiert von brand/piggy/tools/build.js — nicht manuell bearbeiten._\n\n`;
md += `Schwellen: Text 4.5:1 · grosser Text 3:1 · UI-Komponenten/Icons 3:1\n\n`;
md += `| Status | Ratio | Soll | Vordergrund | Hintergrund | Verwendung |\n|---|---|---|---|---|---|\n`;
for (const r of report) md += `| ${r.status} | ${r.ratio.toFixed(2)} | ${r.need} | \`${r.fg}\` ${r.fgHex} | \`${r.bg}\` ${r.bgHex} | ${r.use}${r.exempt ? ' — ' + r.exempt : ''} |\n`;
md += `\n## Lint (8pt-Raster, Modular Scale, Token-Schichten)\n\n`;
md += lint.length ? lint.map((l) => `- ✗ ${l}`).join('\n') + '\n' : '- ✓ keine Verstösse\n';
w(path.join(DIST, 'palette/contrast-report.md'), md);
w(path.join(DIST, 'palette/contrast-report.json'), JSON.stringify({ lint, report }, null, 2) + '\n');
log(`✓ Kontrast: ${report.filter((r) => r.pass).length} PASS · ${report.filter((r) => r.status === 'EXEMPT').length} EXEMPT · ${fails.length} FAIL · Lint: ${lint.length} Verstösse`);
for (const f of fails) log(`  ✗ FAIL ${f.ratio} < ${f.need}: ${f.use}`);

// ------------------------------------------------------------------ 3. Varianten laden + validieren
const SEASONS = path.join(ROOT, 'seasons');
const variants = fs.readdirSync(SEASONS).filter((f) => /^(month|season)-.*\.json$/.test(f)).sort()
  .map((f) => JSON.parse(fs.readFileSync(path.join(SEASONS, f), 'utf8')));
const vErr = variants.flatMap(PB.validateVariant);
for (const v of variants) {
  for (const a of v.accessories || []) if (!PB.ACCESSORIES[a]) vErr.push(`${v.id}: unbekanntes Accessoire ${a}`);
  for (const b of v.background || []) if (!PB.BACKGROUNDS[b]) vErr.push(`${v.id}: unbekannter Hintergrund ${b}`);
  try { PB.resolveTokens(PB.applyOverrides(raw, v.palette)); } catch (e) { vErr.push(`${v.id}: ${e.message}`); }
}
if (vErr.length) { console.error('✗ Varianten-Fehler:\n' + vErr.join('\n')); process.exit(1); }
const ALL = [PB.BASE_VARIANT, ...variants];
log(`✓ ${variants.length} Varianten validiert (${variants.filter((v) => v.kind === 'season').length} Saisons, ${variants.filter((v) => v.kind === 'month').length} Monate)`);

// ------------------------------------------------------------------ 4. SVGs
const png = []; // [svgPath, pngPath, width, height?]
const LOGO = path.join(DIST, 'logo');
w(path.join(LOGO, 'piggy-logo-horizontal.svg'), PB.renderLogo(raw, null, { layout: 'horizontal', uid: 'h' }));
w(path.join(LOGO, 'piggy-logo-stacked.svg'), PB.renderLogo(raw, null, { layout: 'stacked', uid: 's' }));
w(path.join(LOGO, 'piggy-signet.svg'), PB.renderSignet(raw, null, { uid: 'g' }));
w(path.join(LOGO, 'piggy-wordmark.svg'), PB.renderWordmark(raw, null, { uid: 'w' }));
png.push([path.join(LOGO, 'piggy-logo-horizontal.svg'), path.join(LOGO, 'piggy-logo-horizontal.png'), 1200]);
png.push([path.join(LOGO, 'piggy-logo-stacked.svg'), path.join(LOGO, 'piggy-logo-stacked.png'), 600]);
png.push([path.join(LOGO, 'piggy-signet.svg'), path.join(LOGO, 'piggy-signet-512.png'), 512]);
png.push([path.join(LOGO, 'piggy-wordmark.svg'), path.join(LOGO, 'piggy-wordmark.png'), 1024]);

const VAR = path.join(DIST, 'variants');
const index = [];
const vWarn = [];
for (const v of ALL) {
  const d = path.join(VAR, v.id), n = (k) => path.join(d, `piggy-${k}-${v.id}`);
  w(n('logo') + '.svg', PB.renderLogo(raw, v, { layout: 'horizontal', uid: 'l' }));
  w(n('logo-stacked') + '.svg', PB.renderLogo(raw, v, { layout: 'stacked', uid: 'k' }));
  w(n('signet') + '.svg', PB.renderSignet(raw, v, { uid: 'g' }));
  w(n('appicon') + '.svg', PB.renderAppIcon(raw, v, { uid: 'i' }));
  w(n('adaptive') + '.svg', PB.renderAppIcon(raw, v, { uid: 'a', adaptive: true }));
  w(n('splash') + '.svg', PB.renderSplash(raw, v, { uid: 'p' }));
  w(n('splash-screen') + '.svg', PB.renderSplash(raw, v, { uid: 'q', screen: true }));
  png.push([n('appicon') + '.svg', n('appicon') + '-1024.png', 1024]);
  png.push([n('adaptive') + '.svg', n('adaptive') + '-1024.png', 1024]);
  png.push([n('splash') + '.svg', n('splash') + '-1024.png', 1024]);
  png.push([n('splash-screen') + '.svg', n('splash-screen') + '.png', 1284]);
  png.push([n('logo') + '.svg', n('logo') + '.png', 1200]);
  for (const [s, k] of [[1, ''], [2, '@2x'], [3, '@3x']]) {
    png.push([n('logo') + '.svg', path.join(d, `logo${k}.png`), 240 * s]);
    png.push([n('signet') + '.svg', path.join(d, `signet${k}.png`), 128 * s]);
  }
  const vt = PB.resolveTokens(PB.applyOverrides(raw, v.palette));
  const cr = PB.contrastRatio(vt.component.splash.wordmark, vt.component.splash.bg);
  if (cr < 3) vWarn.push(`${v.id}: Splash-Wortmarke ${vt.component.splash.wordmark} auf ${vt.component.splash.bg} = ${cr.toFixed(2)}:1 (< 3:1 grosser Text)`);
  index.push({ id: v.id, kind: v.kind, name: v.name, valid: v.valid || null, accessories: v.accessories, background: v.background || [], splashBg: vt.component.splash.bg, note: v.note || '' });
}
for (const m of vWarn) log('  ⚠ ' + m);
w(path.join(VAR, 'index.json'), JSON.stringify(index, null, 2) + '\n');
log(`✓ Logo + ${ALL.length} Varianten (Logo, Signet, App-Icon, Adaptive, Splash) als SVG`);

// Icons
const ISRC = JSON.parse(fs.readFileSync(path.join(ROOT, 'icons/sources.json'), 'utf8'));
const ISTYLE = JSON.parse(fs.readFileSync(opt('--icon-style') || path.join(ROOT, 'icons/style.json'), 'utf8'));
const ICON = path.join(DIST, 'icons');
const names = Object.keys(ISRC.icons);
const MODES = ['outline', 'filled', 'duotone'];
for (const m of MODES) for (const nme of names) w(path.join(ICON, 'svg', m, `${nme}.svg`), PB.renderIcon(nme, ISRC, ISTYLE, T, { mode: m }));
// Übersicht
{
  const cols = 12, cell = 40, rowsPer = Math.ceil(names.length / cols), H = (rowsPer * 3) * cell + 3 * 28 + 16, W = cols * cell + 24;
  let body = `<rect width="${W}" height="${H}" fill="${T.semantic.color.bg.surface}"/>`;
  MODES.forEach((m, mi) => {
    const y0 = mi * (rowsPer * cell + 28) + 12;
    body += `<text x="12" y="${y0 + 12}" font-family="sans-serif" font-size="11" font-weight="700" fill="${T.semantic.color.text.secondary}">${m.toUpperCase()} · stroke ${ISTYLE.strokeWidth} · radius ${ISTYLE.cornerRadius}</text>`;
    names.forEach((nme, i) => {
      const inner = PB.renderIcon(nme, ISRC, ISTYLE, T, { mode: m }).replace(/<svg[^>]*>/, '').replace('</svg>', '');
      body += `<g transform="translate(${12 + (i % cols) * cell + 8} ${y0 + 22 + Math.floor(i / cols) * cell})">${inner}</g>`;
    });
  });
  w(path.join(ICON, 'piggy-icons-overview.svg'), `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}">${body}</svg>`);
  png.push([path.join(ICON, 'piggy-icons-overview.svg'), path.join(ICON, 'piggy-icons-overview.png'), W * 3]);
}
log(`✓ ${names.length} Icons × ${MODES.length} Modi als SVG (Style "${ISTYLE.name}")`);

// ------------------------------------------------------------------ 5. React-Native-Code (→ sync nach Piggy/src/brand)
const RN = path.join(DIST, 'rn');
const HDR = (src) => `// AUTO-GENERATED von K-Creative-Cloud/brand/piggy/tools/build.js — NICHT manuell bearbeiten.\n// Quelle: ${src}\n// Neu erzeugen: bash K-Creative-Cloud/brand/piggy/build.sh --sync\n`;
const ts = (o) => JSON.stringify(o, null, 2);

w(path.join(RN, 'tokens.json'), JSON.stringify(T, null, 2) + '\n');
w(path.join(RN, 'theme.ts'), `${HDR('brand/tokens/piggy.json')}
/** Schicht 1 — reine Werte (Farbrampen, 4pt-Abstände, Radien, Modular Scale 16×1.25^n). */
export const primitive = ${ts(T.primitive)} as const;

/** Schicht 2 — Bedeutung (bg/text/brand/icon/status/border/mascot). Screens sollten nur diese Ebene nutzen. */
export const semantic = ${ts(T.semantic)} as const;

/** Schicht 3 — Komponenten (tabBar, button, card, icon, mascot, logo, appIcon, splash). */
export const component = ${ts(T.component)} as const;

/**
 * Legacy-Aliase — identisch zu src/constants/design.ts (C/R/S). Ermöglicht einen schrittweisen Umstieg:
 *   import { C } from '@/constants/design'  →  import { legacy } from '@/brand/theme'; const { C } = legacy;
 */
export const legacy = {
  C: ${ts(T.colors)},
  R: ${ts(T.radius)},
  S: ${ts(T.fontSize)},
} as const;

export const theme = { primitive, semantic, component } as const;
export type PiggyTheme = typeof theme;
export default theme;
`);

// Icon-Komponente
{
  // Geometrie pro Primitive (Modus-unabhängig) + Rolle
  const geomOf = {};
  for (const nme of names) {
    const els = PB.iconElements(ISRC.icons[nme], ISTYLE, 'outline');
    geomOf[nme] = ISRC.icons[nme].shapes.map((p, i) => {
      const e = els[i];
      const g = {};
      for (const [k, v] of Object.entries(e.a)) if (!['fill', 'stroke', 'strokeWidth', 'strokeLinecap', 'strokeLinejoin'].includes(k)) g[k] = v;
      const out = [e.tag, g, p.role || 'base'];
      if (p.in) out.push(1); else if (p.thin) out.push(0);
      if (p.thin) out.push(1);
      return out;
    });
  }
  const pal = PB.styleColors(ISTYLE, T);
  const union = names.map((n) => `'${n}'`).join('\n  | ');
  w(path.join(RN, 'icons/PiggyIcon.tsx'), `${HDR('brand/piggy/icons/sources.json + icons/style.json')}
import React from 'react';
import Svg, { Path, Circle, Rect, Ellipse } from 'react-native-svg';
import type { StyleProp, ViewStyle } from 'react-native';

export type PiggyIconName =
  | ${union};
export type PiggyIconMode = 'outline' | 'filled' | 'duotone';

/** Style-Definition zum Generierungszeitpunkt (brand/piggy/icons/style.json). */
export const PIGGY_ICON_STYLE = {
  name: '${ISTYLE.name}',
  mode: '${ISTYLE.fill}' as PiggyIconMode,
  strokeWidth: ${ISTYLE.strokeWidth},
  cornerRadius: ${ISTYLE.cornerRadius},
  primary: '${pal.primary}',
  secondary: '${pal.secondary}',
  onPrimary: '${pal.onPrimary}',
} as const;

type Tag = 'path' | 'circle' | 'rect' | 'ellipse';
type Role = 'base' | 'detail' | 'dot';
/** [tag, geometrie, rolle, liegtAufBase?, dünn?] — Logik gespiegelt aus K-Creative lib/icons.js → iconElements() */
type Shape = [Tag, Record<string, string | number>, Role, (0 | 1)?, (0 | 1)?];

export const PIGGY_ICONS: Record<PiggyIconName, Shape[]> = ${JSON.stringify(geomOf)};

export const PIGGY_ICON_NAMES = Object.keys(PIGGY_ICONS) as PiggyIconName[];

export type PiggyIconProps = {
  name: PiggyIconName;
  size?: number;
  mode?: PiggyIconMode;
  /** Primärfarbe (Kontur/Füllung). Default: component.icon.primary */
  color?: string;
  /** Duotone-Füllung. Default: component.icon.secondary */
  secondaryColor?: string;
  /** Aussparungen im filled-Modus. Default: component.icon.onPrimary */
  onColor?: string;
  strokeWidth?: number;
  style?: StyleProp<ViewStyle>;
};

const TAGS = { path: Path, circle: Circle, rect: Rect, ellipse: Ellipse } as const;

export function PiggyIcon({
  name, size = 24, mode = PIGGY_ICON_STYLE.mode,
  color = PIGGY_ICON_STYLE.primary, secondaryColor = PIGGY_ICON_STYLE.secondary, onColor = PIGGY_ICON_STYLE.onPrimary,
  strokeWidth = PIGGY_ICON_STYLE.strokeWidth, style,
}: PiggyIconProps) {
  const shapes = PIGGY_ICONS[name];
  if (!shapes) return null;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" style={style}>
      {shapes.map(([tag, g, role, inside, thin], i) => {
        const El = TAGS[tag] as React.ComponentType<any>;
        const sw = thin ? strokeWidth * 0.8 : strokeWidth;
        const stroke = { strokeWidth: sw, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
        let p: Record<string, unknown>;
        if (role === 'base') {
          p = mode === 'outline' ? { fill: 'none', stroke: color, ...stroke }
            : mode === 'filled' ? { fill: color, stroke: color, ...stroke }
            : { fill: secondaryColor, stroke: color, ...stroke };
        } else if (role === 'detail') {
          p = { fill: 'none', stroke: mode === 'filled' && inside ? onColor : color, ...stroke };
        } else {
          p = { fill: mode === 'filled' && inside ? onColor : color };
        }
        return <El key={i} {...g} {...p} />;
      })}
    </Svg>
  );
}

export default PiggyIcon;
`);
  // Ionicons → Piggy Mapping
  const map = {};
  for (const nme of names) for (const ion of ISRC.icons[nme].ionicons) if (!(ion in map)) map[ion] = nme;
  w(path.join(RN, 'icons/ioniconsMap.ts'), `${HDR('brand/piggy/icons/sources.json (Feld "ionicons")')}
import type { PiggyIconName, PiggyIconMode } from './PiggyIcon';

/** Für die spätere Migration: Ionicons-Name → Piggy-Icon. "-outline" ⇒ outline, sonst filled. */
export const IONICONS_TO_PIGGY: Record<string, PiggyIconName> = ${ts(map)};

export function ioniconToPiggy(ion: string): { name: PiggyIconName; mode: PiggyIconMode } | null {
  const name = IONICONS_TO_PIGGY[ion];
  if (!name) return null;
  return { name, mode: ion.endsWith('-outline') ? 'outline' : 'filled' };
}
`);
  w(path.join(RN, 'icons/index.ts'), `${HDR('generated')}export * from './PiggyIcon';\nexport * from './ioniconsMap';\n`);
}

// Varianten + Resolver
{
  const req = index.map((v) => `  '${v.id}': {\n    logo: require('./${v.id}/logo.png'),\n    signet: require('./${v.id}/signet.png'),\n  },`).join('\n');
  w(path.join(RN, 'variants/variants.ts'), `${HDR('brand/piggy/seasons/*.json')}
import type { ImageSourcePropType } from 'react-native';

export type VariantKind = 'base' | 'season' | 'month';
export type PiggyVariant = {
  id: string;
  kind: VariantKind;
  name: string;
  /** MM-DD inklusiv; from > to = über Jahreswechsel */
  valid: { month?: number; from: string; to: string } | null;
  accessories: string[];
  background: string[];
  splashBg: string;
  note: string;
};

export const PIGGY_VARIANTS: PiggyVariant[] = ${ts(index)} as PiggyVariant[];

export const BASE_VARIANT = PIGGY_VARIANTS.find((v) => v.id === 'base')!;

const pad2 = (n: number) => String(n).padStart(2, '0');
const inWindow = (md: string, from: string, to: string) => (from <= to ? md >= from && md <= to : md >= from || md <= to);

/**
 * Gültige Variante für ein Datum. Regeln (identisch zu K-Creative lib/tokens.js → currentVariant):
 *   1. Monat schlägt Saison.
 *   2. Mehr als ein Treffer auf der entscheidenden Ebene (Gleichstand) → Basis-Logo.
 *   3. Kein Treffer → Basis-Logo.
 */
export function currentVariant(date: Date = new Date(), variants: PiggyVariant[] = PIGGY_VARIANTS): PiggyVariant {
  const md = pad2(date.getMonth() + 1) + '-' + pad2(date.getDate());
  const hits = variants.filter((v) => v.kind !== 'base' && v.valid && inWindow(md, v.valid.from, v.valid.to));
  for (const kind of ['month', 'season'] as const) {
    const k = hits.filter((v) => v.kind === kind);
    if (k.length === 1) return k[0];
    if (k.length > 1) return BASE_VARIANT;
  }
  return BASE_VARIANT;
}

/** Gerenderte Assets je Variante (@1x/@2x/@3x, Metro wählt automatisch). Logo 240 pt breit, Signet 128 pt. */
export const VARIANT_ASSETS: Record<string, { logo: ImageSourcePropType; signet: ImageSourcePropType }> = {
${req}
};
`);
  w(path.join(RN, 'variants/index.ts'), `${HDR('generated')}export * from './variants';\n`);
}

// Maskottchen-Map (Sprites existieren erst nach dem Blender-Schritt)
{
  const SPR = path.join(DIST, '3d/sprites');
  const sprites = fs.existsSync(SPR) ? fs.readdirSync(SPR).filter((f) => /^piggy-mascot-.*\.png$/.test(f) && !/@\dx/.test(f)).map((f) => f.replace('.png', '')) : [];
  const keyOf = (f) => f.replace('piggy-mascot-', '');
  w(path.join(RN, 'mascot/mascot.ts'), `${HDR('brand/piggy/3d/build_piggy.py (Blender)')}
import type { ImageSourcePropType } from 'react-native';

/** Posen/Ausdrücke als transparente Sprites, Basisgrösse 256 pt (@1x/@2x/@3x). Schlüssel: <pose>-<ausdruck>. */
export const MASCOT_SPRITES = {
${sprites.map((f) => `  '${keyOf(f)}': require('./${f}.png') as ImageSourcePropType,`).join('\n')}
} as const;
export type MascotSprite = keyof typeof MASCOT_SPRITES;
export const MASCOT_SPRITE_SIZE = 256;

/**
 * 3D-Modell: ./piggy.glb (glTF 2.0, Rig + Shape Keys + Aktionen pose_idle/pose_cheer/pose_catch/anim_idle).
 * Bewusst NICHT per require() eingebunden: Metro kennt .glb erst nach assetExts-Erweiterung (siehe INTEGRATION.md).
 * Morph Targets: eye.* closed|wide|sad · brow.* up|sad|happy|angry · mouth open|O|frown|smirk · tongue open|O
 */
export const MASCOT_GLB_PATH = 'src/brand/mascot/piggy.glb';
`);
}

w(path.join(RN, 'index.ts'), `${HDR('generated')}
export * from './theme';
export * from './icons';
export * from './variants';
export * from './mascot/mascot';
`);
log('✓ React-Native-Code: theme.ts, icons/PiggyIcon.tsx, icons/ioniconsMap.ts, variants/variants.ts, mascot/mascot.ts');

// ------------------------------------------------------------------ 6. Creator-Daten (file://-tauglich, kein fetch nötig)
if (IS_DEFAULT_DIST) w(path.join(ROOT, 'creator/data.js'), `// AUTO-GENERATED von tools/build.js — Startdaten für den Creator.\nwindow.PIGGY_DATA = ${JSON.stringify({ tokens: raw, variants, iconSources: ISRC, iconStyle: ISTYLE, generatedAt: new Date().toISOString() })};\n`);
log('✓ Creator-Daten → brand/piggy/creator/data.js');

// ------------------------------------------------------------------ 7. PNG-Rasterisierung (Inkscape, ein Shell-Prozess)
if (!NO_PNG) {
  const cmds = png.map(([svg, out, width]) => {
    fs.mkdirSync(path.dirname(out), { recursive: true });
    return `file-open:${svg}; export-type:png; export-width:${width}; export-filename:${out}; export-do; file-close`;
  }).join('\n') + '\nquit\n';
  const r = spawnSync('inkscape', ['--shell'], { input: cmds, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 });
  const missing = png.filter(([, out]) => !fs.existsSync(out));
  if (missing.length) { console.error('✗ PNG fehlt:', missing.map((m) => rel(m[1])).join(', ')); process.exit(1); }
  log(`✓ ${png.length} PNGs gerendert (Inkscape)`);
  // Übersicht aller App-Icons
  const icons = ALL.map((v) => path.join(VAR, v.id, `piggy-appicon-${v.id}-1024.png`));
  try {
    execFileSync('montage', ['-label', '%t', '-pointsize', '14', '-background', '#ffffff', '-geometry', '256x256+6+6', '-tile', '6x', ...icons, path.join(VAR, 'piggy-variants-overview.png')]);
    log('✓ Varianten-Übersicht → ' + rel(path.join(VAR, 'piggy-variants-overview.png')));
  } catch (e) { log('ℹ montage (ImageMagick) nicht verfügbar — Übersicht übersprungen'); }
}

if (STRICT && (fails.length || lint.length)) { console.error('✗ --strict: Kontrast- oder Lint-Fehler'); process.exit(1); }
console.log('✓ Piggy Brand Build fertig');
