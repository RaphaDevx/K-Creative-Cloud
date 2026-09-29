/**
 * K-Creative Studio — Electron Main Process
 *
 * Features:
 *   - Starts FastAPI Python backend (studio/server.py)
 *   - Opens /live split-screen interface (DJ + Claude terminal)
 *   - chokidar watches live_engine/ → hot-reload IPC to renderer
 *   - electron-updater: silent background updates via GitHub Releases
 *   - Sentry crash reporting (set K_SENTRY_DSN env var to enable)
 *   - Feature flags: fetched from GitHub raw on startup, cached in-memory
 *
 * Launch flags:
 *   --kiosk   fullscreen kiosk mode (no window chrome)
 *   --dev     open DevTools on start
 */
const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const fs   = require('fs');

let mainWindow;
let backendProcess;
let watcher;

const REPO_DIR    = path.join(__dirname, '..');
const STUDIO_DIR  = path.join(__dirname, '..', 'studio');
const ENGINE_DIR  = path.join(__dirname, '..', 'live_engine');
const BACKEND_PORT    = 47200;
const BACKEND_URL     = `http://localhost:${BACKEND_PORT}`;
const LIVE_URL        = `${BACKEND_URL}/live`;
const LOADING_URL     = `file://${path.join(__dirname, 'loading.html')}`;
const DASHBOARD_URL   = `file://${path.join(__dirname, 'dashboard.html')}`;
const DESIGNER_URL    = `file://${path.join(__dirname, 'icon-designer.html')}`;
const BRAND_DATA_FILE = path.join(app.getPath('userData'), 'k-creative-brand.json');

const IS_KIOSK = process.argv.includes('--kiosk');
const IS_DEV   = process.argv.includes('--dev');

// ── Logging ───────────────────────────────────────────────────────────────────
const log = require('electron-log');
log.transports.file.level  = 'info';
log.transports.console.level = IS_DEV ? 'debug' : 'warn';
log.info('[K-Creative] Starting…');

// ── Sentry (optional — set K_SENTRY_DSN in environment) ──────────────────────
try {
  const Sentry = require('@sentry/electron/main');
  const dsn = process.env.K_SENTRY_DSN;
  if (dsn) {
    Sentry.init({
      dsn,
      release: `k-creative-studio@${app.getVersion()}`,
      environment: app.isPackaged ? 'production' : 'development',
    });
    log.info('[Sentry] Crash reporting enabled');
  }
} catch (e) {
  log.warn('[Sentry] Not available:', e.message);
}

// ── Feature flags ─────────────────────────────────────────────────────────────
const FLAGS_URL =
  'https://raw.githubusercontent.com/RaphaDevx/K-Creative-Cloud/main/feature_flags.json';
const FLAGS_LOCAL = app.isPackaged
  ? path.join(process.resourcesPath, 'feature_flags.json')
  : path.join(REPO_DIR, 'feature_flags.json');

let _featureFlags = {};

function loadLocalFlags() {
  try {
    _featureFlags = JSON.parse(fs.readFileSync(FLAGS_LOCAL, 'utf8'));
    log.info('[flags] Loaded local feature_flags.json');
  } catch (e) {
    log.warn('[flags] Could not read local flags:', e.message);
  }
}

async function fetchRemoteFlags() {
  return new Promise((resolve) => {
    const url = new URL(FLAGS_URL);
    http.get({ hostname: url.hostname, path: url.pathname, headers: { 'User-Agent': 'K-Creative' } },
      (res) => {
        let data = '';
        res.on('data', d => data += d);
        res.on('end', () => {
          try {
            const remote = JSON.parse(data);
            _featureFlags = { ..._featureFlags, ...remote };
            log.info('[flags] Remote flags merged — rollout:', remote._rollout_pct ?? '?', '%');
          } catch (_) {}
          resolve();
        });
      }
    ).on('error', (e) => {
      log.warn('[flags] Remote fetch failed (offline?):', e.message);
      resolve();
    });
  });
}

ipcMain.handle('get-feature-flags', () => _featureFlags);
ipcMain.handle('get-version',       () => app.getVersion());

// ── Dashboard IPC ─────────────────────────────────────────────────────────────
ipcMain.on('navigate-to-live',      () => mainWindow?.loadURL(LIVE_URL));
ipcMain.on('navigate-to-dashboard', () => mainWindow?.loadURL(DASHBOARD_URL));

