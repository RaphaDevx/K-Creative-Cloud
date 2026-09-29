#!/usr/bin/env node
/*
 * Tests: Varianten-Resolver (JS-Lib + generiertes variants.ts), Token-Schichten, Legacy-Aliase, Kontrast (semantic).
 *   node brand/piggy/tools/test.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const ROOT = path.resolve(__dirname, '..');
const PB = require(path.join(ROOT, 'lib/tokens.js'));

let passed = 0;
const t = (name, fn) => { try { fn(); passed++; console.log('  ✓', name); } catch (e) { console.error('  ✗', name, '\n    ', e.message); process.exitCode = 1; } };

const raw = JSON.parse(fs.readFileSync(path.join(ROOT, '../tokens/piggy.json'), 'utf8'));
const variants = fs.readdirSync(path.join(ROOT, 'seasons')).filter((f) => /^(month|season)-.*\.json$/.test(f))
  .map((f) => JSON.parse(fs.readFileSync(path.join(ROOT, 'seasons', f), 'utf8')));
const d = (s) => { const [y, m, dd] = s.split('-').map(Number); return new Date(y, m - 1, dd); };

const CASES = [
  ['2026-01-03', 'month-01-neujahr'],      // Monat schlägt Saison (Winter)
  ['2026-01-15', 'season-winter'],
  ['2026-02-20', 'month-02-fasnacht'],
  ['2026-03-14', 'season-winter'],         // Winter läuft bis 19.3.
  ['2026-03-20', 'month-03-steuern'],      // Frühling + Steuern → Monat
  ['2026-05-20', 'season-spring'],
  ['2026-06-20', 'month-06-badi'],
  ['2026-08-01', 'month-08-bundesfeier'],
  ['2026-08-15', 'season-summer'],
  ['2026-09-29', 'month-09-alpabzug'],
  ['2026-10-10', 'season-autumn'],
  ['2026-12-24', 'month-12-samichlaus'],
  ['2026-12-28', 'season-winter'],         // Fenster über Jahreswechsel
];

function resolverSuite(label, resolve) {
  for (const [date, want] of CASES) t(`${label}: ${date} → ${want}`, () => assert.strictEqual(resolve(d(date), variants).id, want));
  const m1 = { id: 'month-x-a', kind: 'month', name: 'A', valid: { month: 7, from: '07-01', to: '07-31' } };
  const m2 = { id: 'month-x-b', kind: 'month', name: 'B', valid: { month: 7, from: '07-10', to: '07-20' } };
  const s1 = { id: 'season-x-a', kind: 'season', name: 'SA', valid: { from: '06-01', to: '08-31' } };
  const s2 = { id: 'season-x-b', kind: 'season', name: 'SB', valid: { from: '07-01', to: '09-30' } };
  t(`${label}: Gleichstand zweier Monate → Basis`, () => assert.strictEqual(resolve(d('2026-07-15'), [m1, m2, s1]).id, 'base'));
  t(`${label}: ein Monat + zwei Saisons → Monat`, () => assert.strictEqual(resolve(d('2026-07-15'), [m1, s1, s2]).id, 'month-x-a'));
  t(`${label}: Gleichstand zweier Saisons → Basis`, () => assert.strictEqual(resolve(d('2026-08-15'), [s1, s2]).id, 'base'));
  t(`${label}: kein Treffer → Basis`, () => assert.strictEqual(resolve(d('2026-11-30'), [m1]).id, 'base'));
  if (label === 'lib') t(`${label}: enabled:false wird ignoriert`, () => assert.strictEqual(resolve(d('2026-07-15'), [{ ...m1, enabled: false }, s1]).id, 'season-x-a'));
}

resolverSuite('lib', PB.currentVariant);

// Generiertes variants.ts mit Piggys TypeScript transpilieren und gegen dieselben Fälle prüfen (Parität).
const tsFile = path.join(ROOT, 'dist/rn/variants/variants.ts');
const tsLib = path.resolve(ROOT, '../../../Piggy/node_modules/typescript');
if (fs.existsSync(tsFile) && fs.existsSync(tsLib)) {
  const ts = require(tsLib);
  const js = ts.transpileModule(fs.readFileSync(tsFile, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2019 } }).outputText;
  const mod = { exports: {} };
  new Function('module', 'exports', 'require', js)(mod, mod.exports, () => ({}));
  resolverSuite('variants.ts', (date, vs) => mod.exports.currentVariant(date, vs.map((v) => ({ ...v, kind: v.kind }))));
} else console.log('  ℹ variants.ts-Parität übersprungen (Build oder Piggy/node_modules/typescript fehlt)');

t('Tokens: keine Lint-Verstösse (8pt, Modular Scale, Schichten)', () => assert.deepStrictEqual(PB.lintTokens(raw), []));
t('Tokens: Legacy colors/radius/fontSize/shadow identisch zu v1', () => {
  const old = JSON.parse(fs.readFileSync(path.join(ROOT, '../tokens/.history/piggy.v1-flat.json'), 'utf8'));
  const r = PB.resolveTokens(raw);
  for (const k of ['colors', 'radius', 'fontSize', 'shadow']) assert.deepStrictEqual(r[k], old[k], k);
});
t('Kontrast: alle nicht-Legacy-Paare PASS oder dokumentiert EXEMPT', () => {
  const bad = PB.contrastReport(raw).filter((r) => r.status === 'FAIL' && !r.use.startsWith('LEGACY'));
  assert.deepStrictEqual(bad.map((b) => b.use), []);
});
t('Varianten: ≥4 Saisons, ≥12 Monate, alle valide', () => {
  assert.ok(variants.filter((v) => v.kind === 'season').length >= 4);
  assert.ok(variants.filter((v) => v.kind === 'month').length >= 12);
  assert.deepStrictEqual(variants.flatMap(PB.validateVariant), []);
});
t('Palette-Wechsel: anderes primitive → andere Maskottchen-Farbe', () => {
  const alt = PB.resolveTokens(PB.applyOverrides(raw, { 'primitive.color.pink.400': '#7FD1FF' }));
  assert.strictEqual(alt.component.mascot.skin, '#7FD1FF');
});

console.log(`\n${passed} Tests bestanden${process.exitCode ? ' — FEHLER vorhanden' : ''}`);
