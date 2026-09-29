#!/usr/bin/env node
/**
 * K-Creative Desktop — Pre-build Validator
 *
 * Checks that catch real bugs before they ship:
 *   1. HTML files referenced in main.js are in package.json files[]
 *   2. IPC channels in preload.js have handlers in main.js
 *   3. extraResources/extraFiles source paths exist
 *   4. No raw alert() calls in HTML (bypasses toast system)
 *   5. Version field present and semver-shaped
 */

const fs   = require('fs');
const path = require('path');

const ROOT    = path.join(__dirname, '..');
const PKG     = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));
const MAIN    = fs.readFileSync(path.join(ROOT, 'main.js'), 'utf8');
const PRELOAD = fs.readFileSync(path.join(ROOT, 'preload.js'), 'utf8');

let errors = 0;
let warnings = 0;

function pass(msg)  { console.log(`  ✅  ${msg}`); }
function fail(msg)  { console.error(`  ❌  ${msg}`); errors++; }
function warn(msg)  { console.warn (`  ⚠️   ${msg}`); warnings++; }
function section(s) { console.log(`\n── ${s} ${'─'.repeat(50 - s.length)}`); }

// ── 1. file:// HTML URLs in main.js → must be in package.json files[] ────
section('1  HTML files vs package.json');

const packedFiles = (PKG.build?.files || []).filter(f => !f.startsWith('!'));

// Only check HTML files that are loaded via file:// (LOADING_URL / DASHBOARD_URL pattern).
// Files in extraResources are served via HTTP and don't need to be in files[].
// Strategy: find const XXXXX_URL = `file://...` pattern, extract basename.
const fileUrlConsts = [...MAIN.matchAll(/const\s+\w+\s*=\s*`file:\/\/\$\{[^}]+\}\s*[/\\]([^`'"\s]+\.html)`/g)]
  .map(m => m[1]);

// Also catch simpler: path.join(__dirname, 'foo.html') used in loadURL / LOADING_URL
const pathjoinRefs  = [...MAIN.matchAll(/path\.join\(__dirname,\s*['"]([^'"]+\.html)['"]\)/g)]
  .map(m => path.basename(m[1]));

const uniqueHtmlRefs = [...new Set([...fileUrlConsts.map(f => path.basename(f)), ...pathjoinRefs])];

for (const f of uniqueHtmlRefs) {
  const inFiles = packedFiles.some(p => p === f || p.endsWith('/' + f));
  if (inFiles) {
    pass(`${f} → in package.json files[]`);
  } else {
    fail(`${f} loaded via file:// in main.js but MISSING from package.json files[] — BLACK SCREEN when packaged`);
  }
}

if (uniqueHtmlRefs.length === 0) warn('No file:// HTML references found in main.js — check manually');

// ── 2. IPC channels: preload.js → main.js ─────────────────────────────────
section('2  IPC channel completeness');

const invokeChannels = [...PRELOAD.matchAll(/ipcRenderer\.invoke\(['"]([^'"]+)['"]/g)].map(m => m[1]);
const sendChannels   = [...PRELOAD.matchAll(/ipcRenderer\.send\(['"]([^'"]+)['"]/g)].map(m => m[1]);
const handleChannels = [...MAIN.matchAll(/ipcMain\.handle\(['"]([^'"]+)['"]/g)].map(m => m[1]);
const onChannels     = [...MAIN.matchAll(/ipcMain\.on\(['"]([^'"]+)['"]/g)].map(m => m[1]);

for (const ch of [...new Set(invokeChannels)]) {
  if (handleChannels.includes(ch)) {
    pass(`invoke('${ch}') → ipcMain.handle exists`);
  } else {
    fail(`invoke('${ch}') in preload but NO ipcMain.handle('${ch}') in main.js`);
  }
}

for (const ch of [...new Set(sendChannels)]) {
  if (onChannels.includes(ch)) {
    pass(`send('${ch}') → ipcMain.on exists`);
  } else {
    fail(`send('${ch}') in preload but NO ipcMain.on('${ch}') in main.js`);
  }
}

if (invokeChannels.length + sendChannels.length === 0) warn('No IPC channels found in preload.js');

// ── 3. extraResources / extraFiles source paths exist ─────────────────────
section('3  extraResources / extraFiles source paths');

const entries = [
  ...(PKG.build?.extraResources || []),
  ...(PKG.build?.extraFiles     || []),
];

for (const entry of entries) {
  const from = entry.from || entry;
  if (typeof from !== 'string') continue;
  const abs = path.resolve(ROOT, from);
  if (fs.existsSync(abs)) {
    pass(`${from} → exists`);
  } else {
    // warn, not fail — some paths only exist after PyInstaller runs
    warn(`${from} → NOT FOUND (may be missing or built by a later step)`);
  }
}

if (entries.length === 0) pass('No extraResources/extraFiles defined');

// ── 4. No raw alert() in HTML files ───────────────────────────────────────
section('4  No raw alert() in HTML files');

const htmlFiles = fs.readdirSync(ROOT).filter(f => f.endsWith('.html'));
for (const f of htmlFiles) {
  const src = fs.readFileSync(path.join(ROOT, f), 'utf8');
  // Strip comments and strings, look for bare alert(
  const stripped = src.replace(/\/\/[^\n]*/g, '').replace(/\/\*[\s\S]*?\*\//g, '');
  const alertMatches = [...stripped.matchAll(/\balert\s*\(/g)];
  if (alertMatches.length > 0) {
    warn(`${f} contains ${alertMatches.length} alert() call(s) — use showToast() instead`);
  } else {
    pass(`${f} — no alert() calls`);
  }
}

// ── 5. Version sanity ──────────────────────────────────────────────────────
section('5  Version sanity');

const ver = PKG.version;
if (/^\d+\.\d+\.\d+$/.test(ver)) {
  pass(`version "${ver}" is valid semver`);
} else {
  fail(`version "${ver}" is not valid semver (expected X.Y.Z)`);
}

// Check publish URL is set
const pub = PKG.build?.publish?.[0];
if (pub?.url) {
  pass(`publish URL: ${pub.url}`);
} else {
  fail('No publish URL in package.json build.publish — OTA updates will not work');
}

// ── Summary ────────────────────────────────────────────────────────────────
console.log('\n' + '═'.repeat(54));
if (errors === 0 && warnings === 0) {
  console.log('  🟢  All checks passed — safe to build');
  process.exit(0);
} else if (errors === 0) {
  console.log(`  🟡  ${warnings} warning(s) — build may proceed but review above`);
  process.exit(0);
} else {
  console.error(`  🔴  ${errors} error(s), ${warnings} warning(s) — FIX BEFORE BUILDING`);
  process.exit(1);
}
