/**
 * Electron preload — exposes safe IPC bridges to the renderer (live.html).
 * contextIsolation: true  →  no direct Node access from renderer.
 */
const { contextBridge, ipcRenderer } = require('electron');

// Loading screen API (used by loading.html before backend is ready)
contextBridge.exposeInMainWorld('electronAPI', {
  getVersion:       () => ipcRenderer.invoke('get-version'),
  onLoadingStatus:  (cb) => ipcRenderer.on('loading-status', cb),
  retryBackend:     () => ipcRenderer.send('retry-backend'),
  openLogs:         () => ipcRenderer.send('open-logs'),
  quitApp:          () => ipcRenderer.send('quit-app'),
});

contextBridge.exposeInMainWorld('electronBridge', {
  // Hot-reload: fired when a file in live_engine/ changes
  onHotReload: (cb) =>
    ipcRenderer.on('hot-reload', (_e, data) => cb(data)),

  // Auto-updater — called by the injected update panel buttons
  downloadUpdate:  () => ipcRenderer.invoke('download-update'),
  installUpdate:   () => ipcRenderer.invoke('install-update'),
  checkForUpdate:  () => ipcRenderer.invoke('check-for-update'),

  // Feature flags (resolved in main process, cached)
  getFeatureFlags: () => ipcRenderer.invoke('get-feature-flags'),

  // App metadata
  getVersion: () => ipcRenderer.invoke('get-version'),

  // Dashboard navigation
  navigateToLive:      () => ipcRenderer.send('navigate-to-live'),
  navigateToDashboard: () => ipcRenderer.send('navigate-to-dashboard'),

  // Brand data (persisted to userData/k-creative-brand.json)
  loadBrand: ()       => ipcRenderer.invoke('load-brand'),
  saveBrand: (data)   => ipcRenderer.invoke('save-brand', data),

  // Icon export
  exportIcons:     (files, platform) => ipcRenderer.invoke('export-icons', files, platform),
  saveFile:        (dataUrl, name)   => ipcRenderer.invoke('save-file', dataUrl, name),
  openInInkscape:  (dataUrl)         => ipcRenderer.invoke('open-in-inkscape', dataUrl),

  // Canvas AI Bridge (designer iframe inside mainWindow)
  canvasExec:      (cmd)     => ipcRenderer.invoke('canvas-exec', cmd),
  canvasGetState:  ()        => ipcRenderer.invoke('canvas-get-state'),
  canvasLoadState: (state)   => ipcRenderer.invoke('canvas-load-state', state),
});
