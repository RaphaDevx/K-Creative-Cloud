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
const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
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
const BACKEND_URL = 'http://localhost:7000';
const LIVE_URL    = `${BACKEND_URL}/live`;

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

// ── Auto-updater ──────────────────────────────────────────────────────────────
function initAutoUpdater() {
  if (!app.isPackaged) {
    log.info('[updater] Skipped — not packaged');
    return;
  }

  let { autoUpdater } = require('electron-updater');
  autoUpdater.logger = log;
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  // Use beta channel if flag is set
  if (_featureFlags?.update_channel === 'beta') {
    autoUpdater.allowPrerelease = true;
  }

  autoUpdater.on('update-available', (info) => {
    log.info('[updater] Update available:', info.version);
    mainWindow?.webContents.send('update-available', info);
  });

  autoUpdater.on('update-downloaded', (info) => {
    log.info('[updater] Downloaded:', info.version);
    mainWindow?.webContents.send('update-downloaded', info);
  });

  autoUpdater.on('error', (err) => {
    log.error('[updater]', err.message);
  });

  ipcMain.on('install-update', () => autoUpdater.quitAndInstall());

  // Check 30s after startup, then every 4 hours
  setTimeout(() => autoUpdater.checkForUpdatesAndNotify(), 30_000);
  setInterval(() => autoUpdater.checkForUpdatesAndNotify(), 4 * 60 * 60 * 1000);
}

// ── Backend lifecycle ─────────────────────────────────────────────────────────
function startBackend() {
  return new Promise((resolve) => {
    http.get(`${BACKEND_URL}/api/check`, () => {
      log.info('[backend] Already running');
      resolve();
    }).on('error', () => {
      log.info('[backend] Starting Python backend…');

      // Use bundled binary in production, python3 in dev
      const serverBin = app.isPackaged
        ? path.join(process.resourcesPath, 'k-creative-server')
        : null;

      const [cmd, args, cwd] = serverBin
        ? [serverBin, [], path.dirname(serverBin)]
        : ['python3', ['server.py'], STUDIO_DIR];

      backendProcess = spawn(cmd, args, {
        cwd,
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: false,
        env: {
          ...process.env,
          K_CREATIVE_DIR: path.join(app.getPath('home'), 'K-Creative'),
          K_MUSIC_DIR:    path.join(app.getPath('music')),
        },
      });

      backendProcess.stdout.on('data', d => log.info('[backend]', d.toString().trim()));
      backendProcess.stderr.on('data', d => log.warn('[backend]', d.toString().trim()));
      backendProcess.on('exit', (code) => log.warn('[backend] Exited with code', code));

      let attempts = 0;
      const poll = setInterval(() => {
        http.get(`${BACKEND_URL}/api/check`, () => {
          clearInterval(poll);
          log.info('[backend] Ready');
          resolve();
        }).on('error', () => {
          if (++attempts > 40) {
            clearInterval(poll);
            log.error('[backend] Failed to start after 20s');
            resolve();
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
    backgroundColor: '#07060f',
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

  mainWindow.loadURL(LIVE_URL);

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
app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('enable-unsafe-swiftshader');
app.commandLine.appendSwitch('disable-gpu-sandbox');

app.whenReady().then(async () => {
  loadLocalFlags();

  buildMenu();
  await startBackend();
  createWindow();
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
