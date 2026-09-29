const path = require('path');
const fs = require('fs');

// afterPack hook: fix Python3.framework symlink structure so electron-builder can sign it.
//
// Problem: electron-builder dereferences symlinks when copying extraResources into the .app,
// turning Python3.framework's proper versioned layout into an ambiguous mix of real files
// and directories. codesign then refuses with "bundle format is ambiguous".
//
// Fix: restore the standard versioned framework symlinks (no keychain ops — those would
// interfere with electron-builder's own subsequent signing pass).
module.exports = async function (context) {
  const { electronPlatformName, appOutDir } = context;
  if (electronPlatformName !== 'darwin') return;

  const appName = fs.readdirSync(appOutDir).find(f => f.endsWith('.app'));
  if (!appName) return;

  const frameworkPath = path.join(
    appOutDir, appName, 'Contents', 'Resources',
    'kdaw-server', '_internal', 'Python3.framework'
  );
  if (!fs.existsSync(frameworkPath)) {
    console.log('[fix-framework] Python3.framework not found — skipping');
    return;
  }

  const versionsDir = path.join(frameworkPath, 'Versions');
  const versions = fs.readdirSync(versionsDir).filter(v => v !== 'Current');
  const version = versions[0];
  if (!version) { console.log('[fix-framework] no version dir — skipping'); return; }

  // 1. Versions/Current: real dir → symlink to e.g. "3.9"
  const currentPath = path.join(versionsDir, 'Current');
  if (fs.existsSync(currentPath) && !fs.lstatSync(currentPath).isSymbolicLink()) {
    // Merge any unique files from Current into the version dir before removing it
    for (const f of fs.readdirSync(currentPath)) {
      const dst = path.join(versionsDir, version, f);
      if (!fs.existsSync(dst)) {
        fs.renameSync(path.join(currentPath, f), dst);
      }
    }
    fs.rmSync(currentPath, { recursive: true });
    fs.symlinkSync(version, currentPath);
    console.log(`[fix-framework] Versions/Current → ${version}`);
  }

  // 2. Python3.framework/Python3: real binary → symlink to Versions/Current/Python3
  const rootBin = path.join(frameworkPath, 'Python3');
  if (fs.existsSync(rootBin) && !fs.lstatSync(rootBin).isSymbolicLink()) {
    fs.unlinkSync(rootBin);
    fs.symlinkSync('Versions/Current/Python3', rootBin);
    console.log('[fix-framework] Python3.framework/Python3 → symlink');
  }

  // 3. Python3.framework/Resources: real dir → symlink to Versions/Current/Resources
  const rootResources = path.join(frameworkPath, 'Resources');
  if (fs.existsSync(rootResources) && !fs.lstatSync(rootResources).isSymbolicLink()) {
    const versionResources = path.join(versionsDir, version, 'Resources');
    if (!fs.existsSync(versionResources)) {
      fs.renameSync(rootResources, versionResources);
    } else {
      fs.rmSync(rootResources, { recursive: true });
    }
    fs.symlinkSync('Versions/Current/Resources', rootResources);
    console.log('[fix-framework] Python3.framework/Resources → symlink');
  }

  console.log('[fix-framework] Python3.framework structure fixed ✓');
};