ipcMain.handle('load-brand', () => {
  try { return JSON.parse(fs.readFileSync(BRAND_DATA_FILE, 'utf8')); }
  catch { return null; }
});

ipcMain.handle('save-brand', (_e, data) => {
  try { fs.writeFileSync(BRAND_DATA_FILE, JSON.stringify(data, null, 2), 'utf8'); return true; }
  catch (e) { log.warn('[brand] save error:', e.message); return false; }
});

ipcMain.handle('export-icons', async (_e, files, platform) => {
  const dest = path.join(app.getPath('downloads'), `k-creative-icons-${platform}`);
  fs.mkdirSync(dest, { recursive: true });
  for (const { name, dataUrl } of files) {
    const buf = Buffer.from(dataUrl.replace(/^data:image\/png;base64,/, ''), 'base64');
    fs.writeFileSync(path.join(dest, name), buf);
  }
  shell.openPath(dest);
  return dest;
});

ipcMain.handle('save-file', async (_e, dataUrl, filename) => {
  const { filePath } = await dialog.showSaveDialog(mainWindow, {
    defaultPath: path.join(app.getPath('downloads'), filename),
    filters: [{ name: 'PNG Image', extensions: ['png'] }],
  });
  if (filePath) {
    const buf = Buffer.from(dataUrl.replace(/^data:image\/png;base64,/, ''), 'base64');
    fs.writeFileSync(filePath, buf);
    return filePath;
  }
  return null;
});

ipcMain.handle('open-in-inkscape', async (_e, dataUrl) => {
  const tmp = path.join(app.getPath('temp'), `k-creative-icon-${Date.now()}.png`);
  const buf = Buffer.from(dataUrl.replace(/^data:image\/png;base64,/, ''), 'base64');
  fs.writeFileSync(tmp, buf);
  const inkscape = process.platform === 'darwin' ? '/Applications/Inkscape.app/Contents/MacOS/inkscape'
    : process.platform === 'win32' ? 'C:\\Program Files\\Inkscape\\bin\\inkscape.exe'
    : 'inkscape';
  spawn(inkscape, [tmp], { detached: true, stdio: 'ignore' }).unref();
  return tmp;
});

ipcMain.handle('check-for-update', () => {
  if (!app.isPackaged) return 'dev';
  const { autoUpdater } = require('electron-updater');
  return autoUpdater.checkForUpdates().catch(() => null);
});

// ── Canvas AI Bridge (targets designer iframe inside mainWindow) ──────────────
// The icon-designer.html runs as an iframe in dashboard.html within mainWindow.
// We reach canvasAPI by crossing the frame boundary via executeJavaScript.

ipcMain.handle('canvas-exec', async (_e, cmd) => {
  return mainWindow?.webContents
    .executeJavaScript(`document.getElementById('designer-frame')?.contentWindow?.canvasAPI?.exec(${JSON.stringify(cmd)})`)
    .catch(() => null);
});

ipcMain.handle('canvas-get-state', async () => {
  return mainWindow?.webContents
    .executeJavaScript(`document.getElementById('designer-frame')?.contentWindow?.canvasAPI?.getState()`)
    .catch(() => null);
});

ipcMain.handle('canvas-load-state', async (_e, state) => {
  return mainWindow?.webContents
    .executeJavaScript(`document.getElementById('designer-frame')?.contentWindow?.canvasAPI?.loadState(${JSON.stringify(state)})`)
    .catch(() => null);
});

function sendLoadingStatus(type, msg, detail) {
  mainWindow?.webContents.send('loading-status', { type, msg, detail });
}

ipcMain.on('retry-backend', async () => {
  sendLoadingStatus('status', 'Starte Backend neu…');
  await startBackend();
  mainWindow?.loadURL(LIVE_URL);
});
ipcMain.on('open-logs', () => shell.openPath(log.transports.file.getFile().path));
ipcMain.on('quit-app',  () => app.quit());

// ── Auto-updater ──────────────────────────────────────────────────────────────
ipcMain.handle('download-update', () => {
  const { autoUpdater } = require('electron-updater');
  return autoUpdater.downloadUpdate().catch(e => log.warn('[updater] download error:', e.message));
});
ipcMain.handle('install-update',  () => {
  const { autoUpdater } = require('electron-updater');
  autoUpdater.quitAndInstall(false, true);
});

