/**
 * K-Creative Studio — Electron Desktop App (Kiosk / Split-Screen Mode)
 * Left panel:  DJ + Shader interface  (/live)
 * Right panel: Claude Code terminal   (PTY via xterm.js)
 *
 * Chokidar watches live_engine/ for plugin/shader/SC changes
 * and sends IPC hot-reload events to the renderer without restarting audio.
 */
const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

let mainWindow;
let backendProcess;
let watcher;

const REPO_DIR    = path.join(__dirname, '..');
const STUDIO_DIR  = path.join(REPO_DIR, 'studio');
const ENGINE_DIR  = path.join(REPO_DIR, 'live_engine');
const BACKEND_URL = 'http://localhost:7000';
const LIVE_URL    = `${BACKEND_URL}/live`;

// ── Backend lifecycle ────────────────────────────────────────────────────────
function startBackend() {
  return new Promise((resolve) => {
    http.get(`${BACKEND_URL}/api/check`, () => {
      console.log('[K-Creative] Backend already running');
      resolve();
    }).on('error', () => {
      console.log('[K-Creative] Starting Python backend…');
      backendProcess = spawn('python3', ['server.py'], {
        cwd: STUDIO_DIR,
        stdio: ['ignore', 'pipe', 'pipe'],
        detached: false,
      });

      backendProcess.stdout.on('data', d => console.log('[backend]', d.toString().trim()));
      backendProcess.stderr.on('data', d => console.error('[backend]', d.toString().trim()));

      let attempts = 0;
      const poll = setInterval(() => {
        http.get(`${BACKEND_URL}/api/check`, () => {
          clearInterval(poll);
          console.log('[K-Creative] Backend ready');
          resolve();
        }).on('error', () => {
          if (++attempts > 30) {
            clearInterval(poll);
            console.error('[K-Creative] Backend failed to start');
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

// ── Chokidar hot-reload watcher ──────────────────────────────────────────────
function startWatcher() {
  let chokidar;
  try {
    chokidar = require('chokidar');
  } catch (e) {
    console.warn('[K-Creative] chokidar not installed — hot-reload disabled');
    return;
  }

  const WATCH_PATHS = [
    path.join(ENGINE_DIR, 'plugins'),
    path.join(ENGINE_DIR, 'shaders'),
    path.join(STUDIO_DIR, 'live.html'),
  ];

  watcher = chokidar.watch(WATCH_PATHS, {
    ignoreInitial: true,
    ignored: /(^|[/\\])\../,   // dot-files
    awaitWriteFinish: { stabilityThreshold: 100, pollInterval: 50 },
  });

  const notify = (event, filePath) => {
    const ext  = path.extname(filePath).slice(1);   // py, glsl, html, scd…
    const name = path.basename(filePath);
    console.log(`[hot-reload] ${event}: ${name}`);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('hot-reload', { event, file: name, ext });
    }
  };

  watcher.on('change', fp => notify('change', fp));
  watcher.on('add',    fp => notify('add',    fp));
  console.log('[K-Creative] Watching live_engine/ for hot-reload');
}

function stopWatcher() {
  if (watcher) { watcher.close(); watcher = null; }
}

// ── Window ───────────────────────────────────────────────────────────────────
function createWindow() {
  const isKiosk  = process.argv.includes('--kiosk');
  const isDev    = process.argv.includes('--dev');

  mainWindow = new BrowserWindow({
    width:  1920,
    height: 1080,
    minWidth:  1280,
    minHeight: 720,
    title: 'K-Creative Live',
    backgroundColor: '#07060f',
    kiosk: isKiosk,
    fullscreen: isKiosk,
    frame: !isKiosk,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,          // allow localhost API + WebSocket
      preload: path.join(__dirname, 'preload.js'),
    },
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    icon: path.join(__dirname, 'src-tauri', 'icons', '128x128.png'),
  });

  mainWindow.loadURL(LIVE_URL);

  // Open external links in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith('http://localhost')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  if (isDev) mainWindow.webContents.openDevTools({ mode: 'detach' });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Preload: expose hot-reload IPC to renderer ───────────────────────────────
// Written at startup so the file is always in sync with main.js
const PRELOAD_SRC = `
const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('electronBridge', {
  onHotReload: (cb) => ipcRenderer.on('hot-reload', (_e, data) => cb(data)),
});
`;

function writePreload() {
  const dest = path.join(__dirname, 'preload.js');
  // Only write if content differs (avoids chokidar re-triggering)
  const current = fs.existsSync(dest) ? fs.readFileSync(dest, 'utf8') : '';
  if (current !== PRELOAD_SRC) fs.writeFileSync(dest, PRELOAD_SRC, 'utf8');
}

// ── App menu ─────────────────────────────────────────────────────────────────
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
        { label: 'Neu laden', accelerator: 'CmdOrCtrl+R', click: () => mainWindow?.webContents.reload() },
        { label: 'Vollbild',  accelerator: 'F11',          role: 'togglefullscreen' },
        { type: 'separator' },
        { label: 'DevTools',  accelerator: 'CmdOrCtrl+Alt+I', click: () => mainWindow?.webContents.toggleDevTools() },
      ],
    },
    {
      label: 'Studio',
      submenu: [
        { label: 'Live Interface',    click: () => mainWindow?.loadURL(LIVE_URL) },
        { label: 'Studio (Classic)',  click: () => mainWindow?.loadURL(BACKEND_URL) },
        { type: 'separator' },
        { label: 'Im Browser öffnen', click: () => shell.openExternal(LIVE_URL) },
        { label: 'Backend-Log',       click: () => shell.openPath('/tmp/studio.log').catch(() => {}) },
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
  writePreload();
  buildMenu();
  await startBackend();
  createWindow();
  startWatcher();

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
