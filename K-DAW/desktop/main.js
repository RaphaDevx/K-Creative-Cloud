const { app, BrowserWindow, dialog, shell, ipcMain } = require('electron');
const { autoUpdater } = require('electron-updater');
const { spawn } = require('child_process');
const http  = require('http');
const path  = require('path');
const fs    = require('fs');

const PORT = 9879;
const SERVER_URL = `http://127.0.0.1:${PORT}`;

let serverProcess = null;
let mainWindow    = null;

// ── Start Python server ────────────────────────────────────────────────────────
function startServer() {
  let bin, args, cwd;

  if (app.isPackaged) {
    // Production: use the PyInstaller binary bundled in Resources/
    bin  = path.join(process.resourcesPath, 'kdaw-server', 'kdaw-server');
    args = [];
    cwd  = app.getPath('userData');
  } else {
    // Dev: run Python directly from the repo
    bin  = 'python3';
    args = [path.join(__dirname, '..', 'backend', 'web_server.py')];
    cwd  = path.join(__dirname, '..');
  }

  serverProcess = spawn(bin, args, {
    cwd,
    env: { ...process.env, KDAW_PORT: String(PORT), KDAW_HOST: '127.0.0.1' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  serverProcess.stdout.on('data', d => console.log('[server]', d.toString().trim()));
  serverProcess.stderr.on('data', d => console.error('[server]', d.toString().trim()));
  serverProcess.on('exit', code => {
    console.log('[server] exited with code', code);
    if (code !== 0 && mainWindow) {
      mainWindow.webContents.executeJavaScript(
        `document.body.innerHTML = '<div style="color:#ff4d6d;font-family:monospace;padding:40px">Server crashed (code ${code}). Please restart K-DAW.</div>';`
      ).catch(() => {});
    }
  });
}

// ── Wait for server to be ready ────────────────────────────────────────────────
function waitForServer(resolve, attempt = 0) {
  http.get(SERVER_URL, () => resolve(true))
    .on('error', () => {
      if (attempt < 60) setTimeout(() => waitForServer(resolve, attempt + 1), 300);
      else resolve(false);   // give up after 18 s
    });
}

// ── Create main window ─────────────────────────────────────────────────────────
async function createWindow() {
  mainWindow = new BrowserWindow({
    width:  1440,
    height: 900,
    minWidth:  800,
    minHeight: 600,
    title: 'K-DAW',
    backgroundColor: '#0e0e12',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // Loading screen while server boots
  await mainWindow.loadFile(path.join(__dirname, 'loading.html'));

  const ready = await new Promise(resolve => waitForServer(resolve));

  if (!ready) {
    dialog.showErrorBox('K-DAW — Server Error',
      'The backend server failed to start within 18 seconds.\n\n' +
      'Make sure no other process is using port 9879.');
    app.quit();
    return;
  }

  mainWindow.loadURL(SERVER_URL);

  // Open external links in the system browser, not in Electron
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => { mainWindow = null; });
  return mainWindow;
}

// ── Auto-updater (electron-updater via R2) ────────────────────────────────────
autoUpdater.autoDownload = false;
autoUpdater.autoInstallOnAppQuit = true;

autoUpdater.on('update-available', (info) => {
  injectUpdateBar(info.version);
});

autoUpdater.on('download-progress', (p) => {
  const pct = Math.round(p.percent);
  mainWindow?.webContents.executeJavaScript(`
    const bar = document.getElementById('k-update-bar');
    if (bar) { const btn = bar.querySelector('.k-update-btn'); if (btn) btn.textContent = 'Downloading… ${pct}%'; }
  `).catch(() => {});
});

autoUpdater.on('update-downloaded', (info) => {
  mainWindow?.webContents.executeJavaScript(`
    const bar = document.getElementById('k-update-bar');
    if (bar) {
      const btn = bar.querySelector('.k-update-btn');
      if (btn) { btn.textContent = 'Install & Restart'; btn.onclick = () => window.kdawElectron.installUpdate(); btn.style.background = 'rgba(255,255,255,0.25)'; }
      const lbl = bar.querySelector('.k-update-label');
      if (lbl) lbl.textContent = '✓ Download complete — ready to install';
    }
  `).catch(() => {});
});

autoUpdater.on('error', (err) => { console.warn('[updater]', err.message); });

function injectUpdateBar(version) {
  const js = `(function() {
    if (document.getElementById('k-update-bar')) return;
    const bar = document.createElement('div');
    bar.id = 'k-update-bar';
    bar.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;background:linear-gradient(135deg,#7c5cfc 0%,#5c8afc 100%);color:#fff;padding:9px 16px 9px 20px;display:flex;align-items:center;gap:12px;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif;font-size:13px;font-weight:500;box-shadow:0 2px 20px rgba(124,92,252,.5);user-select:none;-webkit-app-region:no-drag';
    bar.innerHTML = \`<span style="opacity:.8;font-size:15px">⬆</span><span class="k-update-label" style="flex:1">K-DAW <strong style="font-weight:700">v${version}</strong> ist verfügbar</span><button class="k-update-btn" onclick="window.kdawElectron.downloadUpdate()" style="background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.35);color:#fff;padding:5px 16px;border-radius:7px;cursor:pointer;font-size:12px;font-weight:600;white-space:nowrap">Update laden</button><button onclick="this.closest('#k-update-bar').remove()" style="background:none;border:none;color:rgba(255,255,255,.55);cursor:pointer;font-size:20px;line-height:1;padding:2px 6px;border-radius:4px" title="Später">×</button>\`;
    document.body.prepend(bar);
    document.body.style.paddingTop = (parseInt(document.body.style.paddingTop)||0) + 46 + 'px';
  })()`;
  mainWindow?.webContents.executeJavaScript(js).catch(() => {});
}

ipcMain.handle('download-update', () => autoUpdater.downloadUpdate().catch(console.warn));
ipcMain.handle('install-update',  () => autoUpdater.quitAndInstall(false, true));

// ── App lifecycle ──────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  startServer();
  createWindow().then(() => {
    if (mainWindow) setTimeout(() => autoUpdater.checkForUpdates().catch(() => {}), 3000);
    setInterval(() => { if (mainWindow) autoUpdater.checkForUpdates().catch(() => {}); }, 4 * 60 * 60 * 1000);
  });

  app.on('activate', () => {
    if (!mainWindow) createWindow();
  });
});

app.on('window-all-closed', () => {
  killServer();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', killServer);

function killServer() {
  if (serverProcess) {
    try { serverProcess.kill('SIGTERM'); } catch (_) {}
    serverProcess = null;
  }
}