function injectUpdatePanel(js) {
  if (!mainWindow) return;
  mainWindow.webContents.executeJavaScript(js).catch(() => {});
}

function showUpdateAvailable(version) {
  const cur = app.getVersion();
  injectUpdatePanel(`(() => {
    document.getElementById('__ku')?.remove();
    const el = document.createElement('div');
    el.id = '__ku';
    el.style.cssText = [
      'position:fixed','bottom:20px','right:20px','z-index:99999',
      'width:300px','background:rgba(7,6,13,0.96)',
      'border:1px solid rgba(108,71,255,0.35)','border-radius:14px',
      'padding:16px 18px','box-shadow:0 8px 40px rgba(0,0,0,0.6),0 0 0 1px rgba(108,71,255,0.08)',
      'backdrop-filter:blur(20px)',
      'font-family:-apple-system,SF Pro Display,system-ui,sans-serif',
      'color:#e8e0ff','font-size:13px','line-height:1.5',
      'animation:__ku-in .25s cubic-bezier(.34,1.56,.64,1) both',
    ].join(';');
    el.innerHTML = \`
      <style>
        @keyframes __ku-in{from{opacity:0;transform:translateY(12px) scale(.97)}to{opacity:1;transform:none}}
        #__ku .ku-logo{font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;background:linear-gradient(135deg,#6C47FF,#a855f7,#60A5FA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
        #__ku .ku-title{font-size:14px;font-weight:700;color:#e8e0ff;margin-bottom:3px}
        #__ku .ku-sub{font-size:11.5px;color:rgba(232,224,255,.5);margin-bottom:14px}
        #__ku .ku-row{display:flex;gap:8px;align-items:center}
        #__ku .ku-btn{flex:1;padding:8px 0;border-radius:8px;border:none;cursor:pointer;font-size:12.5px;font-weight:700;letter-spacing:.01em;transition:opacity .15s}
        #__ku .ku-btn:hover{opacity:.8}
        #__ku .ku-primary{background:linear-gradient(135deg,#6C47FF,#a855f7);color:#fff}
        #__ku .ku-close{position:absolute;top:12px;right:14px;background:none;border:none;color:rgba(232,224,255,.35);cursor:pointer;font-size:16px;line-height:1;padding:2px 4px}
        #__ku .ku-close:hover{color:rgba(232,224,255,.7)}
      </style>
      <button class="ku-close" onclick="document.getElementById('__ku')?.remove()">×</button>
      <div class="ku-logo">K-Creative Studio</div>
      <div class="ku-title">Version ${version} verfügbar</div>
      <div class="ku-sub">Du verwendest v${cur}</div>
      <div class="ku-row">
        <button class="ku-btn ku-primary" onclick="window.electronBridge?.downloadUpdate?.();document.querySelector('#__ku .ku-primary').textContent='Wird geladen…';document.querySelector('#__ku .ku-primary').disabled=true">Update laden</button>
      </div>
    \`;
    document.body.appendChild(el);
  })()`);
}

function showUpdateProgress(pct, mbps) {
  injectUpdatePanel(`(() => {
    const el = document.getElementById('__ku');
    if (!el) return;
    const bar = el.querySelector('#__ku-bar');
    const lbl = el.querySelector('#__ku-lbl');
    if (bar) { bar.style.width = '${pct}%'; }
    if (lbl) { lbl.textContent = '${pct}% · ${mbps} MB/s'; }
    if (!bar) {
      el.innerHTML = \`
        <style>
          #__ku .ku-logo{font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;background:linear-gradient(135deg,#6C47FF,#a855f7,#60A5FA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px}
          #__ku .ku-title{font-size:13px;font-weight:600;color:rgba(232,224,255,.7);margin-bottom:12px}
          #__ku .ku-track{width:100%;height:4px;background:rgba(108,71,255,.18);border-radius:99px;overflow:hidden;margin-bottom:8px}
          #__ku .ku-fill{height:100%;background:linear-gradient(90deg,#6C47FF,#a855f7);border-radius:99px;transition:width .3s}
          #__ku .ku-pct{font-size:11px;color:rgba(232,224,255,.45);text-align:right}
        </style>
        <div class="ku-logo">K-Creative Studio</div>
        <div class="ku-title">Update wird geladen…</div>
        <div class="ku-track"><div class="ku-fill" id="__ku-bar" style="width:${pct}%"></div></div>
        <div class="ku-pct" id="__ku-lbl">${pct}% · ${mbps} MB/s</div>
      \`;
    }
  })()`);
}

