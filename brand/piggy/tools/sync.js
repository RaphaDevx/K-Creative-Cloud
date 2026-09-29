#!/usr/bin/env node
/*
 * Piggy Brand Sync — kopiert generierte Brand-Artefakte nach <Piggy>/src/brand (klar als generiert markiert).
 *   node brand/piggy/tools/sync.js <PiggyProjektordner>
 * Aufgerufen von scripts/export-assets.sh piggy --target brand.
 *
 * Sicherheitsregeln:
 *  - schreibt ausschliesslich unter <Projekt>/src/brand/
 *  - löscht nichts; verwaiste Dateien aus einem früheren Sync werden nur gemeldet
 *  - meldet Dateien, die seit dem letzten Sync manuell verändert wurden (Hash-Vergleich mit .generated.json), bevor sie überschrieben werden
 */
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist');
const project = process.argv[2];
if (!project) { console.error('Usage: sync.js <PiggyProjektordner>'); process.exit(1); }
const TARGET = path.join(path.resolve(project), 'src', 'brand');
if (!fs.existsSync(path.join(path.resolve(project), 'app.json'))) { console.error('✗ Kein Expo-Projekt (app.json fehlt): ' + project); process.exit(1); }
if (!fs.existsSync(path.join(DIST, 'rn/theme.ts'))) { console.error('✗ Erst bauen: bash brand/piggy/build.sh'); process.exit(1); }

const sha = (p) => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 16);
const MANIFEST = path.join(TARGET, '.generated.json');
const prev = fs.existsSync(MANIFEST) ? JSON.parse(fs.readFileSync(MANIFEST, 'utf8')).files : {};

const plan = []; // [src, relDest]
const add = (src, dest) => { if (fs.existsSync(src)) plan.push([src, dest]); };
const walk = (dir, base, destBase, filter) => {
  if (!fs.existsSync(dir)) return;
  for (const f of fs.readdirSync(dir)) {
    const p = path.join(dir, f);
    if (fs.statSync(p).isDirectory()) walk(p, base, destBase, filter);
    else if (!filter || filter(p)) plan.push([p, path.join(destBase, path.relative(base, p))]);
  }
};

// Code + Tokens
walk(path.join(DIST, 'rn'), path.join(DIST, 'rn'), '');
// Icons (SVG, alle Modi)
walk(path.join(DIST, 'icons/svg'), path.join(DIST, 'icons/svg'), 'icons/svg');
// Varianten-Assets (@1x/@2x/@3x) + App-Icons/Splash (1024)
const index = JSON.parse(fs.readFileSync(path.join(DIST, 'variants/index.json'), 'utf8'));
for (const v of index) {
  const d = path.join(DIST, 'variants', v.id);
  for (const k of ['logo', 'signet']) for (const s of ['', '@2x', '@3x']) add(path.join(d, `${k}${s}.png`), `variants/${v.id}/${k}${s}.png`);
  add(path.join(d, `piggy-appicon-${v.id}-1024.png`), `app-icons/${v.id}.png`);
  add(path.join(d, `piggy-adaptive-${v.id}-1024.png`), `app-icons/${v.id}-adaptive.png`);
  add(path.join(d, `piggy-splash-${v.id}-1024.png`), `app-icons/${v.id}-splash.png`);
}
// Logos (SVG für Web, PNG)
walk(path.join(DIST, 'logo'), path.join(DIST, 'logo'), 'logo');
// Maskottchen
walk(path.join(DIST, '3d/sprites'), path.join(DIST, '3d/sprites'), 'mascot', (p) => !p.includes('_master'));
add(path.join(DIST, '3d/piggy.glb'), 'mascot/piggy.glb');
// Doku
add(path.join(ROOT, 'INTEGRATION.md'), 'INTEGRATION.md');

// README / Marker
const readme = `# src/brand — GENERIERT\n\n**Nicht manuell bearbeiten.** Alles in diesem Ordner wird von K-Creative-Cloud erzeugt und beim nächsten Sync überschrieben.\n\n- Quelle: \`K-Creative-Cloud/brand/tokens/piggy.json\` + \`K-Creative-Cloud/brand/piggy/\`\n- Neu erzeugen: \`bash K-Creative-Cloud/scripts/export-assets.sh piggy --target brand\` (oder \`bash K-Creative-Cloud/brand/piggy/build.sh --sync\`)\n- Einbau in die App: siehe \`INTEGRATION.md\`\n- Stand: siehe \`.generated.json\`\n`;

const changedByHand = [];
const files = {};
let n = 0;
for (const [src, relDest] of plan) {
  const dest = path.join(TARGET, relDest);
  if (fs.existsSync(dest) && prev[relDest] && sha(dest) !== prev[relDest]) changedByHand.push(relDest);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
  files[relDest] = sha(dest);
  n++;
}
fs.writeFileSync(path.join(TARGET, 'README.md'), readme);
files['README.md'] = sha(path.join(TARGET, 'README.md'));
const orphans = Object.keys(prev).filter((k) => !(k in files));
fs.writeFileSync(MANIFEST, JSON.stringify({
  generator: 'K-Creative-Cloud/brand/piggy/tools/sync.js',
  source: 'K-Creative-Cloud/brand/tokens/piggy.json',
  syncedAt: new Date().toISOString(),
  files,
}, null, 1) + '\n');

console.log(`  ✓ ${n} Dateien → ${TARGET}`);
if (changedByHand.length) console.log(`  ⚠ Manuell verändert seit letztem Sync (wurden überschrieben): ${changedByHand.join(', ')}`);
if (orphans.length) console.log(`  ℹ Verwaist (nicht mehr generiert, NICHT gelöscht): ${orphans.join(', ')}`);
if (!fs.existsSync(path.join(DIST, '3d/piggy.glb'))) console.log('  ℹ Kein 3D-Export gefunden — build.sh ohne --no-3d ausführen');
