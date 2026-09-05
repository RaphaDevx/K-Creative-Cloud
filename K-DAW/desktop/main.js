const { app, BrowserWindow, dialog, shell } = require('electron');
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
}

// ── App lifecycle ──────────────────────────────────────────────────────────────
app.whenReady().then(() => {
  startServer();
  createWindow();

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