function showUpdateReady(version) {
  injectUpdatePanel(`(() => {
    const el = document.getElementById('__ku') || (() => {
      const d = document.createElement('div');
      d.id = '__ku';
      d.style.cssText = [
        'position:fixed','bottom:20px','right:20px','z-index:99999',
        'width:300px','background:rgba(7,6,13,0.96)',
        'border:1px solid rgba(0,255,136,0.3)','border-radius:14px',
        'padding:16px 18px','box-shadow:0 8px 40px rgba(0,0,0,0.6)',
        'backdrop-filter:blur(20px)',
        'font-family:-apple-system,SF Pro Display,system-ui,sans-serif',
        'color:#e8e0ff','font-size:13px',
        'animation:__ku-in .25s cubic-bezier(.34,1.56,.64,1) both',
      ].join(';');
      document.body.appendChild(d);
      return d;
    })();
    el.style.borderColor = 'rgba(0,255,136,0.3)';
    el.innerHTML = \`
      <style>
        @keyframes __ku-in{from{opacity:0;transform:translateY(12px) scale(.97)}to{opacity:1;transform:none}}
        #__ku .ku-logo{font-size:11px;font-weight:900;letter-spacing:.12em;text-transform:uppercase;background:linear-gradient(135deg,#6C47FF,#a855f7,#60A5FA);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
        #__ku .ku-check{font-size:22px;margin-bottom:6px}
        #__ku .ku-title{font-size:14px;font-weight:700;color:#00ff88;margin-bottom:3px}
        #__ku .ku-sub{font-size:11.5px;color:rgba(232,224,255,.5);margin-bottom:14px}
        #__ku .ku-row{display:flex;gap:8px}
        #__ku .ku-btn{flex:1;padding:8px 0;border-radius:8px;border:none;cursor:pointer;font-size:12px;font-weight:700;transition:opacity .15s}
        #__ku .ku-btn:hover{opacity:.8}
        #__ku .ku-primary{background:linear-gradient(135deg,#00c872,#00ff88);color:#07060d}
        #__ku .ku-ghost{background:transparent;color:rgba(232,224,255,.5);border:1px solid rgba(108,71,255,.3)!important}
      </style>
      <div class="ku-logo">K-Creative Studio</div>
      <div class="ku-check">✓</div>
      <div class="ku-title">Update bereit</div>
      <div class="ku-sub">Version ${version} heruntergeladen</div>
      <div class="ku-row">
        <button class="ku-btn ku-primary" onclick="window.electronBridge?.installUpdate?.()">Jetzt neu starten</button>
        <button class="ku-btn ku-ghost" onclick="document.getElementById('__ku')?.remove()">Beim nächsten Start</button>
      </div>
    \`;
  })()`);
}

function initAutoUpdater() {
  if (!app.isPackaged) {
    log.info('[updater] Skipped — not packaged');
    return;
  }

  const { autoUpdater } = require('electron-updater');
  autoUpdater.logger = log;
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.allowDowngrade = false;

  if (_featureFlags?.update_channel === 'beta') {
    autoUpdater.allowPrerelease = true;
  }

  autoUpdater.on('update-available', (info) => {
    log.info('[updater] Update available:', info.version);
    showUpdateAvailable(info.version);
  });

  autoUpdater.on('download-progress', (progress) => {
    const pct  = Math.round(progress.percent);
    const mbps = (progress.bytesPerSecond / 1024 / 1024).toFixed(1);
    log.info(`[updater] ${pct}% @ ${mbps} MB/s`);
    showUpdateProgress(pct, mbps);
  });

  autoUpdater.on('update-downloaded', (info) => {
    log.info('[updater] Downloaded:', info.version);
    showUpdateReady(info.version);
  });

  autoUpdater.on('update-not-available', () => {
    log.info('[updater] Up to date');
  });

  autoUpdater.on('error', (err) => {
    log.error('[updater]', err.message);
  });

  // Check 30s after startup, then every 30 minutes
  setTimeout(() => autoUpdater.checkForUpdates().catch(() => {}), 30_000);
  setInterval(() => {
    log.info('[updater] Periodic check (30min interval)');
    autoUpdater.checkForUpdates().catch(() => {});
  }, 30 * 60 * 1000);
}

// ── Backend lifecycle ─────────────────────────────────────────────────────────
function startBackend() {
  return new Promise((resolve) => {
    http.get(`${BACKEND_URL}/api/check`, (res) => {
      if (res.statusCode === 200) {
        log.info('[backend] Already running');
        sendLoadingStatus('log', 'Server bereits aktiv');
        resolve(true);
      } else {
        // Port occupied by another service (e.g. macOS AirPlay on 7000)
        log.warn(`[backend] Port ${BACKEND_PORT} returns ${res.statusCode} — treating as unavailable`);
        resolve(false);
      }
    }).on('error', () => {
      log.info('[backend] Starting Python backend…');
      sendLoadingStatus('status', 'Starte K-Creative Server…');

      const serverBin = app.isPackaged
        ? path.join(process.resourcesPath, 'k-creative-server')
        : null;

      const binExists = serverBin && fs.existsSync(serverBin);
      if (serverBin && !binExists) {
        log.warn('[backend] Bundled binary not found:', serverBin);
        sendLoadingStatus('log', 'Gebündelter Server nicht gefunden — fallback auf python3');
      }

      const [cmd, args, cwd] = binExists
        ? [serverBin, [], path.dirname(serverBin)]
        : ['python3', ['server.py'], STUDIO_DIR];

      sendLoadingStatus('log', binExists ? 'Starte k-creative-server…' : 'Starte python3 server.py…');

      backendProcess = spawn(cmd, args, {
        cwd,
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: false,
        env: {
          ...process.env,
          K_CREATIVE_DIR:  path.join(app.getPath('home'), 'K-Creative'),
          K_MUSIC_DIR:     path.join(app.getPath('music')),
          K_CREATIVE_PORT: String(BACKEND_PORT),
        },
      });

      backendProcess.stdout.on('data', d => {
        const msg = d.toString().trim();
        log.info('[backend]', msg);
        sendLoadingStatus('log', msg.substring(0, 80));
      });
      backendProcess.stderr.on('data', d => {
        const msg = d.toString().trim();
        log.warn('[backend]', msg);
        if (msg) sendLoadingStatus('log', msg.substring(0, 100));
      });
      backendProcess.on('error', (err) => {
        log.error('[backend] spawn error:', err.message);
      });
      backendProcess.on('exit', (code) => log.warn('[backend] Exited with code', code));

      let attempts = 0;
      const MAX_ATTEMPTS = 240; // 120s at 500ms intervals
      const poll = setInterval(() => {
        const n = Math.round(attempts * 0.5);
        if (n % 5 === 0) sendLoadingStatus('status', `Server startet… (${n}s)`);

        http.get(`${BACKEND_URL}/api/check`, (res) => {
          if (res.statusCode === 200) {
            clearInterval(poll);
            log.info('[backend] Ready');
            sendLoadingStatus('status', 'Server bereit');
            resolve(true);
          }
        }).on('error', () => {
          if (++attempts > MAX_ATTEMPTS) {
            clearInterval(poll);
            log.error('[backend] Failed to start after 120s');
            resolve(false);
          }
        });
      }, 500);
    });
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}

// ── Chokidar hot-reload watcher ───────────────────────────────────────────────
function startWatcher() {
  let chokidar;
  try { chokidar = require('chokidar'); }
  catch (e) { log.warn('[watcher] chokidar not available — hot-reload disabled'); return; }

  const WATCH = [
    path.join(ENGINE_DIR, 'plugins'),
    path.join(ENGINE_DIR, 'shaders'),
    path.join(STUDIO_DIR, 'live.html'),
  ];

  watcher = chokidar.watch(WATCH, {
    ignoreInitial: true,
    ignored: /(^|[/\\])\../,
    awaitWriteFinish: { stabilityThreshold: 100, pollInterval: 50 },
  });

  const notify = (event, filePath) => {
    const ext  = path.extname(filePath).slice(1);
    const name = path.basename(filePath);
    log.debug(`[hot-reload] ${event}: ${name}`);
    mainWindow?.webContents.send('hot-reload', { event, file: name, ext });
  };

  watcher.on('change', fp => notify('change', fp));
  watcher.on('add',    fp => notify('add',    fp));
  log.info('[watcher] Watching live_engine/ for hot-reload');
}

function stopWatcher() {
  if (watcher) { watcher.close(); watcher = null; }
}

// ── Window ────────────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width:  1920,
    height: 1080,
    minWidth:  1280,
    minHeight: 720,
    title: 'K-Creative Live',
    backgroundColor: '#07060d',
    kiosk:      IS_KIOSK,
    fullscreen: IS_KIOSK,
    frame:     !IS_KIOSK,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
      preload: path.join(__dirname, 'preload.js'),
    },
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    icon: path.join(__dirname, 'src-tauri', 'icons', '128x128.png'),
  });

  mainWindow.loadURL(LOADING_URL);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith('http://localhost')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  if (IS_DEV) mainWindow.webContents.openDevTools({ mode: 'detach' });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── App menu ──────────────────────────────────────────────────────────────────
function buildMenu() {
  const template = [
    {
      label: 'K-Creative',
      submenu: [
        { label: 'Über K-Creative', role: 'about' },
        { type: 'separator' },
        { label: 'Beenden', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() },
      ],
    },
    {
      label: 'Ansicht',
      submenu: [
        { label: 'Neu laden',  accelerator: 'CmdOrCtrl+R', click: () => mainWindow?.webContents.reload() },
        { label: 'Vollbild',   accelerator: 'F11',          role: 'togglefullscreen' },
        { type: 'separator' },
        { label: 'DevTools',   accelerator: 'CmdOrCtrl+Alt+I', click: () => mainWindow?.webContents.toggleDevTools() },
      ],
    },
    {
      label: 'Studio',
      submenu: [
        { label: 'Dashboard',        click: () => mainWindow?.loadURL(DASHBOARD_URL) },
        { label: 'Icon Designer',    click: () => mainWindow?.webContents.executeJavaScript("nav('designer')") },
        { label: 'Live Interface',   click: () => mainWindow?.loadURL(LIVE_URL) },
        { label: 'Studio (Classic)', click: () => mainWindow?.loadURL(BACKEND_URL) },
        { type: 'separator' },
        { label: 'Im Browser öffnen', click: () => shell.openExternal(LIVE_URL) },
        { label: 'Log öffnen',        click: () => shell.openPath(log.transports.file.getFile().path) },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
if (process.platform === 'linux') {
  app.commandLine.appendSwitch('no-sandbox');
  app.commandLine.appendSwitch('enable-unsafe-swiftshader');
  app.commandLine.appendSwitch('disable-gpu-sandbox');
}

app.whenReady().then(async () => {
  loadLocalFlags();

  buildMenu();
  createWindow();  // opens loading.html immediately

  // Race-condition-safe wait: resolves immediately if loading.html already loaded
  await new Promise(resolve => {
    if (!mainWindow.webContents.isLoading()) {
      resolve();
    } else {
      mainWindow.webContents.once('did-finish-load', resolve);
    }
  });

  // Load dashboard immediately — backend starts in parallel
  mainWindow?.loadURL(DASHBOARD_URL);

  // Fallback: if dashboard fails to load, show loading.html with error
  mainWindow?.webContents.once('did-fail-load', (_e, code, desc, url) => {
    log.error('[startup] Failed to load dashboard:', code, desc, url);
    mainWindow?.loadURL(LOADING_URL);
    setTimeout(() => sendLoadingStatus('error',
      'Dashboard konnte nicht geladen werden.',
      `Fehler ${code}: ${desc}`
    ), 500);
  });

  // Start backend in parallel — auto-retry up to 3× with 30s backoff
  let retries = 0;
  const tryBackend = () => startBackend().then(ok => {
    if (!ok && retries++ < 3) {
      log.warn(`[backend] Start failed — retry ${retries}/3 in 30s`);
      mainWindow?.webContents.send('hot-reload', { event: 'backend-retry', retry: retries });
      setTimeout(tryBackend, 30_000);
    } else if (!ok) {
      log.error('[backend] Failed after 3 retries');
    }
  });
  tryBackend();

  startWatcher();
  initAutoUpdater();

  // Fetch remote flags in background (don't block startup)
  fetchRemoteFlags().then(() => {
    mainWindow?.webContents.send('hot-reload', { event: 'flags-updated', file: 'feature_flags.json', ext: 'json' });
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopWatcher();
  if (process.platform !== 'darwin') {
    stopBackend();
    app.quit();
  }
});

app.on('before-quit', () => {
  stopWatcher();
  stopBackend();
});
